
import os
import json
from key_generator import generate_keys
from certificate_module import (
    create_certificate_data,
    sign_certificate,
    generate_pdf_certificate,
    generate_json_certificate,
    generate_qr_code,
)
from verify_module import verify_signature

MOCK_DATA = {
    "deviceModel": "Samsung 970 EVO",
    "deviceSerial": "S4PUNELD571717",
    "deviceSize": "1 TB",
    "wipeMethod": "NIST SP 800-88 Purge",
}

def main():
    """Main function to test Phase 1."""
    print("--- Phase 1 Test Started ---")

    # 1. Generate Keys
    if not (os.path.exists("private_key.pem") and os.path.exists("public_key.pem")):
        print("Generating RSA keys...")
        generate_keys()
        print("  -> Done.")
    else:
        print("RSA keys already exist.")

    # 2. Create Certificate
    print("Creating certificate data...")
    certificate_data = create_certificate_data(MOCK_DATA)
    print("  -> Done.")
    print(json.dumps(certificate_data, indent=4))

    # 3. Sign Certificate
    print("Signing certificate...")
    signature = sign_certificate(certificate_data, "private_key.pem")
    print("  -> Done.")

    # 4. Generate Certificate Files
    print("Generating PDF and JSON certificates...")
    generate_pdf_certificate(certificate_data, signature, "certificate.pdf")
    generate_json_certificate(certificate_data, signature, "certificate.json")
    print("  -> Done.")

    # 5. Generate QR Code
    print("Generating QR code...")
    qr_data = json.dumps({"certificateId": certificate_data["certificateId"]})
    generate_qr_code(qr_data, "certificate_qr.png")
    print("  -> Done.")

    # 6. Verify Signature
    print("Verifying certificate signature...")
    is_valid = verify_signature("certificate.json", "public_key.pem")
    if is_valid:
        print("  -> Signature is VALID.")
    else:
        print("  -> Signature is INVALID.")

    print("--- Phase 1 Test Finished ---")

if __name__ == "__main__":
    main()
