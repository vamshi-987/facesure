from fastapi import HTTPException, status
from pymongo.errors import PyMongoError

from data.roles_repo import create_role_if_not_exists
from data.superadmin_repo import get_superadmin_by_id, create_superadmin
from data.user_roles_repo import assign_role
from security.passwords import hash_password
from config import Config


def init_bootstrap():
    try:
        role_super = create_role_if_not_exists("SUPER_ADMIN")
        create_role_if_not_exists("ADMIN")
        create_role_if_not_exists("HOD")
        create_role_if_not_exists("GUARD")
        create_role_if_not_exists("STUDENT")
        create_role_if_not_exists("FACULTY")
        create_role_if_not_exists("MENTOR")

        # Load superadmin info from environment variables (set in .env)
        import os
        superadmin_id = os.getenv("SUPERADMIN_USERNAME")
        superadmin_password = os.getenv("SUPERADMIN_PASSWORD")
        superadmin_name = os.getenv("SUPERADMIN_NAME", "Super Admin")
        superadmin_phone = os.getenv("SUPERADMIN_PHONE", "9999999999")

        if superadmin_id and superadmin_password:
            existing = get_superadmin_by_id(superadmin_id)
            if not existing:
                create_superadmin({
                    "_id": superadmin_id,
                    "name": superadmin_name,
                    "phone": superadmin_phone,
                    "password_hash": hash_password(superadmin_password)
                })
                assign_role(superadmin_id, role_super["_id"])

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap initialization failed"
        )
