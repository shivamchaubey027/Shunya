
# SystemRescue USB Setup Guide

This guide explains how to set up a bootable SystemRescue USB drive to run the Secure Data Wiper & Verifier (SDWV) application in a self-contained, offline environment.

## Step 1: Create the Bootable USB

1.  **Download SystemRescue:** Download the latest ISO image from the [official SystemRescue website](https://www.systemrescue.org/Download/).
2.  **Create the USB Drive:** Use a tool like [Rufus](https://rufus.ie/) or [balenaEtcher](https://www.balena.io/etcher/) to write the downloaded ISO image to a USB drive (at least 2GB recommended).

## Step 2: Set Up the Directory Structure

After creating the bootable USB, plug it into a computer. It should appear as a standard storage device. Create the following directory structure in the **root** of the USB drive:

```
(USB Root)/
├── autorun.yml           <-- The autorun file from this directory
├── sdwv_app/             <-- A new directory you create
│   ├── main.py
│   ├── certificate_module.py
│   ├── key_generator.py
│   ├── nwipe_handler.py
│   ├── safety_config.py
│   ├── verify_module.py
│   ├── private_key.pem
│   ├── public_key.pem
│   ├── requirements.txt
│   └── libs/             <-- A new directory for offline dependencies
└── ... (other SystemRescue files and folders)
```

- **Copy `autorun.yml`:** Copy the `autorun.yml` file from this `systemrescue_config` directory to the root of the USB drive.
- **Create `sdwv_app/`:** Create a new folder named `sdwv_app` in the root of the USB drive.
- **Copy Application Files:** Copy all the Python files (`.py`) and the key files (`.pem`) from the project into the `sdwv_app/` folder.

## Step 3: Bundle Offline Dependencies

The SystemRescue environment does not have internet access, so you must include the Python libraries on the USB drive.

1.  **On your development machine (with the `venv` activated):**
    Run the following command to download the packages (`PyQt5`, `cryptography`, `reportlab`, `qrcode`, `pillow`) into the `libs` folder.

    ```bash
    pip download -r requirements.txt -d sdwv_app/libs/
    ```
    *Note: This command downloads the wheel files (`.whl`) for the libraries. You should run this on a Linux machine to ensure you get the correct versions for the SystemRescue environment.*

2.  **Modify `main.py` for Offline Use:**
    To make the application use these bundled libraries, you must add the following lines to the **very top** of your `main.py` script:

    ```python
    import sys
    import os
    # Add the bundled libraries to the Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))
    ```
    This tells the Python interpreter to look for libraries inside the `libs` folder on the USB drive.

## Step 4: Boot and Run

Eject the USB drive safely. You can now boot a computer from this USB drive. Thanks to the `autorun.yml` file, the SDWV application should launch automatically after the system finishes booting.
