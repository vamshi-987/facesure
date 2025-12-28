from extensions.mongo import db

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


def get_students_for_mentor(mentor_id: str):
    """
    Returns list of student_ids mapped to a mentor
    Used by mentor request approval flow
    """
    return student_mentor.distinct(
        "student_id",
        {"mentor_id": mentor_id}
    )
