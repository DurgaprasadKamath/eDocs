from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import Base, engine, SessionLocal
from app.models import UserInfo
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.routes import auth_routes
from app import crud, database, models
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime
from sqlalchemy import and_, or_
import asyncio
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_routes.router)

SECRET_KEY = 'eDocsProject'
app.add_middleware(SessionMiddleware, secret_key = SECRET_KEY)

Base.metadata.create_all(bind=engine)

@app.exception_handler(Exception)
async def error_page(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "error_page.html",
        {
            "request": request,
        }
    )
    
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "not_page.html",
            {
                "request": request,
                "role": "office_staff"
            },
            status_code=404
        )
    raise exc

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

docTypes = {
    "DOC_VER": "Document Verification",
    "LEA_REQ": "Leave Request",
    "EVE_REQ": "Event Request",
    "INT_REQ": "Internship Request",
    "WORK_REQ": "Workshop Request"
}

async def refresh_office_home(db: Session):
    prev_count = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Pending"
    ).count()
    
    while True:
        await asyncio.sleep(2)

        cur_count = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.status == "Pending"
        ).count()
        
        if cur_count != prev_count:
            prev_count = cur_count
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }

@app.get("/office_home_refresh")
async def sse_endpoint(db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_office_home(db))

async def refresh_office_reports(db: Session):
    prev_rep_count = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.rec_role == "office_staff"
    ).count()
    prev_pending = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Pending"
    ).count()
    prev_process = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Under Process"
    ).count()
    prev_reject = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Rejected"
    ).count()
    prev_approved = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Approved"
    ).count()
    
    while True:
        await asyncio.sleep(2)
        
        curr_rep_count = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.rec_role == "office_staff"
        ).count()
        curr_pending = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.status == "Pending"
        ).count()
        curr_process = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.status == "Under Process"
        ).count()
        curr_reject = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.status == "Rejected"
        ).count()
        curr_approved = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.status == "Approved"
        ).count()
        
        if (
            curr_rep_count != prev_rep_count
            or
            curr_pending != prev_pending
            or
            curr_process != prev_process
            or
            curr_reject != prev_reject
            or
            curr_approved != prev_approved
            ):
            prev_rep_count = curr_rep_count
            prev_pending = curr_pending
            prev_process = curr_process
            prev_reject = curr_reject
            prev_approved = curr_approved
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
        
@app.get("/office_reports_refresh")
async def sse_endpoint(db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_office_reports(db))

@app.get("/", response_class=HTMLResponse)
async def read_home(
    request: Request
):
    email = request.session.get('email')
    
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    else:
        role = request.session.get('role')
        if role == 'office_staff':
            return RedirectResponse(url="/office/dashboard", status_code=303)
        elif role == 'hod':
            return RedirectResponse(url="/hod/dashboard", status_code=303)
        elif role == 'faculty':
            return RedirectResponse(url="/faculty/dashboard", status_code=303)
        elif role == 'student':
            return RedirectResponse(url="/student/dashboard", status_code=303)
        
@app.get("/login", response_class=HTMLResponse)
async def read_login(
    request: Request
):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        }
    )
    
    
@app.get("/logout", response_class=HTMLResponse)
async def read_logout(
    request: Request
):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def read_profile(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    if not email:
        return RedirectResponse(url="/login", status_code=303) 
    user = crud.get_user_by_email(db, email)
    
    if user:
        picPath = crud.get_profile_path(db, user.id)
        if picPath:
            picPath = picPath.path
            nonePic = (len(picPath) == 0)
        
            if not nonePic:
                picPath = str(picPath.replace("app",""))
        else:
            picPath = None
            nonePic = True

    else:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "profile_data.html",
        {
            "request": request,
            "page": "profile",
            "email": email,
            "name": user.name,
            "id": user.id,
            "phone": user.phone,
            "dob": user.dob,
            "gender": user.gender,
            "department": departments[user.department],
            "picPath": picPath,
            "noPic": nonePic,
            "verifyTxt": (user.name[0:4] + user.id[4:])
        }
    )

@app.get("/change-password", response_class=HTMLResponse)
async def read_profile(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    if not email:
        return RedirectResponse(url="/login", status_code=303) 
    user = crud.get_user_by_email(db, email)
    
    if user:
        picPath = crud.get_profile_path(db, user.id)
        if picPath:
            picPath = picPath.path
            nonePic = (len(picPath) == 0)
        
            if not nonePic:
                picPath = str(picPath.replace("app",""))
        else:
            picPath = None
            nonePic = True

    else:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "page": "password",
            "email": email,
            "name": user.name,
            "id": user.id,
            "phone": user.phone,
            "dob": user.dob,
            "gender": user.gender,
            "department": user.department,
            "password": user.password,
            "picPath": picPath,
            "noPic": nonePic
        }
    )

@app.get("/edit-profile", response_class=HTMLResponse)
async def read_profile(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    if not email:
        return RedirectResponse(url="/login", status_code=303) 
    user = crud.get_user_by_email(db, email)
    
    if user:
        picPath = crud.get_profile_path(db, user.id)
        if picPath:
            picPath = picPath.path
            nonePic = (len(picPath) == 0)
        
            if not nonePic:
                picPath = str(picPath.replace("app",""))
        else:
            picPath = None
            nonePic = True

    else:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "edit_profile.html",
        {
            "request": request,
            "page": "edit",
            "email": email,
            "name": user.name,
            "id": user.id,
            "phone": user.phone,
            "dob": user.dob,
            "gender": user.gender,
            "department": user.department,
            "password": user.password,
            "picPath": picPath,
            "noPic": nonePic,
            "departments": departments
        }
    )
    
