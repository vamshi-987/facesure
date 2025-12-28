from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Request(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")

    student_id: str
    student_name: str
    year: int
    course: str
    section: str

    
    request_time: datetime
    reason: str
    
     # Mentor stage
    mentor_id: Optional[str] = None
    mentor_name: Optional[str] = None
    mentor_remark: Optional[str] = None
    mentor_action_time: Optional[datetime] = None

    hod_id: Optional[str] = None
    hod_name: Optional[str] = None

    
    approval_time: Optional[datetime] = None
    rejection_time: Optional[datetime] = None

    
    left_time: Optional[datetime] = None

    status: Literal[
        "REQUESTED",
        "PENDING_MENTOR_APPROVAL",
        "APPROVED_BY_MENTOR",
        "REJECTED_BY_MENTOR",
        "PENDING_HOD_APPROVAL",
        "UNCHECKED",
        "APPROVED",
        "REJECTED",
        "LEFT_CAMPUS",
        "APPROVED_NOT_LEFT"
    ]

    class Config:
        populate_by_name = True
