import sys
import urllib.parse
import json
import subprocess
import re
import os

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
    QLabel, QPushButton, QListWidget, QLineEdit, QProgressBar, QFileDialog, 
    QMessageBox, QListWidgetItem, QHBoxLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from certificate_module import (
    create_certificate_data,
    sign_certificate,
    generate_pdf_certificate,
    generate_json_certificate,
    generate_qr_code,
)
import safety_config
from nwipe_handler import build_nwipe_command, run_nwipe

# --- Dark Theme Stylesheet ---
DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}
QMainWindow {
    background-color: #2b2b2b;
}
QStackedWidget {
    background-color: #2b2b2b;
}
QLabel {
    color: #ffffff;
}
QPushButton {
    background-color: #555555;
    color: #ffffff;
    border: 1px solid #666666;
    padding: 8px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #666666;
}
QPushButton:pressed {
    background-color: #444444;
}
QPushButton:disabled {
    background-color: #444444;
    color: #888888;
}
QListWidget {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    font-size: 14px;
}
QListWidget::item {
    padding: 12px 8px;
    border-bottom: 1px solid #555555;
    min-height: 50px;
}
QListWidget::item:hover {
    background-color: #4a4a4a;
}
QListWidget::item:selected {
    background-color: #0078d7;
    color: #ffffff;
}
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    padding: 8px;
    border-radius: 4px;
}
QProgressBar {
    border: 1px solid #555555;
    border-radius: 4px;
    text-align: center;
    background-color: #3c3c3c;
}
QProgressBar::chunk {
    background-color: #0078d7;
    width: 10px;
    margin: 0.5px;
}
QMessageBox {
    background-color: #3c3c3c;
}
"""

class WipeThread(QThread):
    """Worker thread for the wipe process."""
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    log_message = pyqtSignal(str)

    def __init__(self, device_path, method, is_dry_run=False):
        super().__init__()
        self.device_path = f"/dev/{device_path}"
        self.method = method
        self.is_dry_run = is_dry_run

    def run(self):
        if self.is_dry_run:
            command = build_nwipe_command(self.device_path, self.method, self.is_dry_run)
            self.log_message.emit("*** DRY RUN MODE ***")
            self.log_message.emit(f"Command: {' '.join(command)}")
            self.progress.emit(100)
            self.finished.emit()
            return

        # --- REAL WIPE LOGIC ---
        command = build_nwipe_command(self.device_path, self.method, is_dry_run=False)
        self.log_message.emit("--- REAL WIPE STARTED ---")
        self.log_message.emit(f"Command: {' '.join(command)}")

        progress_regex = re.compile(r"(\d+\.\d+)\s*% done")

        for line in run_nwipe(command):
            self.log_message.emit(line.strip())  # Log nwipe's raw output
            match = progress_regex.search(line)
            if match:
                percentage = float(match.group(1))
                self.progress.emit(int(percentage))
        
        self.progress.emit(100) # Ensure it finishes at 100%
        self.log_message.emit("--- REAL WIPE FINISHED ---")
        self.finished.emit()

class DiskInfo:
    """Helper class to store disk information and provide formatting."""
    def __init__(self, disk_data):
        self.disk_data = disk_data
    
    def get_display_text(self):
        """Generate display text for the disk."""
        model = self.disk_data.get('model', 'Unknown Device')
        size = self.disk_data.get('size', 'N/A')
        name = self.disk_data.get('name', 'N/A')
        
        transport_value = self.disk_data.get('tran')
        if transport_value is None:
            transport = 'unknown'
        else:
            transport = str(transport_value).lower()

        is_removable = self.disk_data.get('rm', False)
        disk_type = self.disk_data.get('type')

        # Create base text
        if disk_type == 'loop':
            base_text = f"Virtual Test Disk - {name} ({size})"
        elif transport == 'usb':
            base_text = f"USB Drive - {model} - {name} ({size})"
        elif is_removable:
            base_text = f"Removable Drive - {model} - {name} ({size})"
        else:
            base_text = f"INTERNAL DRIVE - {model} - {name} ({size})"
        
        # Add safety status
        is_safe, reason = self.is_safe()
        if is_safe:
            status = "[SAFE] Ready to Wipe"
        else:
            status = f"[BLOCKED] {reason}"
        
        return f"{base_text}  —  {status}"
    
    def is_safe(self):
        """Check if disk is safe to wipe."""
        disk_type = self.disk_data.get('type')
        is_removable = self.disk_data.get('rm', False)
        
        transport_value = self.disk_data.get('tran')
        if transport_value is None:
            transport = 'unknown'
        else:
            transport = str(transport_value).lower()

        if safety_config.SAFETY_MODE:
            if transport == 'usb' or is_removable:
                return True, "Removable"
            
            if disk_type == 'loop' and 'loop' in safety_config.WHITELISTED_MODELS:
                return True, "Test Disk"

            return False, "SYSTEM DRIVE"
        else:
            return True, "Safety Mode OFF"

class WelcomeScreen(QWidget):
    """Screen 1: Welcome and Disk Selection."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # --- Main Vertical Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # --- Title Widget ---
        title = QLabel("Secure Data Wiper & Verifier")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        # --- Disk List Widget ---
        self.disk_list = QListWidget()
        self.disk_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.disk_list.setResizeMode(QListWidget.Adjust)

        # --- Bottom Buttons Layout ---
        button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh Disk List")
        refresh_button.clicked.connect(self.populate_disks)
        self.wipe_button = QPushButton("Wipe Selected Drive")
        self.wipe_button.clicked.connect(self.go_to_confirmation)
        self.wipe_button.setEnabled(False)
        self.wipe_button.setStyleSheet("font-size: 16px; padding: 12px;")
        
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(self.wipe_button)

        # --- Assemble the Main Layout ---
        layout.addWidget(title, 0)
        layout.addWidget(self.disk_list, 1)
        layout.addLayout(button_layout, 0)

        self.disk_list.itemSelectionChanged.connect(self.enable_wipe_button)
        self.populate_disks()

    def populate_disks(self):
        """Populate the disk list with available drives."""
        self.disk_list.clear()
        self.disk_objects = []  # Store disk objects for later reference
        
        try:
            result = subprocess.run(
                ['lsblk', '--json', '-o', 'NAME,MODEL,SIZE,TYPE,RM,TRAN'], 
                capture_output=True, text=True, check=True
            )
            devices = json.loads(result.stdout)['blockdevices']
            
            for device in devices:
                if device.get('type') in ['disk', 'loop']:
                    disk_info = DiskInfo(device)
                    self.disk_objects.append(disk_info)
                    
                    # Create a simple list item with text
                    item = QListWidgetItem(disk_info.get_display_text())
                    
                    # Color the item based on safety
                    is_safe, _ = disk_info.is_safe()
                    if is_safe:
                        item.setForeground(QColor("#ffffff"))  # White text
                    else:
                        item.setForeground(QColor("#ffaaaa"))  # Light red text
                    
                    self.disk_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Disk Detection Error", f"Could not list disks: {e}")

    def enable_wipe_button(self):
        """Enable wipe button only if a safe disk is selected."""
        current_row = self.disk_list.currentRow()
        if current_row < 0 or current_row >= len(self.disk_objects):
            self.wipe_button.setEnabled(False)
            return

        disk_info = self.disk_objects[current_row]
        is_safe, _ = disk_info.is_safe()
        self.wipe_button.setEnabled(is_safe)

    def go_to_confirmation(self):
        """Navigate to confirmation screen after final warning."""
        current_row = self.disk_list.currentRow()
        if current_row < 0 or current_row >= len(self.disk_objects):
            return
            
        disk_info = self.disk_objects[current_row]
        
        reply = QMessageBox.warning(self, "Final Confirmation", 
            f"You are about to permanently erase:\n\n{disk_info.get_display_text()}\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.main_window.set_selected_disk(disk_info.disk_data)
            self.main_window.stack.setCurrentIndex(1)

class ConfirmationScreen(QWidget):
    """Screen 2: Wipe Confirmation."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        warning_label = QLabel("To proceed, please type ERASE into the box below.")
        warning_label.setAlignment(Qt.AlignCenter)
        warning_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(warning_label)

        self.confirm_text = QLineEdit()
        self.confirm_text.setPlaceholderText('ERASE')
        self.confirm_text.setAlignment(Qt.AlignCenter)
        self.confirm_text.setStyleSheet("font-size: 18px; padding: 10px;")
        layout.addWidget(self.confirm_text)

        self.confirm_button = QPushButton("Confirm & Start Wipe")
        self.confirm_button.clicked.connect(self.go_to_progress)
        self.confirm_button.setEnabled(False)
        self.confirm_button.setStyleSheet("font-size: 16px; padding: 12px; background-color: #e74c3c;")
        layout.addWidget(self.confirm_button)

        self.confirm_text.textChanged.connect(self.enable_confirm_button)

        self.setLayout(layout)

    def enable_confirm_button(self):
        is_enabled = self.confirm_text.text() == "ERASE"
        self.confirm_button.setEnabled(is_enabled)
        if is_enabled:
            self.confirm_button.setStyleSheet("font-size: 16px; padding: 12px; background-color: #c0392b;")
        else:
            self.confirm_button.setStyleSheet("font-size: 16px; padding: 12px; background-color: #e74c3c;")

    def go_to_progress(self):
        self.main_window.stack.setCurrentIndex(2)

class ProgressScreen(QWidget):
    """Screen 3: Wiping Progress."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        self.status_label = QLabel("Wiping in progress...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; margin-bottom: 10px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel Wipe")
        self.cancel_button.clicked.connect(self.cancel_wipe)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def start_wipe(self, device_path):
        self.wipe_thread = WipeThread(device_path, method="dodshort", is_dry_run=False)
        self.wipe_thread.progress.connect(self.progress_bar.setValue)
        self.wipe_thread.log_message.connect(lambda msg: print(msg))
        self.wipe_thread.finished.connect(self.go_to_completion)
        self.wipe_thread.start()

    def cancel_wipe(self):
        if hasattr(self, 'wipe_thread') and self.wipe_thread.isRunning():
            self.wipe_thread.terminate()
            self.main_window.stack.setCurrentIndex(0)

    def go_to_completion(self):
        self.main_window.stack.setCurrentIndex(3)

class CompletionScreen(QWidget):
    """Screen 4: Completion and Certificate."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        self.status_label = QLabel("Wipe Successful!")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2ecc71; margin-bottom: 10px;")
        layout.addWidget(self.status_label)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_label)

        save_button = QPushButton("Save Certificate to USB")
        save_button.clicked.connect(self.save_certificate)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def generate_certificate(self):
        self.certificate_data = create_certificate_data(self.main_window.selected_disk)
        self.signature = sign_certificate(self.certificate_data, "private_key.pem")
        cert_with_sig = self.certificate_data.copy()
        cert_with_sig["signature"] = self.signature.hex()
        full_cert_json = json.dumps(cert_with_sig)
        encoded_cert = urllib.parse.quote(full_cert_json)
        verification_url = f"https://sdwv-verifier.com/verify?cert={encoded_cert}"
        generate_qr_code(verification_url, "certificate_qr.png")
        pixmap = QPixmap("certificate_qr.png")
        scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.qr_label.setPixmap(scaled_pixmap)

    def save_certificate(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        directory = QFileDialog.getExistingDirectory(self, "Select USB Drive", options=options)
        if directory:
            qr_path = "certificate_qr.png"
            generate_pdf_certificate(self.certificate_data, self.signature, qr_path, os.path.join(directory, "certificate.pdf"))
            generate_json_certificate(self.certificate_data, self.signature, os.path.join(directory, "certificate.json"))
            QMessageBox.information(self, "Success", f"Certificate saved to {directory}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDWV - Secure Data Wiper & Verifier")
        self.setGeometry(100, 100, 700, 500)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome_screen = WelcomeScreen(self)
        self.confirmation_screen = ConfirmationScreen(self)
        self.progress_screen = ProgressScreen(self)
        self.completion_screen = CompletionScreen(self)

        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.confirmation_screen)
        self.stack.addWidget(self.progress_screen)
        self.stack.addWidget(self.completion_screen)

        self.stack.currentChanged.connect(self.on_screen_change)

    def set_selected_disk(self, disk):
        self.selected_disk = disk

    def on_screen_change(self, index):
        if index == 2:
            device_name = self.selected_disk.get('name')
            self.progress_screen.start_wipe(device_name)
        elif index == 3:
            self.completion_screen.generate_certificate()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    
    if not os.path.exists("private_key.pem"):
        QMessageBox.critical(None, "Error", "private_key.pem not found. Please run key_generator.py first.")
        sys.exit(1)

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())