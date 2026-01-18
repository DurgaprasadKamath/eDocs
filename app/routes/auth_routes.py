from fastapi import APIRouter, Request, Form, Depends, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app import database, models, crud, schemas
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")
router.mount("/static", StaticFiles(directory="app/static"), name="static")

departments = {
    "UG_BA_ENG": "B.A. English",
    "UG_BCOM": "B.Com",
    "UG_BSC_MATH": "B.Sc. Mathematics",
    "UG_BSC_CS": "B.Sc. Computer Science",
    "UG_BCA": "BCA",
    "UG_BBA": "BBA",
    "UG_BVOC_RSCM": "B.Voc Retail & Supply Chain Management",
    "UG_BVOC_SAD": "B.Voc Software & App Development",
    "UG_BVOC_DMFM": "B.Voc Digital Media & Film Making",
    "PG_MA_ENG": "M.A. English",
    "PG_MCOM": "M.Com",
    "PG_MSC_MATH": "M.Sc. Mathematics",
    "PG_MSC_CS": "M.Sc. Computer Science",
    "PG_MCA": "MCA",
    "PG_MBA": "MBA",
    "OTHER": "Other"
}

roles = {
    "office_staff": "OFFICE STAFF",
    "hod": "HOD",
    "faculty": "FACULTY",
    "student": "STUDENT"
}

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/login")
async def login_user(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    userData = crud.checkEmptyPassword(db, identifier)
    if userData:
        return RedirectResponse("/set-password/email", status_code=303)
    
    user = crud.get_user_by_email(db, identifier)
    if not user:
        user = crud.get_user_by_id(db, identifier)
        
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "emailError": True,
                "enteredIdentifier": identifier,
                "enteredPassword": password,
            }
        )
        
    if not verify_password(password, user.password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "passwordError": True,
                "enteredIdentifier": identifier,
                "enteredPassword": password
            }
        )
    
    request.session["id"] = user.id
    request.session["email"] = user.email
    request.session["name"] = user.name
    request.session["dob"] = user.dob.strftime('%Y-%m-%d')
    request.session["phone"] = user.phone
    request.session["gender"] = user.gender
    request.session["department"] = user.department
    request.session["password"] = user.password
    request.session["role"] = user.role
    
    if user.role == 'principal':
        return RedirectResponse(url="/principal/dashboard", status_code=303)
    
    if user.role == 'office_staff':
        return RedirectResponse(url="/office/dashboard", status_code=303)
    
    if user.role == 'hod':
        return RedirectResponse(url="/hod/dashboard", status_code=303)
    
    if user.role == 'faculty':
        return RedirectResponse(url="/faculty/dashboard", status_code=303)
    
    if user.role == 'student':
        return RedirectResponse(url="/student/dashboard", status_code=303)
    
@router.post("/delete-account")
async def delete_account(
    request: Request,
    id: str = Form(...),
    db: Session = Depends(database.get_db)
):
    crud.delete_account(db, id)

    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.post("/edit-profile")
async def edit_profile(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    department: str = Form(...),
    db: Session = Depends(database.get_db)
):
    editProfile = crud.edit_profile(db, email, name, dob, gender, department)
    
    if editProfile:
        user = crud.get_user_by_email(db, email)
        request.session['email'] = email
        request.session['name'] = user.name
        request.session['dob'] = user.dob.strftime('%Y-%m-%d')
        request.session['gender'] = user.gender
        request.session['department'] = user.department
        
        return RedirectResponse(url="/profile", status_code=303)
    
@router.post("/change-password")    
async def change_password(
    request: Request,
    email: str = Form(...),
    curPassword: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = crud.get_user_by_email(db, email)
    
    picPath = crud.get_profile_path(db, user.id)
    if picPath:
        picPath = picPath.path
        nonePic = (len(picPath) == 0)
    
        if not nonePic:
            picPath = str(picPath.replace("app",""))
    else:
        picPath = None
        nonePic = True
        
    if curPassword != user.password:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "page": "password",
                "curPassword": curPassword,
                "incorrectTxt": True,
                "email": email,
                "name": user.name,
                "picPath": picPath,
                "noPic": nonePic,
            }
        )
    
    if user:
        user.password = hash_password(password)
        
        db.commit()
        db.refresh(user)
    return RedirectResponse(url="/profile", status_code=303)

