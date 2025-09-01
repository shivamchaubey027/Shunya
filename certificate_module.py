
import json
import uuid
from datetime import datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import qrcode

def create_certificate_data(disk_info):
    """Creates the certificate data structure from lsblk info."""
    return {
        "certificateId": str(uuid.uuid4()),
        "deviceModel": disk_info.get('model', 'N/A'),
        "deviceSerial": disk_info.get('serial', 'N/A'), # lsblk doesn't typically provide serial
        "deviceSize": disk_info.get('size', 'N/A'),
        "wipeMethod": "NIST SP 800-88 Purge (Simulated)", # This is currently a simulation
        "wipeTimestamp": datetime.utcnow().isoformat() + "Z",
        "status": "Success",
    }

def sign_certificate(certificate_data, private_key_path):
    """Signs the certificate data with the private key."""
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )

    # IMPORTANT: The signature is created from the certificate data *before* the signature itself is added.
    # This exact dictionary structure must be recreated by the verifier.
    certificate_string = json.dumps(certificate_data, sort_keys=True).encode('utf-8')

    signature = private_key.sign(
        certificate_string,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.MGF1.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

from reportlab.lib.utils import ImageReader
from textwrap import wrap
import os

def generate_pdf_certificate(certificate_data, signature, qr_code_path, file_path):
    """Generates a PDF certificate with a QR code and wrapped signature."""
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 100, "Certificate of Data Erasure")
    y_position = height - 140
    for key, value in certificate_data.items():
        c.drawString(100, y_position, f"{key}: {value}")
        y_position -= 20
    
    y_position -= 10
    c.drawString(100, y_position, "Signature:")
    y_position -= 15

    # Switch to a monospace font for the signature
    c.setFont("Courier", 10)
    sig_hex = signature.hex()
    # Wrap the signature hex string at a safe width
    wrapped_sig = wrap(sig_hex, 65)
    for line in wrapped_sig:
        c.drawString(120, y_position, line)
        y_position -= 12 # Line spacing for the smaller font

    # Switch back to the default font
    c.setFont("Helvetica", 12)

    # Embed the QR code
    if os.path.exists(qr_code_path):
        qr_img = ImageReader(qr_code_path)
        c.drawImage(qr_img, width - 220, 80, width=140, height=140, preserveAspectRatio=True, mask='auto')

    c.save()

def generate_json_certificate(certificate_data, signature, file_path):
    """Generates a JSON certificate."""
    certificate_data_with_signature = certificate_data.copy()
    certificate_data_with_signature["signature"] = signature.hex()
    with open(file_path, "w") as f:
        json.dump(certificate_data_with_signature, f, indent=4)

def generate_qr_code(data, file_path):
    """Generates a QR code from the given data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img.save(file_path)
