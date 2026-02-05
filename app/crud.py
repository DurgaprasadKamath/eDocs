from sqlalchemy.orm import Session
from sqlalchemy import String, or_, and_
from app import models, schemas
from collections import defaultdict
from datetime import date, datetime
from app.routes import auth_routes


def create_account(
    db: Session,
    id: str,
    email: str,
    phone: str,
    role: str,
):
  db_account = models.UserInfo(
    id=id,
    email=email,
    phone=phone,
    role=role,
    date=datetime.today()
  )
  
  db.add(db_account)
  db.commit()
  db.refresh(db_account)
  return db_account

def get_user_by_email(db: Session, email: str):
    return db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.email == email
    ).first()
    
def get_user_by_id(db: Session, id: str):
    return db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.id == id
    ).first()
    
def checkEmptyPassword(db: Session, identifier: str):
    user = get_user_by_email(db, identifier)
    if not user:
        user = get_user_by_id(db, identifier)

    if not user:
        return False
    
    if user.password is None:
        return True
    return False

def setPasswordData(
    db: Session,
    id: str,
    email: str,
    name: str,
    dob: date,
    phone: str,
    gender: str,
    department: str,
    password: str,
    role: str
):
    user = get_user_by_email(db, email)
    if user:
        user.id = id
        user.email = email
        user.name = name
        user.dob = dob
        user.phone = phone
        user.gender = gender
        user.department = department
        user.password = auth_routes.hash_password(password)
        user.role = role
        user.date = user.date
        
        db.commit()
        db.refresh(user)
        
def get_all_users(db: Session):
    return db.query(
        models.UserInfo
    ).order_by(
        models.UserInfo.date.asc()
    ).all()
    

    
def get_count(db: Session, role: str):
    return db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.role == role
    ).count()

def delete_account(db: Session, id: str):
    userAccount = db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.id == id
    ).first()
    
    if userAccount:
        db.delete(userAccount)
        db.commit()
        
def edit_profile(
    db: Session,
    email: str,
    name: str,
    dob: str,
    gender: str,
    department: str
):
    user = get_user_by_email(db, email)
    if user:
        user.name = name
        user.dob = dob
        user.gender = gender
        user.department = department

        db.commit()
        db.refresh(user)
        return True
    return False
        
def reset_account(db: Session, id: str):
    resetAccount = db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.id == id
    ).first()
    
    if resetAccount:
        resetAccount.name = None
        resetAccount.dob = None
        resetAccount.gender = None
        resetAccount.department = None
        resetAccount.password = None

        db.commit()
        db.refresh(resetAccount)
    
def filter_search(
    db: Session,
    searchTxt: str
):
    return db.query(
        models.UserInfo
    ).filter(
        or_(
            models.UserInfo.name.ilike(f"%{searchTxt}%"),
            models.UserInfo.email.ilike(f"%{searchTxt}%"),
            models.UserInfo.id.ilike(f"%{searchTxt}%"),
            models.UserInfo.phone.ilike(f"%{searchTxt}%"),
            models.UserInfo.department.ilike(f"%{searchTxt}%"),
            models.UserInfo.role.ilike(f"%{searchTxt}%")
        )
    ).order_by(
        models.UserInfo.name.asc()
    ).all()
    
def add_profile_pic(db: Session, id: str, path: str):
    pic_data = db.query(
        models.ProfilePic
    ).filter(
        models.ProfilePic.id == id
    ).first()
    
    if pic_data:
        pic_data.path = path
    
    else:
        pic_data = models.ProfilePic(
            id=id,
            path=path
        )
        db.add(pic_data)
        
    db.commit()
    db.refresh(pic_data)
    return pic_data
    
def get_profile_path(db: Session, id: str):
    return db.query(
        models.ProfilePic
    ).filter(
        models.ProfilePic.id == id
    ).first()
    
def add_document(
    db: Session,
    appData: schemas.Documents
):
    db_appData = models.DocumentInfo(**appData.dict())
    db.add(db_appData)
    db.commit()
    db.refresh(db_appData)
    return db_appData

def pending_docs_office(db: Session):
    return db.query(
        models.DocumentInfo
    ).filter(
        and_(
            models.DocumentInfo.rec_role == 'office_staff',
            models.DocumentInfo.status == 'Pending'
        )
    ).order_by(
        models.DocumentInfo.date.asc()
    ).all()
    
def get_office_reports(db: Session):
    return db.query(
        models.DocumentInfo
    ).filter(
        models.DocumentInfo.rec_role == "office_staff",
    ).order_by(
        models.DocumentInfo.app_no.asc()
    ).all()
    
def office_filter_reports(db: Session, searchInput: str):
    return db.query(
        models.DocumentInfo
    ).filter(
        or_(
            models.DocumentInfo.app_no.ilike(f"%{searchInput}%"),
            models.DocumentInfo.sender_id_no.ilike(f"%{searchInput}%"),
            models.DocumentInfo.sender_name.ilike(f"%{searchInput}%"),
            models.DocumentInfo.status.ilike(f"%{searchInput}%"),
            models.DocumentInfo.app_type.ilike(f"%{searchInput}%")
        )
    ).order_by(
        models.DocumentInfo.app_no.asc()
    ).all()
    
def get_student_reports(
    db: Session,
    stdEmail: str,
    stdDept: str
):
    return db.query(models.DocumentInfo).filter(
        or_(
            models.DocumentInfo.rec_role == "all",
            models.DocumentInfo.rec_role == "student",
            models.DocumentInfo.sender_email == stdEmail,
            models.DocumentInfo.rec_role == stdDept
        )
    ).order_by(
        models.DocumentInfo.date.asc()    
    ).all()