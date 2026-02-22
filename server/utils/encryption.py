from cryptography.fernet import Fernet
from config import Config
import base64
import json

cipher = Fernet(Config.FACE_ENCRYPTION_KEY.encode())

def encrypt_embedding(embedding_list):
    data = json.dumps(embedding_list).encode()
    encrypted = cipher.encrypt(data)
    return base64.b64encode(encrypted).decode()

def decrypt_embedding(encrypted_str):
    encrypted = base64.b64decode(encrypted_str.encode())
    decrypted = cipher.decrypt(encrypted)
    return json.loads(decrypted.decode())

def encrypt_image_bytes(image_bytes):
    return cipher.encrypt(image_bytes)

def decrypt_image_bytes(encrypted_bytes):
    return cipher.decrypt(encrypted_bytes)
