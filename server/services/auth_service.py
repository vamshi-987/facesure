from fastapi import HTTPException, status
from utils.audit_log import logger
from datetime import datetime, timedelta
from extensions.mongo import db

from security.passwords import verify_password
from security.jwt_tokens import create_access_token, create_refresh_token
from data.refresh_token_repo import store_refresh_token, revoke_refresh_token

from data.superadmin_repo import get_superadmin_by_id
from data.admin_repo import get_admin_by_id
from data.guards_repo import get_guard_by_id
from data.student_repo import get_student_by_id
from data.faculty_repo import get_faculty_by_id


from data.user_roles_repo import get_user_role
from data.roles_repo import get_role_by_id

from core.global_response import success


USER_LOOKUP_ORDER = [
    get_superadmin_by_id,
    get_admin_by_id,
    get_guard_by_id,
    get_faculty_by_id,
    get_student_by_id,
]


# ==========================================================
# LOGIN
# ==========================================================
def login(user_id: str, password: str):
    # Account lockout logic
    users_collection = db["users"] if "users" in db.list_collection_names() else None
    lockout_threshold = 5
    lockout_minutes = 15
    user_doc = None
    if users_collection:
        user_doc = users_collection.find_one({"_id": user_id})
        if user_doc:
            locked_until = user_doc.get("locked_until")
            if locked_until and datetime.utcnow() < locked_until:
                logger.log(user_id, 'login_failed', details='Account locked')
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account locked until {locked_until}"
                )

    user = None
    for fn in USER_LOOKUP_ORDER:
        doc = fn(user_id)
        if doc:
            user = doc
            break

    if not user:
        logger.log(user_id, 'login_failed', details='User not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not verify_password(user.get("password_hash", ""), password):
        # Increment failed attempts
        if users_collection and user_doc:
            failed_attempts = user_doc.get("failed_attempts", 0) + 1
            update_fields = {"failed_attempts": failed_attempts}
            if failed_attempts >= lockout_threshold:
                update_fields["locked_until"] = datetime.utcnow() + timedelta(minutes=lockout_minutes)
                logger.log(user_id, 'account_locked', details=f'Exceeded {lockout_threshold} failed attempts')
            users_collection.update_one({"_id": user_id}, {"$set": update_fields})
        logger.log(user_id, 'login_failed', details='Invalid password')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    mapping = get_user_role(user_id)
    if not mapping:
        logger.log(user_id, 'login_failed', details='No role assigned')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no role assigned"
        )

    role_doc = get_role_by_id(mapping["role_id"])
    role_name = role_doc["name"]

    access_token = create_access_token(user_id)
    refresh_token, jti = create_refresh_token(user_id)

    store_refresh_token(jti, user_id)

    response_data = {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "role": role_name,
    }   

    # 👇 ONLY STUDENT HAS FACE ID
    if role_name == "STUDENT":
        response_data["face_id"] = user.get("face_id")

    # Reset failed attempts on successful login
    if users_collection and user_doc:
        users_collection.update_one({"_id": user_id}, {"$set": {"failed_attempts": 0, "locked_until": None}})
    logger.log(user_id, 'login_success', details='Login successful')
    return success("Login successful", response_data)



# ==========================================================
# ROTATE REFRESH TOKEN
# ==========================================================
def rotate_refresh_token(old_jti: str, user_id: str):

    revoke_refresh_token(old_jti)

    new_access = create_access_token(user_id)
    new_refresh, new_jti = create_refresh_token(user_id)

    store_refresh_token(new_jti, user_id)

    return success(
        "Token refreshed",
        {
            "access_token": new_access,
            "refresh_token": new_refresh
        }
    )
