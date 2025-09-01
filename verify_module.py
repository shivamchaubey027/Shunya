
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

def verify_signature(certificate_path, public_key_path):
    """Verifies the signature of a certificate using the public key."""
    with open(public_key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
        )

    with open(certificate_path, "r") as f:
        certificate_with_signature = json.load(f)

    signature = bytes.fromhex(certificate_with_signature.pop("signature"))
    certificate_string = json.dumps(certificate_with_signature, sort_keys=True).encode('utf-8')

    try:
        public_key.verify(
            signature,
            certificate_string,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.MGF1.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
