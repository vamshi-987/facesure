from extensions.mongo import db

# Utility to find duplicates in a collection for a given field

def find_duplicates(collection, field):
    pipeline = [
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}, "docs": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}, "_id": {"$ne": None}}}
    ]
    return list(collection.aggregate(pipeline))

# Utility to remove all but one duplicate for each value

def remove_duplicates(collection, field):
    duplicates = find_duplicates(collection, field)
    for dup in duplicates:
        # Keep the first document, remove the rest
        ids_to_remove = dup["docs"][1:]
        collection.delete_many({"_id": {"$in": ids_to_remove}})
        print(f"Removed {len(ids_to_remove)} duplicates for {field}: {dup['_id']}")

if __name__ == "__main__":
    # Example: Remove duplicates for phone and email in students, admins, faculty
    print("Checking students for phone duplicates...")
    remove_duplicates(db.students, "phone")
    print("Checking students for email duplicates...")
    remove_duplicates(db.students, "email")

    print("Checking admins for phone duplicates...")
    remove_duplicates(db.admins, "phone")

    print("Checking faculty for phone duplicates...")
    remove_duplicates(db.faculty, "phone")
    print("Checking faculty for email duplicates...")
    remove_duplicates(db.faculty, "email")

    print("Duplicate cleanup complete.")
