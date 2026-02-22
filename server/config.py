
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    FACE_ENCRYPTION_KEY = os.getenv("FACE_ENCRYPTION_KEY")
    # Remove hardcoded superadmin credentials. Manage superadmins securely (e.g., via environment, admin panel, or secure vault)
