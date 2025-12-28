# data/hod_mentor_repo.py
from extensions.mongo import db

hod_mentor = db["hod_mentor"]

def create_hod_mentor_mapping(doc, session=None):
    return hod_mentor.insert_one(doc, session=session)

def delete_hod_mentor_mappings(hod_id, year, course, college, session=None):
    return hod_mentor.delete_many(
        {
            "hod_id": hod_id,
            "year": year,
            "course": course,
            "college": college
        },
        session=session
    )


def get_hod_for_year_course(college, year, course):
    return hod_mentor.find_one(
        {
            "college": college,
            "year": year,
            "course": course
        }
    )

def delete_hod_mentor_mappings_for_scope(
    hod_id: str,
    college: str,
    year: int,
    course: str,
    session=None
):
    """
    Deletes ONLY HOD → mentor mappings
    for a specific (college, year, course).

    ✔ Does NOT touch other years
    ✔ Does NOT touch other courses
    ✔ Does NOT affect mentor assignments
    ✔ Safe for partial HOD reassignment
    """

    query = {
        "hod_id": hod_id,
        "college": college,
        "year": year,
        "course": course
    }

    return hod_mentor.delete_many(
        query,
        session=session
    )