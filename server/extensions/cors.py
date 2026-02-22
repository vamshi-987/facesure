# extensions/cors.py
from fastapi.middleware.cors import CORSMiddleware

def init_cors(app):
    import os
    ENV = os.environ.get("ENV", "development")
    if ENV == "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://facesure.com", "https://www.facesure.com"],  # Set your real domains
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
