
from extensions.mongo import db
from bson import ObjectId
from datetime import datetime
from utils.encryption import encrypt_image_bytes, decrypt_image_bytes

faces = db["faces"]

def create_face_doc(user_id, user_type, image_bytes, vector_ref, session=None):
    encrypted_image = encrypt_image_bytes(image_bytes)
    doc = {
        "user_id": user_id,
        "user_type": user_type,
        "image_data_encrypted": encrypted_image,
        "is_encrypted": True,
        "vector_ref": vector_ref,
        "created_at": datetime.utcnow()
    }
    res = faces.insert_one(doc, session=session)
    return str(res.inserted_id)

def get_face_by_id(face_id: str):
    doc = faces.find_one({"_id": ObjectId(face_id)})
    if doc and doc.get("is_encrypted"):
        doc["image_data"] = decrypt_image_bytes(doc["image_data_encrypted"])
    return doc

def get_face_by_user(user_id: str):
    doc = faces.find_one({"user_id": user_id})
    if doc and doc.get("is_encrypted"):
        doc["image_data"] = decrypt_image_bytes(doc["image_data_encrypted"])
    return doc

def delete_face(face_id: str, session=None):
    return faces.delete_one(
        {"_id": ObjectId(face_id)},
        session=session
    )
