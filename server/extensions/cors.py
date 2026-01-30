# extensions/cors.py
from fastapi.middleware.cors import CORSMiddleware

def init_cors(app):
    app.add_middleware(
        CORSMiddleware,
        # Allow common local dev origins. Add more origins via env when needed.
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
