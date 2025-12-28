# schemas/hod_mentor_schema.py
from pydantic import BaseModel
from datetime import datetime

class HodMentorMapping(BaseModel):
    hod_id: str
    mentor_id: str
    college: str
    year: int
    course: str
    created_at: datetime