@router.get("/set-password/email")
async def get_password_email(
    request: Request
):
    return templates.TemplateResponse(
        "set_email.html",
        {
            "request": request
        }
    )
    
@router.post("/set-password/email")
async def set_password_email(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(database.get_db)
):
    if not crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "set_email.html",
            {
                "request": request,
                "email": email,
                "emailError": True
            }
        )
    if not crud.checkEmptyPassword(db, email):
        return templates.TemplateResponse(
            "set_email.html",
            {
                "request": request,
                "email": email,
                "passwordExists": True
            }
        )
    request.session['userEmail'] = email

    return RedirectResponse(url="/set-password/name", status_code=303)

@router.get("/set-password/name")
async def get_password_name(
    request: Request
):
    userEmail = request.session.get('userEmail')
    if not userEmail:
        return RedirectResponse(url="/set-password/email", status_code=303)

    return templates.TemplateResponse(
        "set_name.html",
        {
            "request": request
        }
    )

@router.post("/set-password/name")
async def set_password_name(
    request: Request,
    fname: str = Form(...),
    lname: str = Form(...)
):
    if lname is None:
        lname = ''
    
    name = f"{fname} {lname}"

    request.session['userName'] = name
    return RedirectResponse(url="/set-password/gender-birthday", status_code=303)

@router.get("/set-password/gender-birthday")
async def get_password_gender_bday(
    request: Request
):
    userEmail = request.session.get('userEmail')
    userName = request.session.get('userName')

    if not userEmail and not userName:
        return RedirectResponse(url="/set-password/email", status_code=303)
    
    return templates.TemplateResponse(
        "set_gender_birthday.html",
        {
            "request": request,
            "todayDate": datetime.today().strftime('%Y-%m-%d')
        }
    )

@router.post("/set-password/gender-birthday")
async def set_password_gender_bday(
    request: Request,
    dob: str = Form(...),
    gender: str = Form(...)
):
    request.session['userDob'] = dob
    request.session['userGender'] = gender
    
    return RedirectResponse(url="/set-password/id-department", status_code=303)

@router.get("/set-password/id-department")
async def get_password_id_department(
    request: Request,
    db: Session = Depends(database.get_db)
):
    userEmail = request.session.get('userEmail')
    userName = request.session.get('userName')
    userDob = request.session.get('userDob')
    userGender = request.session.get('userGender')
    
    if not userEmail and not userName and not userDob and not userGender:
        return RedirectResponse(url="/set-password/email", status_code=303)
    
    return templates.TemplateResponse(
        "set_id_department.html",
        {
            "request": request,
            "departments": departments
        }
    )
    
@router.post("/set-password/id-department")
async def set_password_id_department(
    request: Request,
    idno: str = Form(...),
    department: str = Form(...),
    db: Session = Depends(database.get_db)
):
    email = request.session.get('userEmail')
    userIdNo = db.query(
        models.UserInfo.id
    ).filter(
        models.UserInfo.email == email
    ).scalar()
    
    if idno != userIdNo:
        return templates.TemplateResponse(
            "set_id_department.html",
            {
                "request": request,
                "idError": True,
                "id_no": idno,
                "departments": departments
            }
        )
    
    request.session['userId'] = idno
    request.session['userDepartment'] = department
    
    return RedirectResponse(url="/set-password/validate-account", status_code=303)

@router.get("/set-password/validate-account")
async def get_password_validate(
    request: Request,
):
    userEmail = request.session.get('userEmail')
    userName = request.session.get('userName')
    userDob = request.session.get('userDob')
    userGender = request.session.get('userGender')
    userIdNo = request.session.get('userIdNo')
    userDepartment = request.session.get('userDepartment')
    
    if not userEmail and not userName and not userDob and not userGender and not userIdNo and not userDepartment:
        return RedirectResponse(url="/set-password/email", status_code=303)
    
    return templates.TemplateResponse(
        "set_validate.html",
        {
            "request": request
        }
    )
    
