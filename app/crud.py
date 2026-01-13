from sqlalchemy.orm import Session
from sqlalchemy import String, or_
from app import models, schemas
from collections import defaultdict
from datetime import date, datetime

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
        user.password = password
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
    
def delete_account(db: Session, id: str):
    userAccount = db.query(
        models.UserInfo
    ).filter(
        models.UserInfo.id == id
    ).first()
    
    if userAccount:
        db.delete(userAccount)
        db.commit()
        
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