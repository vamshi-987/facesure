# services/hod_assignment_service.py
from datetime import datetime
from fastapi import HTTPException
from extensions.mongo import client, db
from core.global_response import success

from data.faculty_repo import get_faculty_by_id
from data.student_hod_repo import (
    map_student_to_hod,
    delete_hod_mappings_for_scope,
    get_hod_assignments
)
from data.hod_mentor_repo import (
    get_hod_for_year_course,
    delete_hod_mentor_mappings_for_scope,
    create_hod_mentor_mapping
)
from data.roles_repo import get_role_by_name
from data.user_roles_repo import assign_role, delete_specific_role


def assign_hod_service(payload):
    faculty_id = payload.faculty_id
    college = payload.college
    years = payload.years
    courses = payload.courses

    faculty = get_faculty_by_id(faculty_id)
    if not faculty:
        raise HTTPException(404, "Faculty not found")

    hod_role = get_role_by_name("HOD")
    faculty_role = get_role_by_name("FACULTY")

    with client.start_session() as s:
        with s.start_transaction():

            for year in years:
                for course in courses:

                    # 🔴 REMOVE OLD HOD (ONLY THIS SCOPE)
                    old = get_hod_for_year_course(college, year, course)
                    if old:
                        old_hod = old["hod_id"]

                        delete_hod_mappings_for_scope(
                            old_hod, college, year, course, session=s
                        )
                        delete_hod_mentor_mappings_for_scope(
                            old_hod, college, year, course, session=s
                        )

                        delete_specific_role(
                            old_hod, hod_role["_id"], session=s
                        )
                        assign_role(
                            old_hod, faculty_role["_id"], session=s
                        )

                    # 🟢 ASSIGN HOD ROLE (IDEMPOTENT)
                    delete_specific_role(
                        faculty_id, faculty_role["_id"], session=s
                    )
                    assign_role(
                        faculty_id, hod_role["_id"], session=s
                    )

                    # 🟢 MAP STUDENTS (ONLY SELECTED COHORT)
                    students = db["students"].find(
                        {
                            "college": college,
                            "year": year,
                            "course": course
                        },
                        session=s
                    )

                    for st in students:
                        map_student_to_hod(
                            student_id=st["_id"],
                            hod_id=faculty_id,
                            college=college,
                            year=year,
                            course=course,
                            session=s
                        )

                    # 🟢 MAP MENTORS (DERIVED FROM STUDENT_MENTOR)
                    mentor_ids = db["student_mentor_mapping"].distinct(
                        "mentor_id",
                        {
                            "college": college,
                            "year": year,
                            "course": course
                        }
                    )

                    for mid in mentor_ids:
                        create_hod_mentor_mapping(
                            {
                                "hod_id": faculty_id,
                                "mentor_id": mid,
                                "college": college,
                                "year": year,
                                "course": course,
                                "created_at": datetime.utcnow()
                            },
                            session=s
                        )

    return success("HOD assigned successfully")

def get_hod_assignments_service(hod_id):
    return success(
        "HOD assignments",
        list(get_hod_assignments(hod_id))
    )
