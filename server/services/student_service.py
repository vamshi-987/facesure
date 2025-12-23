import cv2
from datetime import datetime
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status

from security.passwords import hash_password
from schemas.student_schema import Student as StudentSchema

from data.student_repo import (
    get_student_by_id as repo_get_student_by_id, 
    update_student as repo_update_student,
    delete_student as repo_delete_student,
    filter_students as filter_students_repo,
    promote_students_year_repo,
    get_students_by_year_and_college
)

from data.roles_repo import get_role_by_name
from data.faces_repo import get_face_by_user, delete_face, create_face_doc
from data.face_vectors_repo import create_vector, delete_vector, search_similar_faces
from data.student_hod_repo import map_student_to_hod, delete_student_mappings
from data.hod_repo import get_all_hods
from extensions.mongo import client, db
from services.validators import validate_college
from services.face_service import decode_image, extract_embedding_and_landmarks, DUPLICATE_HIGH
from core.global_response import success

# ==========================================================
# CREATE STUDENT
# ==========================================================
def register_student(student_id, name, phone, year, course, section, college, password, created_by):
    validate_college(college)
    if repo_get_student_by_id(student_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student already exists")

    student_doc = StudentSchema(
        _id=student_id, name=name, phone=phone, year=year,
        course=course, section=section, college=college,
        created_by=created_by, password_hash=hash_password(password),
        face_id=None
    ).model_dump(by_alias=True)

    try:
        with client.start_session() as s:
           with s.start_transaction():
            db["students"].insert_one(student_doc, session=s)

            role = get_role_by_name("STUDENT")
            db["user_roles"].insert_one({
                "user_id": student_id,
                "role_id": role["_id"],
                "assigned_at": datetime.utcnow()
            }, session=s)

            # ✅ CREATE STUDENT–HOD MAPPINGS
            hods = get_all_hods()
            for h in hods:
                if (
                    h["college"] == college
                    and year in h["years"]          # int vs int
                    and course in h["courses"]
                ):
                    map_student_to_hod(
                        student_id,
                        h["_id"],
                        year,
                        course,
                        college,
                        session=s                   # 🔑 pass session
                    )

    except PyMongoError:
        raise HTTPException(status_code=500, detail="Student creation failed")
    return success("Student created successfully", {"student_id": student_id})

# ==========================================================
# REGISTER FACE
# ==========================================================
def register_student_face_service(student_id: str, image_b64: str):
    student = repo_get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.get("face_id"):
        raise HTTPException(status_code=409, detail="Face already registered")

    img, _ = decode_image(image_b64)
    emb, _, _ = extract_embedding_and_landmarks(img)
    emb_list = emb.tolist()
    matches = search_similar_faces(emb_list)
    for m in matches:
        if m["score"] >= DUPLICATE_HIGH:
            raise HTTPException(status_code=409, detail=f"Duplicate face detected")

    vector_id = f"vec_{student_id}"
    try:
        with client.start_session() as s:
            with s.start_transaction():
                create_vector(vector_id, student_id, emb_list, session=s)
                ok, buf = cv2.imencode(".jpg", img)
                face_id = create_face_doc(student_id, "STUDENT", buf.tobytes(), vector_id, session=s)
                db["students"].update_one({"_id": student_id}, {"$set": {"face_id": face_id}}, session=s)
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Face registration failed")
    return success("Face registered successfully")

# ==========================================================
# UPDATE STUDENT (RESTORED)
# ==========================================================
def update_student_service(student_id, updates):
    student = repo_get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    sensitive_fields = {"year", "course", "college"}
    needs_remap = any(f in updates for f in sensitive_fields)

    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))

    try:
        with client.start_session() as s:
            with s.start_transaction():
                repo_update_student(student_id, updates, session=s)

                if needs_remap:
                    delete_student_mappings(student_id, session=s)

                    updated = repo_get_student_by_id(student_id)

                    hods = get_all_hods()
                    for h in hods:
                        if (
                            h["college"] == updated["college"]
                            and updated["year"] in h["years"]
                            and updated["course"] in h["courses"]
                        ):
                            map_student_to_hod(
                                student_id,
                                h["_id"],
                                updated["year"],
                                updated["course"],
                                updated["college"],
                                session=s
                            )

    except PyMongoError:
        raise HTTPException(status_code=500, detail="Student update failed")

    updated = repo_get_student_by_id(student_id)
    updated.pop("password_hash", None)
    return success("Student updated successfully", updated)


# ==========================================================
# DELETE STUDENT
# ==========================================================
def delete_student_service(student_id):
    face = get_face_by_user(student_id)
    try:
        with client.start_session() as s:
          with s.start_transaction():
            if face:
                if face.get("vector_ref"):
                    delete_vector(face["vector_ref"], session=s)
                delete_face(face["_id"], session=s)

            repo_delete_student(student_id, session=s)
            delete_student_mappings(student_id, session=s)
            db["user_roles"].delete_many({"user_id": student_id}, session=s)

    except PyMongoError:
        raise HTTPException(status_code=500, detail="Delete failed")
    delete_student_mappings(student_id)
    return success("Student deleted successfully")

# ==========================================================
# GET STUDENT
# ==========================================================
def get_student_service(student_id: str):
    student = repo_get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.pop("password_hash", None)
    return success("Student fetched", student)

# ==========================================================
# OTHERS
# ==========================================================
def filter_students_service(filters: dict):
    return success("Filtered students", filter_students_repo(filters))

def promote_students_service(year: str, college: str, new_year: str):
    promote_students_year_repo(year, college, new_year)
    return success("Students promoted successfully")