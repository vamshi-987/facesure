from extensions.mongo import db
from utils.encryption import encrypt_image_bytes
from bson import ObjectId

def migrate_faces():
    count = 0
    for doc in db["faces"].find({"is_encrypted": {"$ne": True}}):
        face_id = doc["_id"]
        image_bytes = doc["image_data"]
        encrypted = encrypt_image_bytes(image_bytes)
        db["faces"].update_one(
            {"_id": ObjectId(face_id)},
            {"$set": {
                "image_data_encrypted": encrypted,
                "is_encrypted": True
            }, "$unset": {"image_data": ""}}
        )
        count += 1
    print(f"Encrypted {count} faces.")

if __name__ == "__main__":
    migrate_faces()
