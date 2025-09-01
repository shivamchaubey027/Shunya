# -- SAFETY CONFIGURATION --
# WARNING: Modifying these settings can lead to data loss. 
# Do not disable safety mode unless you are an expert and know what you are doing.

# Master switch for safety features. 
# If True, the application will only allow wiping of whitelisted external USB drives.
# If False, the application will allow wiping of any drive, including internal ones.
SAFETY_MODE = True

# Whitelist of approved device models for testing.
# This is an extra layer of protection to prevent accidental wiping of the wrong drive.
# The model name is read from `lsblk`.
# Example: ["Cruzer Blade", "DataTraveler 2.0"]
WHITELISTED_MODELS = ["Cruzer Blade", "DataTraveler 2.0", "Virtual Disk", "loop"]

# Maximum allowed drive size in Terabytes (TB) to wipe in safety mode.
# This is a safeguard against accidentally wiping large storage arrays.
MAX_SIZE_TB = 2