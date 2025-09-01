
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, g
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'verification.db'

# --- Database Functions ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# --- Verification Logic ---

def verify_certificate_signature(certificate_path):
    public_key_path = '../public_key.pem'
    if not os.path.exists(public_key_path):
        return False, "Public key not found on server."

    with open(public_key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())

    with open(certificate_path, "r") as f:
        try:
            cert_data = json.load(f)
        except json.JSONDecodeError:
            return False, "Invalid JSON format."

    signature_hex = cert_data.pop("signature", None)
    if not signature_hex:
        return False, "No signature found in certificate."

    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False, "Invalid signature format."

    # Recreate the message that was signed
    message = json.dumps(cert_data, sort_keys=True).encode('utf-8')

    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.MGF1.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True, "Certificate is authentic."
    except InvalidSignature:
        return False, "Signature is invalid. The certificate may have been tampered with."
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and file.filename.endswith('.json'):
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            is_valid, message = verify_certificate_signature(filepath)

            # Log the attempt
            db = get_db()
            db.execute(
                'INSERT INTO verifications (filename, verified_at, is_authentic, result_message) VALUES (?, ?, ?, ?)',
                (file.filename, datetime.utcnow(), is_valid, message)
            )
            db.commit()

            return render_template('result.html', is_valid=is_valid, message=message, filename=file.filename)

    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db() # Initialize the database if it doesn't exist
    app.run(debug=True)
