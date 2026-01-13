from sqlalchemy import Column, Integer, String, Sequence, DateTime, Date
from app.database import Base
from datetime import datetime

class UserInfo(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, nullable=False)
    email = Column(String, nullable=False)
    name = Column(String)
    dob = Column(Date)
    phone = Column(String, nullable=False)
    gender = Column(String)
    department = Column(String)
    password = Column(String)
    role = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    
class DocumentInfo(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    app_no = Column(String, nullable=False)
    app_path = Column(String, nullable=False)
    sender_email = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    sender_id_no = Column(String, nullable=False)
    sender_department = Column(String, nullable=False)
    sender_role = Column(String, nullable=False)
    app_type = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    rec_role = Column(String, nullable=False)
    status = Column(String, nullable=False)