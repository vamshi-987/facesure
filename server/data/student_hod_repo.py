from extensions.mongo import db

student_hod = db["student_hod"]

# ==========================================================
# CREATE / UPDATE MAPPING
# ==========================================================
def map_student_to_hod(
    student_id: str,
    hod_id: str,
    year: int,
    course: str,
    college: str,
    session=None
):
    doc = {
        "student_id": student_id,
        "hod_id": hod_id,
        "year": year,          # ✅ FIXED (actual value)
        "course": course,
        "college": college
    }

    student_hod.update_one(
        {"student_id": student_id, "hod_id": hod_id},
        {"$set": doc},
        upsert=True,
        session=session
    )


# ==========================================================
# READ
# ==========================================================
def get_hods_for_student(student_id: str):
    return list(student_hod.find({"student_id": student_id}))


def get_students_for_hod(hod_id: str):
    return list(student_hod.find({"hod_id": hod_id}))


# ==========================================================
# DELETE
# ==========================================================
def delete_student_mappings(student_id: str, session=None):
    return student_hod.delete_many(
        {"student_id": student_id},
        session=session
    )


def delete_hod_mappings(hod_id, year, course, college, session=None):
    return student_hod.delete_many(
        {
            "hod_id": hod_id,
            "year": year,
            "course": course,
            "college": college
        },
        session=session
    )

# data/student_hod_repo.py
def get_hod_assignments(hod_id):
    return student_hod.aggregate([
        {
            "$group": {
                "_id": {
                    "college": "$college",
                    "year": "$year",
                    "course": "$course"
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "college": "$_id.college",
                "year": "$_id.year",
                "course": "$_id.course"
            }
        }
    ])

def delete_hod_mappings_for_scope(
    hod_id: str,
    college: str,
    year: int,
    course: str,
    session=None
):
    """
    Deletes ONLY the HOD → student mappings
    for a specific (college, year, course) scope.

    ✔ Safe
    ✔ Scoped
    ✔ Does NOT affect other HOD assignments
    """

    query = {
        "hod_id": hod_id,
        "college": college,
        "year": year,
        "course": course
    }

    return student_hod.delete_many(
        query,
        session=session
    )
