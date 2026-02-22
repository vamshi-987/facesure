from fastapi import APIRouter, Depends, Request
from security.dependencies import require_roles
from services.face_service import (
    verify_then_replace_face,
    verify_face_for_user
)
from services.face_validation_service import validate_and_cache_face
from schemas.api_request_models import (
    FaceReplaceRequest,
    FaceVerifyRequest,
    FaceValidateRequest
)
from core.global_response import success

# Rate Limiting
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter



router = APIRouter(prefix="/face", tags=["Face Biometrics"])
limiter = Limiter(key_func=get_remote_address)


# ==========================================================
# 1. FACE REGISTRATION
# ==========================================================
@router.post("/register")
@limiter.limit("5/minute")
def register_face_route(request: Request,
    payload: FaceReplaceRequest,
    _=Depends(require_roles("STUDENT", "HOD", "GUARD", "ADMIN", "SUPER_ADMIN"))
):
    """
    Registers or replaces a user's face biometric.
    Enforces:
    - Exactly one face
    - No duplicate faces globally
    """
    verify_then_replace_face(
        user_id=payload.user_id,
        user_type=payload.user_type,
        b64=payload.image_b64
    )

    return success("Face registered successfully")


# ==========================================================
# 2. FACE VERIFICATION
# ==========================================================
@router.post("/verify")
@limiter.limit("10/minute")
def verify_face_route(request: Request,
    payload: FaceVerifyRequest,
    _=Depends(require_roles("STUDENT", "HOD", "GUARD", "ADMIN", "SUPER_ADMIN"))
):
    """
    Verifies a captured face against the stored biometric
    of the given user.
    """
    ok, score = verify_face_for_user(
        user_id=payload.user_id,
        b64=payload.image_b64
    )

    return success(
        "Face verified" if ok else "Face mismatch",
        {"verified": ok, "score": score}
    )


# ==========================================================
# 3. FACE QUALITY VALIDATION (Pre-check)
# ==========================================================
@router.post("/validate")
@limiter.limit("10/minute")
def validate_face_route(request: Request, payload: FaceValidateRequest):
    """
    Validates face quality before registration.
    Ensures:
    - Exactly one face
    - No global duplicate
    """
    ok, token = validate_and_cache_face(payload.image_b64)
    return success("Face validated", {"face_token": token})


# ==========================================================
# 4. VERIFY & REPLACE (SECURE UPDATE)
# ==========================================================
@router.post("/verify-replace")
@limiter.limit("5/minute")
def verify_and_replace_face_route(request: Request,
    payload: FaceReplaceRequest,
    _=Depends(require_roles("STUDENT", "HOD", "GUARD", "ADMIN", "SUPER_ADMIN"))
):
    """
    Verifies ownership before replacing existing biometric.
    """
    verify_then_replace_face(
        user_id=payload.user_id,
        user_type=payload.user_type,
        b64=payload.image_b64
    )

    return success("Face biometric updated successfully")
