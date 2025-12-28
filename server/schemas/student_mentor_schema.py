from pydantic import BaseModel, Field
from datetime import datetime


class StudentMentorMapping(BaseModel):

    student_id: str          # references students._id
    mentor_id: str           # references faculty._id

    college: str
    year: int
    course: str
    section: str

    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
