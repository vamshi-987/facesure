# ===============================================================
# ASYNC FACE PROCESSING (ThreadPoolExecutor)
# ===============================================================
from concurrent.futures import ThreadPoolExecutor
import asyncio
from config import Config
import threading

# Thread pool for CPU-intensive face processing
face_executor = ThreadPoolExecutor(max_workers=Config.FACE_EXECUTOR_MAX_WORKERS)
_inference_semaphore = threading.BoundedSemaphore(Config.FACE_INFERENCE_CONCURRENCY)


def _run_face_get(img, max_num=1):
    if not _inference_semaphore.acquire(timeout=Config.FACE_INFERENCE_TIMEOUT_SECONDS):
        raise HTTPException(
            status_code=503,
            detail="Face service busy. Please retry in a moment."
        )
    try:
        return face_model.get(img, max_num=max_num)
    finally:
        _inference_semaphore.release()

async def extract_embedding_async(img):
    """Run face extraction in thread pool"""
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(
                face_executor,
                extract_embedding_and_landmarks,
                img
            ),
            timeout=Config.FACE_INFERENCE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Face processing timed out. Please retry."
        )
import cv2
import base64
import numpy as np
import importlib
from datetime import datetime
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status
from utils.audit_log import logger
import traceback

torch = None
if importlib.util.find_spec("torch") is not None:
    import torch  # type: ignore[import-not-found]

from insightface.app import FaceAnalysis

# LIVENESS DETECTION (BLINK)
def detect_blink(face):
    # Use eye landmarks to check for blink
    # InsightFace landmark_3d_68: 36-41 (left eye), 42-47 (right eye)
    left_eye = face.landmark_3d_68[36:42]
    right_eye = face.landmark_3d_68[42:48]
    def eye_aspect_ratio(eye):
        # Compute distances between vertical eye landmarks
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        # Compute distance between horizontal eye landmarks
        C = np.linalg.norm(eye[0] - eye[3])
        # Eye aspect ratio formula
        return (A + B) / (2.0 * C)
    left_ear = eye_aspect_ratio(left_eye)
    right_ear = eye_aspect_ratio(right_eye)
    # Typical threshold for blink: EAR < 0.21
    blinked = left_ear < 0.21 or right_ear < 0.21
    return blinked

from extensions.mongo import client, db
from data.faces_repo import (
    get_face_by_user,
    delete_face,
    create_face_doc
)
from data.face_vectors_repo import (
    get_vector,
    create_vector,
    delete_vector,
    search_similar_faces
)


# ===============================================================
# MODEL INITIALIZATION (Singleton with GPU support)
# ===============================================================

class FaceModelSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        try:
            # If torch is unavailable, run InsightFace in CPU mode.
            use_gpu = bool(torch is not None and torch.cuda.is_available())
            ctx_id = 0 if use_gpu else -1
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if use_gpu else ['CPUExecutionProvider']

            self.model = FaceAnalysis(
                name="buffalo_l",
                providers=providers
            )
            self.model.prepare(ctx_id=ctx_id, det_size=(640, 640))
            print(f"✅ Face model loaded on {'GPU' if ctx_id == 0 else 'CPU'}")
        except Exception as e:
            print(f"❌ Face model load failed: {e}")
            traceback.print_exc() 
            self.model = None

    def get_model(self):
        return self.model

# Use singleton
face_model = FaceModelSingleton().get_model()


# ===============================================================
# THRESHOLDS (UNCHANGED)
# ===============================================================
VERIFY_THRESHOLD = 0.55
DUPLICATE_HIGH = 0.65
AMBIGUOUS_LOW = 0.50
LANDMARK_TWIN_THRESHOLD = 18.0


# ===============================================================
# IMAGE DECODER
# ===============================================================
def decode_image(b64):
    try:
        if "," in b64:
            b64 = b64.split(",")[1]
        img_bytes = base64.b64decode(b64)
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError()

        h, w = img.shape[:2]
        if w < Config.FACE_MIN_WIDTH or h < Config.FACE_MIN_HEIGHT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image too small. Minimum {Config.FACE_MIN_WIDTH}x{Config.FACE_MIN_HEIGHT} required"
            )

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        if brightness < Config.FACE_MIN_BRIGHTNESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image too dark. Improve lighting and retry"
            )
        if brightness > Config.FACE_MAX_BRIGHTNESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image too bright. Reduce glare/flash and retry"
            )

        return img, None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted image"
        )


