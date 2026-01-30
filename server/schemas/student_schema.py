from pydantic import BaseModel, Field
from typing import Optional, Literal

class Student(BaseModel):
    id: str = Field(alias="_id")
    name: str
    phone: str
    
    father_mobile: Optional[str] = None
    mother_mobile: Optional[str] = None

    year: int
    course: str
    section: str
    college: Literal["KMIT", "KMEC", "NGIT"]

    created_by: str
    password_hash: str

    face_id: Optional[str] = None

    class Config:
        populate_by_name = True