@router.post("/set-password/validate-account")
async def set_password_validate(
    request: Request,
    validNo: str = Form(...),
    db: Session = Depends(database.get_db)
):
    email = request.session.get('userEmail')
    userIdNo, phone = (
        db.query(models.UserInfo.id).filter(
            models.UserInfo.email == email
        ).scalar(),
        db.query(models.UserInfo.phone).filter(
            models.UserInfo.email == email
        ).scalar()
    )
    validationNo = userIdNo + phone[6:]
    
    if validNo != validationNo:
        return templates.TemplateResponse(
            "set_validate.html",
            {
                "request": request,
                "validNo": validNo,
                "validNoError": True
            }
        )
    
    return RedirectResponse(url="/set-password/password", status_code=303)

@router.get("/set-password/password")
async def get_password_pass(
    request: Request
):
    userEmail = request.session.get('userEmail')
    userName = request.session.get('userName')
    userDob = request.session.get('userDob')
    userGender = request.session.get('userGender')
    userIdNo = request.session.get('userIdNo')
    userDepartment = request.session.get('userDepartment')
    
    if not userEmail and not userName and not userDob and not userGender and not userIdNo and not userDepartment:
        return RedirectResponse(url="/set-password/email", status_code=303)
    
    return templates.TemplateResponse(
        "set_pass.html",
        {
            "request": request,
            "email": request.session.get('userEmail')
        }
    )
    