# ===============================================================
# 🚨 FACE COUNT ENFORCEMENT (NEW)
# ===============================================================
def ensure_single_face(img):
    if face_model is None:
        raise HTTPException(
            status_code=503,
            detail="Face service unavailable: model failed to initialize"
        )

    faces = _run_face_get(img, max_num=1)

    if not faces:
        raise HTTPException(
            status_code=400,
            detail="No face detected. Ensure your face is visible."
        )

    if len(faces) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple faces detected. Only one person allowed."
        )

    return faces[0]


# ===============================================================
# EMBEDDING EXTRACTION (UNCHANGED LOGIC)
# ===============================================================
def extract_embedding_and_landmarks(img):
    face = ensure_single_face(img)

    emb = face.embedding.astype(np.float32)
    lm = face.landmark_3d_68.astype(np.float32)

    return emb, lm


def landmark_distance(a, b):
    return float(np.linalg.norm(a.flatten() - b.flatten()))


# ===============================================================
# VERIFICATION
# ===============================================================
def verify_face_for_user(user_id, b64):
    face = get_face_by_user(user_id)
    if not face:
        logger.log(user_id, 'face_verification_failed', details='Face not registered')
        raise HTTPException(404, "Face not registered")

    vector = get_vector(face["vector_ref"])
    if not vector:
        logger.log(user_id, 'face_verification_failed', details='Stored face vector missing')
        raise HTTPException(500, "Stored face vector missing")

    saved_emb = np.array(vector["embedding"], np.float32)

    img, _ = decode_image(b64)
    emb, lm1 = extract_embedding_and_landmarks(img)
    # LIVENESS CHECK: Blink detection
    # face = ensure_single_face(img)
    # if not detect_blink(face):
    #     logger.log(user_id, 'liveness_failed', details='Blink not detected')
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Liveness check failed: Please blink during authentication."
    #     )

    score = float(
        np.dot(saved_emb, emb)
        / (np.linalg.norm(saved_emb) * np.linalg.norm(emb))
    )
    logger.log(user_id, 'face_verification_attempt', details=f'Verification score: {score}')

    print(f"[VERIFY] {user_id} | score={score:.3f}")

    if score < VERIFY_THRESHOLD:
        return False, score

    if score < DUPLICATE_HIGH:
        img2 = cv2.imdecode(
            np.frombuffer(face["image_data"], np.uint8),
            cv2.IMREAD_COLOR
        )
        _, lm2 = extract_embedding_and_landmarks(img2)

        if landmark_distance(lm1, lm2) > LANDMARK_TWIN_THRESHOLD:
            raise HTTPException(
                status_code=403,
                detail="Identity ambiguous (Twin or spoof detected)"
            )

    return True, score


# ===============================================================
# SAVE / REPLACE FACE (UNCHANGED FLOW)
# ===============================================================
def save_face_replace(user_id, user_type, b64):
    img, _ = decode_image(b64)
    emb, _ = extract_embedding_and_landmarks(img)
    emb_list = emb.tolist()

    matches = search_similar_faces(emb_list, limit=5)
    for m in matches:
        if m.get("score", 0.0) >= DUPLICATE_HIGH and m["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Face already registered to user {m['user_id']}"
            )

    vector_id = f"vec_{user_id}"

    try:
        with client.start_session() as session:
            with session.start_transaction():
                old = get_face_by_user(user_id)
                if old:
                    delete_vector(old["vector_ref"], session=session)
                    delete_face(old["_id"], session=session)

                create_vector(vector_id, user_id, emb_list, session=session)

                ok, buf = cv2.imencode(".jpg", img)
                face_id = create_face_doc(
                    user_id,
                    user_type,
                    buf.tobytes(),
                    vector_id,
                    session=session
                )

                col_map = {
                    "STUDENT": "students",
                    "ADMIN": "admins",
                    "HOD": "hods",
                    "SUPER_ADMIN": "superadmins"
                }

                db[col_map[user_type.upper()]].update_one(
                    {"_id": user_id},
                    {"$set": {
                        "face_id": str(face_id),
                        "updated_at": datetime.utcnow()
                    }},
                    session=session
                )
        return True

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Failed to save biometric data"
        )


# ===============================================================
# VERIFY THEN REPLACE (UNCHANGED)
# ===============================================================
def verify_then_replace_face(user_id, user_type, b64):
    try:
        verify_face_for_user(user_id, b64)
        save_face_replace(user_id, user_type, b64)
    except HTTPException as e:
        if e.status_code == 404:
            save_face_replace(user_id, user_type, b64)
        else:
            raise
