from datetime import datetime
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status

from security.passwords import hash_password
from schemas.faculty_schema import Faculty as FacultySchema
from data.faculty_repo import (
    create_faculty as repo_create,
    get_faculty_by_id,
    update_faculty as repo_update,
    delete_faculty as repo_delete,
    get_all_faculty,
    get_faculty_by_college,
    filter_faculty
)
from data.roles_repo import get_role_by_name
from extensions.mongo import client, db
from core.global_response import success


# ==================================================
# REGISTER FACULTY
# ==================================================
def register_faculty(
    faculty_id: str,
    name: str,
    phone: str,
    email: str,
    password: str,
    college: str,
    years: list,
    courses: list
):
    if get_faculty_by_id(faculty_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{faculty_id} already exists"
        )

    faculty_doc = FacultySchema(
        _id=faculty_id,
        name=name,
        phone=phone,
        email=email,
        college=college,
        years=years,
        courses=courses,
        password_hash=hash_password(password)
    ).model_dump(by_alias=True)

    try:
        with client.start_session() as s:
            with s.start_transaction():

                repo_create(faculty_doc, session=s)

                role = get_role_by_name("FACULTY")
                db["user_roles"].insert_one(
                    {
                        "user_id": faculty_id,
                        "role_id": role["_id"],
                        "assigned_at": datetime.utcnow()
                    },
                    session=s
                )

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Faculty registration failed"
        )

    return success("Faculty registered successfully", {"faculty_id": faculty_id})


# ==================================================
# GET FACULTY BY ID
# ==================================================
def service_get_faculty_by_id(faculty_id: str):
    faculty = get_faculty_by_id(faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    faculty.pop("password_hash", None)
    return success("Faculty profile fetched", faculty)


# ==================================================
# UPDATE FACULTY
# ==================================================
def update_faculty_service(faculty_id: str, updates: dict):
    faculty = get_faculty_by_id(faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))

    try:
        with client.start_session() as s:
            with s.start_transaction():
                repo_update(faculty_id, updates, session=s)

    except PyMongoError:
        raise HTTPException(status_code=500, detail="Faculty update failed")

    updated = get_faculty_by_id(faculty_id)
    updated.pop("password_hash", None)
    return success("Faculty updated successfully", updated)


# ==================================================
# DELETE FACULTY
# ==================================================
def delete_faculty_service(faculty_id: str):
    if not get_faculty_by_id(faculty_id):
        raise HTTPException(status_code=404, detail="Faculty not found")

    try:
        with client.start_session() as s:
            with s.start_transaction():
                repo_delete(faculty_id, session=s)
                db["user_roles"].delete_many(
                    {"user_id": faculty_id},
                    session=s
                )

    except PyMongoError:
        raise HTTPException(status_code=500, detail="Faculty deletion failed")

    return success("Faculty deleted successfully")


# ==================================================
# GET ALL FACULTY
# ==================================================
def service_get_all_faculty():
    faculty = get_all_faculty()
    for f in faculty:
        f.pop("password_hash", None)
    return success("All faculty retrieved", faculty)


# ==================================================
# GET FACULTY BY COLLEGE
# ==================================================
def service_get_faculty_by_college(college: str):
    faculty = get_faculty_by_college(college)
    for f in faculty:
        f.pop("password_hash", None)
    return success("Faculty by college", faculty)


# ==================================================
# FILTER FACULTY
# ==================================================
def filter_faculty_service(filters: dict):
    faculty = filter_faculty(filters)
    for f in faculty:
        f.pop("password_hash", None)
    return success("Filtered faculty", faculty)
