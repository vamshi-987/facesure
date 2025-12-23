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

        for sa in Config.SUPERADMINS:
            existing = get_superadmin_by_id(sa["_id"])
            if existing:
                continue

            create_superadmin({
                "_id": sa["_id"],
                "name": sa["name"],
                "phone": sa["phone"],
                "password_hash": hash_password(sa["password"])
            })

            assign_role(sa["_id"], role_super["_id"])

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap initialization failed"
        )