@app.get("/view/{appNo}", response_class=HTMLResponse)
async def read_view_docs(
    request: Request,
    appNo: str,
    db: Session = Depends(database.get_db)
):
    appDoc = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.app_no == appNo
    ).first()
    if not appDoc:
        return RedirectResponse(url="/", status_code=303)
        
    appPath = str(appDoc.app_path)
    
    return templates.TemplateResponse(
        "view_all.html",
        {
            "request": request,
            "appPath": appPath.replace("app", ""),
            "appNo": appNo
        }
    )
    
#office staff backend
@app.get("/office/dashboard", response_class=HTMLResponse)
async def read_office_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):
    # from email.message import EmailMessage
    # import smtplib

    # msg = EmailMessage()
    # msg["From"] = "231353@sdmcujire.in"
    # msg["To"] = "durgaprasadkamath2004@gmail.com"
    # msg["Subject"] = "eDocs"
    # msg.set_content("Good morning")
    
    # with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    #     server.login("231353@sdmcujire.in", "yyvqvmlwenfwmwfd")
    #     server.send_message(msg)
    
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    pendingDocs = crud.pending_docs_office(db)
    
    return templates.TemplateResponse(
        "/office_staff/index.html",
        {
            "request": request,
            "page": "dashboard",
            "email": email,
            "role": role,
            "pendingDocs": pendingDocs,
            "departments": departments,
            "docTypes": docTypes,
        }
    )

@app.get("/office/create", response_class=HTMLResponse)
async def read_office_create(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/create.html",
        {
            "request": request,
            "page": "create",
            "role": role
        }
    )

@app.get("/office/create/office", response_class=HTMLResponse)
async def read_office_create(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/create_office.html",
        {
            "request": request,
            "page": "create",
            "role": role
        }
    )

@app.get("/office/create/hod", response_class=HTMLResponse)
async def read_office_create(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/create_hod.html",
        {
            "request": request,
            "page": "create",
            "role": role
        }
    )

@app.get("/office/create/faculty", response_class=HTMLResponse)
async def read_office_create(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/create_faculty.html",
        {
            "request": request,
            "page": "create",
            "role": role
        }
    )

@app.get("/office/create/student", response_class=HTMLResponse)
async def read_office_create(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/create_student.html",
        {
            "request": request,
            "page": "create",
            "role": role
        }
    )

@app.get("/office/manage", response_class=HTMLResponse)
async def read_office_manage(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    allUser = crud.get_all_users(db)
    
    return templates.TemplateResponse(
        "/office_staff/manage.html",
        {
            "request": request,
            "page": "manage",
            "email": email,
            "role": role,
            "allUser": allUser,
            "roles": roles,
            "departments": departments,
            "studentCount": crud.get_count(db, "student"),
            "officeCount": crud.get_count(db, "office_staff"),
            "hodCount": crud.get_count(db, "hod"),
            "facultyCount": crud.get_count(db, "faculty")
        }
    )
    
@app.get("/office/upload", response_class=HTMLResponse)
async def read_office_upload(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "/office_staff/upload.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role
        }
    )

@app.get("/office/upload/student", response_class=HTMLResponse)
async def read_upload_student(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "/office_staff/upload_student.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role
        }
    )

@app.get("/office/upload/teaching-staff", response_class=HTMLResponse)
async def read_upload_teaching(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "/office_staff/upload_teaching.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role
        }
    )

@app.get("/office/upload/department", response_class=HTMLResponse)
async def read_upload_department(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "/office_staff/upload_department.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role
        }
    )

@app.get("/office/upload/all", response_class=HTMLResponse)
async def read_upload_all(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "/office_staff/upload_all.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role
        }
    )

@app.get("/office/reports", response_class=HTMLResponse)
async def read_office_reports(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/reports.html",
        {
            "request": request,
            "page": "reports",
            "role": role,
            "allReports": crud.get_office_reports(db),
            "docType": docTypes
        }
    )
    
@app.get("/office/preview/{appNo}")
async def view_document(
    request: Request,
    appNo: str,
    db: Session = Depends(database.get_db)
):
    appDoc = db.query(
        models.DocumentInfo
    ).filter(
        models.DocumentInfo.app_no == appNo
    ).first()
    appPath = str(appDoc.app_path)
    
    if appDoc.status != "Under Process":
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse(
        "/office_staff/view_doc.html",
        {
            "request": request,
            "appNo": appNo,
            "appType": docTypes[appDoc.app_type],
            "appDesc": appDoc.description,
            "senderEmail": appDoc.sender_email,
            "senderName": appDoc.sender_name,
            "senderIdNo": appDoc.sender_id_no,
            "sentDate": appDoc.date,
            "appTitle": appDoc.app_title,
            "appPath": appPath.replace("app", ""),
        }
    )
    
#student backend
@app.get("/student/dashboard", response_class=HTMLResponse)
async def read_std_home(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    user = crud.get_user_by_email(db, email)
    stdDocs = crud.get_student_reports(db, email, user.department)

    return templates.TemplateResponse(
        "student/index.html",
        {
            "request": request,
            "page": "dashboard",
            "role": role,
            "stdDocs": stdDocs
        }
    )

@app.get("/student/upload", response_class=HTMLResponse)
async def read_std_home(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "student/upload.html",
        {
            "request": request,
            "page": "upload",
            "role": role,
            "email": email,
        }
    )

@app.get("/student/approved", response_class=HTMLResponse)
async def read_std_home(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "student/approved.html",
        {
            "request": request,
            "page": "approved",
            "role": role
        }
    )

@app.get("/student/reports", response_class=HTMLResponse)
async def read_std_home(
    request: Request
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "student/reports.html",
        {
            "request": request,
            "page": "reports",
            "role": role
        }
    )