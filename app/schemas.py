from pydantic import BaseModel
from datetime import datetime, date

class Users(BaseModel):
    id: str
    email: str
    name: str
    dob: date
    phone: str
    gender: str
    department: str
    password: str
    role: str
    
class Documents(BaseModel):
    app_no: str
    app_path: str
    app_type: str
    app_title: str
    description: str
    sender_email: str
    sender_name: str
    sender_id_no: str
    sender_department: str
    sender_role: str
    date: datetime
    rec_role: str
    status: str