@router.post("/set-password/password")
async def set_password_pass(
    request: Request,
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    email = request.session.get('userEmail')
    
    role = db.query(models.UserInfo.role).filter(
        models.UserInfo.email == email
    ).scalar()
    phone = db.query(models.UserInfo.phone).filter(
        models.UserInfo.email == email
    ).scalar()
    
    name = request.session.get('userName')
    dob = request.session.get('userDob')
    gender = request.session.get('userGender')
    id = request.session.get('userId')
    department = request.session.get('userDepartment')
    
    crud.setPasswordData(
        db,
        email=email,
        name=name,
        dob=dob,
        phone=phone,
        gender=gender,
        id=id,
        department=department,
        password=password,
        role=role
    )
    
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

#create office staff
@router.post("/office/create/office")
async def create_office_account(
    request: Request,
    email: str = Form(...),
    id: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(database.get_db)
):
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "office_staff/create_office.html",
            {
                "request": request,
                "page": "create",
                "emailError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
    if crud.get_user_by_id(db, id):
        return templates.TemplateResponse(
            "office_staff/create_office.html",
            {
                "request": request,
                "page": "create",
                "idError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
        
    crud.create_account(db, id, email, phone, "office_staff")
    
    return RedirectResponse(url="/office/create/office", status_code=303)

#create hod
@router.post("/office/create/hod")
async def create_office_account(
    request: Request,
    email: str = Form(...),
    id: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(database.get_db)
):
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "office_staff/create_hod.html",
            {
                "request": request,
                "page": "create",
                "emailError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
    if crud.get_user_by_id(db, id):
        return templates.TemplateResponse(
            "office_staff/create_hod.html",
            {
                "request": request,
                "page": "create",
                "idError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
        
    crud.create_account(db, id, email, phone, "hod")
    
    return RedirectResponse(url="/office/create/hod", status_code=303)

#create faculty
@router.post("/office/create/faculty")
async def create_office_account(
    request: Request,
    email: str = Form(...),
    id: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(database.get_db)
):
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "office_staff/create_faculty.html",
            {
                "request": request,
                "page": "create",
                "emailError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
    if crud.get_user_by_id(db, id):
        return templates.TemplateResponse(
            "office_staff/create_faculty.html",
            {
                "request": request,
                "page": "create",
                "idError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
        
    crud.create_account(db, id, email, phone, "faculty")
    
    return RedirectResponse(url="/office/create/faculty", status_code=303)

#create student
@router.post("/office/create/student")
async def create_office_account(
    request: Request,
    email: str = Form(...),
    id: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(database.get_db)
):
    if crud.get_user_by_email(db, email):
        return templates.TemplateResponse(
            "office_staff/create_student.html",
            {
                "request": request,
                "page": "create",
                "emailError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
    if crud.get_user_by_id(db, id):
        return templates.TemplateResponse(
            "office_staff/create_student.html",
            {
                "request": request,
                "page": "create",
                "idError": True,
                "email": email,
                "id": id,
                "phone": phone,
                "role": request.session.get("role")
            }
        )
        
    crud.create_account(db, id, email, phone, "student")
    
    return RedirectResponse(url="/office/create/student", status_code=303)

#delete account
@router.post("/delete/{id}")
async def delete_account(
    request: Request,
    id: str,
    db: Session = Depends(database.get_db)
):
    crud.delete_account(db, id)
    return RedirectResponse(url="/office/manage", status_code=303)

#reset account
@router.post("/reset/{id}")
async def reset_account(
    request: Request,
    id: str,
    db: Session = Depends(database.get_db)
):
    crud.reset_account(db, id)
    return RedirectResponse(url="/office/manage", status_code=303)

#filter search
@router.post("/office/manage")
async def serach_filter(
    request: Request,
    searchInput: str = Form(...)
):
    url = f"/office/manage/{searchInput}"
    return RedirectResponse(url=url, status_code=303)

@router.get("/office/manage/{searchInput}")
async def get_search_filter(
    request: Request,
    searchInput: str,
    db: Session = Depends(database.get_db)
):
    allUser = crud.filter_search(db, searchInput)

    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/manage.html",
        {
            "request": request,
            "page": "manage",
            "role": role,
            "allUser": allUser,
            "roles": roles,
            "departments": departments,
            "searchInput": searchInput,
            "isEmpty": (len(allUser) == 0),
            "studentCount": crud.get_count(db, "student"),
            "officeCount": crud.get_count(db, "office_staff"),
            "hodCount": crud.get_count(db, "hod"),
            "facultyCount": crud.get_count(db, "faculty")
        }
    )
    
@router.post("/upload-profile")
async def upload_profile(
    request: Request,
    id: str = Form(...),
    profilePicture: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    _, ext = os.path.splitext(profilePicture.filename)

    filename = f"{id}{ext}"
    file_path = f"app/static/images/profile_pictures/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(profilePicture.file, buffer)
        
    crud.add_profile_pic(db, id, file_path)

    return RedirectResponse(url="/profile", status_code=303)

@router.post("/delete-profile")
async def delete_profile(
    request: Request,
    id: str = Form(...),
    db: Session = Depends(database.get_db)
):
    picPath = crud.get_profile_path(db, id)
    if picPath:
        imgPath = picPath.path
        os.remove(imgPath)
        db.delete(picPath)
        db.commit()
    
    return RedirectResponse("/profile", status_code=303)

@router.post("/upload-document")
async def upload_document(
    request: Request,
    email: str = Form(...),
    appType: str = Form(...),
    docTitle: str = Form(...),
    description: str = Form(...),
    docFile: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):    
    app_list = db.query(
        models.DocumentInfo
    ).order_by(
        models.DocumentInfo.date.desc()
    ).first()
    
    year = datetime.today().strftime("%Y")
    user = crud.get_user_by_email(db, email)
    
    if not app_list:
        num = 10001
        app_no = f"EDOC-{year}-0{num}"
    else:
        app_no = app_list.app_no
        app_no = str(app_no)
        num = app_no[11:]
        num = int(num)
        num += 1
        app_no = f"EDOC-{year}-0{num}"
    
    _, ext = os.path.splitext(docFile.filename)
    
    app_name = f"{app_no}{ext}"
    app_path = f"app/static/document_uploads/{app_name}"
    
    with open(app_path, "wb") as buffer:
        shutil.copyfileobj(docFile.file, buffer)
        
    if appType == 'DOC_VER' or appType == 'EVE_REQ':
        rec_role = 'office_staff'
    elif appType == 'LEA_REQ' or appType == 'INT_REQ' or appType == 'WORK_REQ':
        rec_role = 'hod'
        
    appData = schemas.Documents(
        app_no = app_no,
        app_path = app_path,
        app_type = appType,
        app_title = docTitle,
        description = description,
        sender_email = email,
        sender_name = user.name,
        sender_id_no = user.id,
        sender_department = user.department,
        sender_role = user.role,
        rec_role = rec_role,
        status = "Pending",
        date = datetime.now()
    )
    
    crud.add_document(db, appData)

    return RedirectResponse(url="/", status_code=303)