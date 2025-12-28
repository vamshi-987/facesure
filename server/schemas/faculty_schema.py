from pydantic import BaseModel, Field
from typing import Literal, List


class Faculty(BaseModel):
    id: str = Field(alias="_id")

    name: str
    phone: str
    email: str

    college: Literal["KMIT", "KMEC", "NGIT"]

    years: List[int] = []
    courses: List[str] = []

    password_hash: str
    active: bool = True

    class Config:
        populate_by_name = True
        from_attributes = True
