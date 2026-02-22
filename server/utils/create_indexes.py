from extensions.mongo import db

def create_all_indexes():
    """Create all required indexes for optimal performance"""
    # Users collection - frequent lookups by ID and phone
    db.students.create_index("_id")
    db.students.create_index("phone", unique=True)
    db.students.create_index("email", unique=True, sparse=True)
    db.students.create_index("face_id")
    db.students.create_index([("department", 1), ("year", 1)])

    db.admins.create_index("_id")
    db.admins.create_index("phone", unique=True)

    db.faculty.create_index("_id")
    db.faculty.create_index("phone", unique=True)
    db.faculty.create_index("department")

    # Face collections - critical for performance
    db.faces.create_index("user_id", unique=True)
    db.faces.create_index("user_type")
    db.faces.create_index("created_at")

    # Face vectors - already has vector search index, but add this
    db.face_vectors.create_index("user_id", unique=True)

    # Refresh tokens - for quick validation
    db.refresh_tokens.create_index("jti", unique=True)
    db.refresh_tokens.create_index([("user_id", 1), ("jti", 1)])
    db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)  # TTL index

    # User roles - frequently joined data
    db.user_roles.create_index("user_id", unique=True)
    db.user_roles.create_index("role_id")

    # Audit logs - for security monitoring (with TTL)
    db.audit_logs.create_index([("timestamp", -1)])
    db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
    db.audit_logs.create_index("event_type")
    db.audit_logs.create_index("timestamp", expireAfterSeconds=7776000)  # 90 days retention

    # Requests (gate pass, etc.)
    db.requests.create_index([("student_id", 1), ("created_at", -1)])
    db.requests.create_index([("status", 1), ("created_at", -1)])
    db.requests.create_index("created_at")

    # Mentor mappings
    db.student_mentor.create_index("student_id", unique=True)
    db.student_mentor.create_index("mentor_id")

    # HOD mappings
    db.student_hod.create_index("student_id", unique=True)
    db.student_hod.create_index("hod_id")

    print("✅ All indexes created successfully")

if __name__ == "__main__":
    create_all_indexes()
