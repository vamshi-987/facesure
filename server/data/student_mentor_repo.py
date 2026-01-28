from extensions.mongo import db
from datetime import datetime

student_mentor = db["student_mentor_mapping"]


def get_existing_mentor_ids_for_students(student_ids):
    return student_mentor.distinct(
        "mentor_id",
        {"student_id": {"$in": student_ids}}
    )


def delete_student_mentor_mappings_by_students(student_ids, session=None):
    return student_mentor.delete_many(
        {"student_id": {"$in": student_ids}},
        session=session
    )


def insert_student_mentor_mappings(docs, session=None):
    return student_mentor.insert_many(docs, session=session)

def map_student_to_mentor(student_id: str, mentor_id: str, college: str, year: int, course: str, section: str, session=None):
    """Create a single student-mentor mapping"""
    return student_mentor.insert_one({
        "student_id": student_id,
        "mentor_id": mentor_id,
        "college": college,
        "year": year,
        "course": course,
        "section": section,
        "created_at": datetime.utcnow()
    }, session=session)


def get_all_mentor_mappings():
    """
    Returns DISTINCT mentor → course/year/section assignments.
    Avoids duplicates caused by multiple students.
    """
    pipeline = [
        {
            "$group": {
                "_id": {
                    "mentor_id": "$mentor_id",
                    "course": "$course",
                    "year": "$year",
                    "section": "$section"
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "mentor_id": "$_id.mentor_id",
                "course": "$_id.course",
                "year": "$_id.year",
                "section": "$_id.section"
            }
        }
    ]

    return list(student_mentor.aggregate(pipeline))


def get_mentors_for_scope(college: str, year: int, course: str, section: str):
    """Get all mentor IDs assigned to a specific course/year/section"""
    return student_mentor.distinct(
        "mentor_id",
        {
            "college": college,
            "year": year,
            "course": course,
            "section": section
        }
    )


def get_students_for_mentor(mentor_id: str):
    """
    Returns list of student_ids mapped to a mentor
    Used by mentor request approval flow
    """
    results = student_mentor.distinct(
        "student_id",
        {"mentor_id": mentor_id}
    )
    return results
