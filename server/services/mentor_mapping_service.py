import math
from datetime import datetime
from fastapi import HTTPException

from core.global_response import success
from extensions.mongo import client

from data.student_repo import get_students_by_college_year_course_section
from data.student_mentor_repo import (
    delete_student_mentor_mappings_by_students,
    get_existing_mentor_ids_for_students,
    insert_student_mentor_mappings,
    get_all_mentor_mappings
)

from data.roles_repo import get_role_by_name
from data.user_roles_repo import assign_role, delete_specific_role


# ==========================================================
# ASSIGN MENTORS (ROLE SWITCH LOGIC)
# ==========================================================
def assign_mentors_service(payload):

    # --------------------------------------------------
    # 1️⃣ Basic validation
    # --------------------------------------------------
    if len(payload.mentor_ids) != 2:
        raise HTTPException(400, "Exactly 2 mentors must be selected")

    students = get_students_by_college_year_course_section(
        payload.college,
        payload.year,
        payload.course,
        payload.section
    )

    if not students:
        raise HTTPException(404, "No students found")

    student_ids = [s["_id"] for s in students]

    # --------------------------------------------------
    # 2️⃣ Role validation
    # --------------------------------------------------
    mentor_role = get_role_by_name("MENTOR")
    faculty_role = get_role_by_name("FACULTY")

    if not mentor_role or not faculty_role:
        raise HTTPException(500, "Role configuration missing")

    mentor_role_id = mentor_role["_id"]
    faculty_role_id = faculty_role["_id"]

    # --------------------------------------------------
    # 3️⃣ Transaction
    # --------------------------------------------------
    with client.start_session() as s:
        with s.start_transaction():

            # ------------------------------------------
            # 3️⃣ Fetch old mentors
            # ------------------------------------------
            old_mentor_ids = get_existing_mentor_ids_for_students(student_ids)

            # ------------------------------------------
            # 4️⃣ Delete old mappings
            # ------------------------------------------
            delete_student_mentor_mappings_by_students(
                student_ids,
                session=s
            )

            # ------------------------------------------
            # 5️⃣ OLD mentors → back to FACULTY
            # ------------------------------------------
            for mid in old_mentor_ids:
                # Remove mentor role
                delete_specific_role(mid, mentor_role_id, session=s)

                # Restore faculty role
                assign_role(
                    user_id=mid,
                    role_id=faculty_role_id,
                    session=s
                )

            # ------------------------------------------
            # 6️⃣ Create new mappings (roll split)
            # ------------------------------------------
            half = math.ceil(len(students) / 2)
            mappings = []

            for i, student in enumerate(students):
                mentor_id = (
                    payload.mentor_ids[0]
                    if i < half
                    else payload.mentor_ids[1]
                )

                mappings.append({
                    "student_id": student["_id"],
                    "mentor_id": mentor_id,
                    "college": payload.college,
                    "year": payload.year,
                    "course": payload.course,
                    "section": payload.section,
                    "created_at": datetime.utcnow()
                })

            insert_student_mentor_mappings(mappings, session=s)

            # ------------------------------------------
            # 7️⃣ NEW mentors → MENTOR ONLY
            # ------------------------------------------
            for mentor_id in payload.mentor_ids:
                # Remove faculty role
                delete_specific_role(
                    mentor_id,
                    faculty_role_id,
                    session=s
                )

                # Assign mentor role
                assign_role(
                    user_id=mentor_id,
                    role_id=mentor_role_id,
                    session=s
                )

    return success("Mentors assigned and roles updated successfully")


# ==========================================================
# GET ALL MENTOR MAPPINGS
# ==========================================================
def service_get_all_mentor_mappings():
    mappings = get_all_mentor_mappings()
    return success("Mentor mappings fetched", mappings)
