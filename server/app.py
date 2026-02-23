from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
import uuid
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import JSONResponse
# from fastapi.staticfiles import StaticFiles
import os
import socket
import sentry_sdk
from pythonjsonlogger import jsonlogger
import logging

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from extensions.cors import init_cors
from services.bootstrap_service import init_bootstrap
from core.global_response import error
from core.global_exception_handler import init_exception_handlers

# Routers
from routes.auth_routes import router as auth_router
from routes.admin_routes import router as admin_router
from routes.face_routes import router as face_router
from routes.student_routes import router as student_router
from routes.hod_routes import router as hod_router
from routes.guard_routes import router as guard_router
from routes.request_routes import router as request_router
from routes.mentor_mapping_routes import router as mentor_mapping_router
from routes.faculty_routes import router as faculty_router

app = FastAPI(title="FaceAuth System", version="2.0")
instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Sentry initialization
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN", ""))

# Structured JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.responses import Response

# Security Headers Middleware
# Security Headers Middleware

# Request ID Tracing Middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self';"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.scheme == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url)
        return await call_next(request)


if os.environ.get("ENV", "development") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)



# ---------------------------------------------------------
#  CORS + STATIC
# ---------------------------------------------------------
init_cors(app)
init_exception_handlers(app)

# app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------------
#  ROUTES
# ---------------------------------------------------------

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(face_router)
app.include_router(student_router)
app.include_router(hod_router)
app.include_router(guard_router)
app.include_router(request_router)
app.include_router(mentor_mapping_router)
app.include_router(faculty_router)
app.include_router(admin_router, prefix="/super_admin") # Handles /super_admin/...



# ---------------------------------------------------------
#  STARTUP WITH SERVER URL PRINT
# ---------------------------------------------------------
@app.on_event("startup")
async def on_start():
    init_bootstrap()

    # Detect machine IP (LAN)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # SMS config (for parent leave notifications)
    sms_enabled = str(os.environ.get("SMS_ENABLED", "")).lower() in ("true", "1", "yes")
    sms_provider = os.environ.get("SMS_PROVIDER", "msg91")
    sms_key = os.environ.get("FAST2SMS_API_KEY") or os.environ.get("MSG91_AUTH_KEY") or ""
    sms_ok = sms_key and not sms_key.startswith("REPLACE_")

    print("\n" + "="*60)
    print("🚀 FASTAPI SERVER STARTED SUCCESSFULLY")
    print(f"🔹 Local Address:     http://127.0.0.1:5000")
    print(f"🔹 LAN Address:       http://{local_ip}:5000")
    print(f"🔹 API Docs (Swagger): http://{local_ip}:5000/docs")
    print(f"🔹 ReDoc Docs:         http://{local_ip}:5000/redoc")
    print(f"🔹 Static Files:       http://{local_ip}:5000/static")
    print(f"🔹 SMS:               {'ON' if sms_enabled else 'OFF'} ({sms_provider})" + (" [key set]" if sms_ok else " [key missing/placeholder]"))
    print("="*60 + "\n")



# Health check endpoint
# Health check endpoint

# API Key validation dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.environ.get("API_SECRET_KEY", "supersecret"):
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return {"message": "Server running"}

# Example protected endpoint
@app.get("/protected")
async def protected(api_key: str = Security(get_api_key)):
    return {"message": "You accessed a protected endpoint!"}
