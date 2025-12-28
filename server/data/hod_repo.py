"""HOD compatibility module.

This module provides the same functions previously exposed by a standalone
`hods` collection. For backward compatibility it will:
 - Read / write to the `hods` collection if present
 - Fall back to `faculty`-based HOD helpers when no dedicated hods document exists

This resolves import errors like "No module named 'data.hod_repo'" and keeps
existing behavior intact during a migration to a single `faculty` collection.
"""

from extensions.mongo import db

# Local collection (may be empty or unused after migration)
hods = db["hods"]

# Helper: lazy import faculty helpers
def _faculty_helpers():
    from data.faculty_repo import (
        get_faculty_by_id as _get_faculty_by_id,
        get_all_hods as _get_all_hods,
        get_hods_by_college as _get_hods_by_college,
        filter_hods as _filter_hods,
        create_hod as _create_hod_faculty_alias,
        update_hod as _update_hod_faculty_alias,
        delete_hod as _delete_hod_faculty_alias,
    )
    return {
        "get_faculty_by_id": _get_faculty_by_id,
        "get_all_hods": _get_all_hods,
        "get_hods_by_college": _get_hods_by_college,
        "filter_hods": _filter_hods,
        "create_hod_alias": _create_hod_faculty_alias,
        "update_hod_alias": _update_hod_faculty_alias,
        "delete_hod_alias": _delete_hod_faculty_alias,
    }


def get_hod_by_id(hod_id: str):
    """Return HOD document. Prefer dedicated hods collection; fallback to faculty."""
    doc = hods.find_one({"_id": hod_id})
    if doc:
        return doc

    # fallback
    helpers = _faculty_helpers()
    return helpers["get_faculty_by_id"](hod_id)


def create_hod(doc: dict, session=None):
    """Create in `hods` collection (legacy). If you prefer faculty-backed HODs,
    use faculty helpers (this function preserves previous behavior)."""
    return hods.insert_one(doc, session=session)


def update_hod(hod_id: str, updates: dict, session=None):
    res = hods.update_one({"_id": hod_id}, {"$set": updates}, session=session)
    if res.matched_count:
        return res

    # If no legacy hod doc exists, update the faculty document instead
    helpers = _faculty_helpers()
    return helpers["update_hod_alias"](hod_id, updates, session=session)


def delete_hod(hod_id: str, session=None):
    res = hods.delete_one({"_id": hod_id}, session=session)
    if res.deleted_count:
        return res

    helpers = _faculty_helpers()
    return helpers["delete_hod_alias"](hod_id, session=session)


def get_all_hods():
    """Return list of HODs. If legacy collection is empty, return faculty-based HODs."""
    docs = list(hods.find({}).sort("_id", 1))
    if docs:
        return docs

    helpers = _faculty_helpers()
    return helpers["get_all_hods"]()


def filter_hods(filters: dict):
    """Filter HODs — prefer legacy collection when results exist, else fallback."""
    query = {}
    for key, value in filters.items():
        if value is None:
            continue
        if key in ["years", "courses"]:
            query[key] = {"$in": value if isinstance(value, list) else [value]}
        else:
            query[key] = value

    docs = list(hods.find(query).sort("_id", 1))
    if docs:
        return docs

    helpers = _faculty_helpers()
    return helpers["filter_hods"](filters)
