from extensions.mongo import db

faculty = db["faculty"]

# =========================
# CREATE
# =========================
def create_faculty(doc: dict, session=None):
    return faculty.insert_one(doc, session=session)

# =========================
# GET BY ID
# =========================
def get_faculty_by_id(faculty_id: str):
    return faculty.find_one({"_id": faculty_id})

# =========================
# UPDATE
# =========================
def update_faculty(faculty_id: str, updates: dict, session=None):
    return faculty.update_one(
        {"_id": faculty_id},
        {"$set": updates},
        session=session
    )

# =========================
# DELETE
# =========================
def delete_faculty(faculty_id: str, session=None):
    return faculty.delete_one(
        {"_id": faculty_id},
        session=session
    )

# =========================
# GET ALL
# =========================
def get_all_faculty():
    return list(faculty.find().sort("_id", 1))

# =========================
# GET BY COLLEGE
# =========================
def get_faculty_by_college(college: str):
    return list(
        faculty.find(
            {"college": college, "active": True}
        ).sort("_id", 1)
    )

# =========================
# CUSTOM FILTER
# =========================
def filter_faculty(filters: dict):
    query = {k: v for k, v in filters.items() if v is not None}
    return list(faculty.find(query).sort("_id", 1))


# ---------------------------------------------------------
# HOD compatibility shims
# These helpers are provided so existing HOD-based code can
# operate on `faculty` documents without immediate refactors.
# They are deliberate compatibility layers and can be
# replaced with role-aware queries later.
# ---------------------------------------------------------




def _hod_user_ids():
    """Return list of user_ids that are currently assigned the HOD role."""
    role = db["roles"].find_one({"name": "HOD"})
    if not role:
        return []
    cursor = db["user_roles"].find({"role_id": role["_id"]}, {"user_id": 1})
    return [r["user_id"] for r in cursor]


def get_hod_by_id(hod_id: str):
    """Return faculty document only if the user has HOD role assigned."""
    role = db["roles"].find_one({"name": "HOD"})
    if not role:
        return None
    mapping = db["user_roles"].find_one({"user_id": hod_id, "role_id": role["_id"]})
    if not mapping:
        return None
    return get_faculty_by_id(hod_id)



def get_all_hods():
    """Return list of faculty documents that are assigned the HOD role."""
    ids = _hod_user_ids()
    if not ids:
        return []
    return list(faculty.find({"_id": {"$in": ids}}).sort("_id", 1))


def get_hods_by_college(college: str):
    """Return HODs filtered by `college`."""
    ids = _hod_user_ids()
    if not ids:
        return []
    return list(
        faculty.find({"_id": {"$in": ids}, "college": college, "active": True}).sort("_id", 1)
    )


def filter_hods(filters: dict):
    """Filter HODs using the same filters as `filter_faculty` but scoped to HODs."""
    query = {k: v for k, v in filters.items() if v is not None}
    ids = _hod_user_ids()
    if not ids:
        return []
    query["_id"] = {"$in": ids}
    return list(faculty.find(query).sort("_id", 1))



