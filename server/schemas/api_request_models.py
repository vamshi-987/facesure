from pydantic import BaseModel
from typing import Optional, List, Dict, Literal


# ================= AUTH =================
class LoginRequest(BaseModel):
    userId: str
    password: str


class LogoutRequest(BaseModel):
    user_id: str


# ================= ADMIN =================
class AdminCreateRequest(BaseModel):
    id: str
    name: str
    phone: str
    password: str
    college: str


class AdminUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    college: str | None = None

# ================= HOD =================
class HODCreateRequest(BaseModel):
    id: str
    name: str
    phone: str
    years: List[int]
    college: str
    courses: List[str]
    password: str


class HODUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    years: Optional[List[int]] = None
    courses: Optional[List[str]] = None
    college: Optional[str] = None
    password: Optional[str] = None


class HODFilterRequest(BaseModel):
    college: Optional[str] = None
    years: Optional[List[int]] = None
    courses: Optional[List[str]] = None


# ================= STUDENT =================
# 🔐 ADMIN / SUPER_ADMIN → CREATE STUDENT (NO FACE)
class StudentCreateRequest(BaseModel):
    id: str
    name: str
    phone: str
    year: int
    course: str
    section: str
    college: str
    password: str
    created_by: str


# 👤 STUDENT → REGISTER FACE AFTER LOGIN
class StudentFaceRegisterRequest(BaseModel):
    student_id: str
    image_b64: str


class StudentUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    year: Optional[int] = None
    course: Optional[str] = None
    section: Optional[str] = None
    password: Optional[str] = None
    image_b64: Optional[str] = None


class StudentFilterRequest(BaseModel):
    college: Optional[str] = None
    year: Optional[int] = None
    course: Optional[str] = None
    section: Optional[str] = None


class PromoteStudentsRequest(BaseModel):
    year: int
    college: str
    new_year: int


# ================= GUARD =================
class GuardCreateRequest(BaseModel):
    id: str
    name: str
    phone: str
    password: str
    college: str


class GuardUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


# ================= FACE =================
class FaceReplaceRequest(BaseModel):
    user_id: str
    user_type: str
    image_b64: str


class FaceVerifyRequest(BaseModel):
    user_id: str
    image_b64: str


class FaceValidateRequest(BaseModel):
    image_b64: str


# ================= REQUESTS =================
class RequestCreate(BaseModel):
    student_id: str
    reason: str


class ApproveRequestBody(BaseModel):
    hod_id: str
    hod_name: str


class RejectRequestBody(BaseModel):
    hod_id: str
    hod_name: str

class MentorMappingRequest(BaseModel):
    college: str
    year: int
    course: str
    section: str
    mentor_ids: List[str]

class MentorActionBody(BaseModel):
    mentor_id: str
    mentor_name: str
    remark: str


class FacultyCreateRequest(BaseModel):
    id: str                     # faculty _id
    name: str
    phone: str
    email: str
    password: str
    college: Literal["KMIT", "KMEC", "NGIT"]
    years: List[int] = []
    courses: List[str] = []

class FacultyUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    college: Optional[Literal["KMIT", "KMEC", "NGIT"]] = None
    active: Optional[bool] = None
    years: Optional[List[int]] = None
    courses: Optional[List[str]] = None

class FacultyFilterRequest(BaseModel):
    college: Optional[Literal["KMIT", "KMEC", "NGIT"]] = None
    active: Optional[bool] = None
    name: Optional[str] = None

class AssignHODRequest(BaseModel):
    faculty_id: str
    college: str
    years: List[int]
    courses: List[str]