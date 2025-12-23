from pydantic import BaseModel, Field
from typing import List, Optional

class HOD(BaseModel):
    id: str = Field(alias="_id")
    name: str
    phone: str
    years: List[int]          
    college: str              # "KMIT" | "KMEC" | "NGIT" validated separately
    courses: List[str]        # Example: ["CSE", "ECE"]
    password_hash: str
    

    class Config:
        populate_by_name = True
