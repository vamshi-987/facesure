
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    FACE_ENCRYPTION_KEY = os.getenv("FACE_ENCRYPTION_KEY")
    FACE_EXECUTOR_MAX_WORKERS = int(os.getenv("FACE_EXECUTOR_MAX_WORKERS", "4"))
    FACE_INFERENCE_CONCURRENCY = int(os.getenv("FACE_INFERENCE_CONCURRENCY", "2"))
    FACE_INFERENCE_TIMEOUT_SECONDS = float(os.getenv("FACE_INFERENCE_TIMEOUT_SECONDS", "8"))
    FACE_MIN_WIDTH = int(os.getenv("FACE_MIN_WIDTH", "320"))
    FACE_MIN_HEIGHT = int(os.getenv("FACE_MIN_HEIGHT", "320"))
    FACE_MIN_BRIGHTNESS = float(os.getenv("FACE_MIN_BRIGHTNESS", "35"))
    FACE_MAX_BRIGHTNESS = float(os.getenv("FACE_MAX_BRIGHTNESS", "220"))
    # Remove hardcoded superadmin credentials. Manage superadmins securely (e.g., via environment, admin panel, or secure vault)
