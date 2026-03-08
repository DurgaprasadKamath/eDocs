from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import Base, engine
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.routes import auth_routes
from app import crud, database, models
from sqlalchemy.orm import Session
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
    "WORK_REQ": "Workshop Request",
    "EXA_TBL": "Exam Timetable",
    "NOTI": "Notice",
    "ACA_EVE": "Academic Event",
    "ACA_DOC": "Academic Documents",
    "MEET": "Meetings",
    "MARK_SUB": "Marks Submission",
    "SYL_COM": "Syllabus Progress Report",
    "OTHER": "Other"
}

# approved page refresh (for all users)
async def refresh_page_approved(request: Request, db: Session):
    email = request.session.get('email')
    
    prevApprovedCount = crud.status_with_email_count(db, 'Approved', email)
    
    while True:
        await asyncio.sleep(2)
        
        curApprovedCount = crud.status_with_email_count(db, 'Approved', email)
        
        if curApprovedCount != prevApprovedCount:
            prevApprovedCount = curApprovedCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
            
@app.get("/refresh-approved")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_page_approved(request, db))

# pending page refresh (for all users)
async def refresh_page_pending(request: Request, db: Session):
    email = request.session.get('email')
    
    prevPendingCount = crud.status_with_email_count(db, 'Pending', email)
    
    while True:
        await asyncio.sleep(2)
        
        curPendingCount = crud.status_with_email_count(db, 'Pending', email)
        
        if curPendingCount != prevPendingCount:
            prevPendingCount = curPendingCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
            
@app.get("/refresh-pending")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_page_pending(request, db))

# inbox page refresh(for all users)
async def refresh_page_inbox(request: Request, db: Session):
    email = request.session.get('email')
    dept = (crud.get_user_by_email(db, email)).department
    role = (crud.get_user_by_email(db, email)).role
    
    prevInboxCount = db.query(models.InboxDocs).filter(
        and_(
            or_(
                models.InboxDocs.rec_role == 'all',
                models.InboxDocs.rec_role == role
            ),
            or_(
                models.InboxDocs.rec_department == 'all',
                models.InboxDocs.rec_department == dept
            )            
        )
    ).count()
    
    while True:
        await asyncio.sleep(2)

        currInboxCount = db.query(models.InboxDocs).filter(
            and_(
                or_(
                    models.InboxDocs.rec_role == 'all',
                    models.InboxDocs.rec_role == role
                ),
                or_(
                    models.InboxDocs.rec_department == 'all',
                    models.InboxDocs.rec_department == dept
                )            
            )
        ).count()
        
        if currInboxCount != prevInboxCount:
            prevInboxCount = currInboxCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
            
@app.get("/refresh-inbox")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_page_inbox(request, db))

# reports page refresh (for all users)
async def refresh_page_reports(request: Request, db: Session):
    email = request.session.get('email')

    prevReportsCount = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.sender_email == email
    ).count()
    
    prevPendingCount, prevUnderProcessCount, prevRejectCount, prevApprovedCount = (
        crud.status_with_email_count(db, 'Pending', email),
        crud.status_with_email_count(db, 'Under Process', email),
        crud.status_with_email_count(db, 'Reject', email),
        crud.status_with_email_count(db, 'Approved', email)
    )
    
    while True:
        await asyncio.sleep(2)
        
        currReportsCount = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.sender_email == email
        ).count()
        
        curPendingCount, curUnderProcessCount, curRejectCount, curApprovedCount = (
            crud.status_with_email_count(db, 'Pending', email),
            crud.status_with_email_count(db, 'Under Process', email),
            crud.status_with_email_count(db, 'Reject', email),
            crud.status_with_email_count(db, 'Approved', email)
        )
        
        if (
            currReportsCount != prevReportsCount
            or
            curApprovedCount != prevApprovedCount
            or
            curPendingCount != prevPendingCount
            or
            curRejectCount != prevRejectCount
            or
            curUnderProcessCount != prevUnderProcessCount
        ):
            prevReportsCount = currReportsCount
            prevApprovedCount = curApprovedCount
            prevPendingCount = curPendingCount
            prevRejectCount = curRejectCount
            prevUnderProcessCount = curUnderProcessCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
        
@app.get("/refresh-reports")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_page_reports(request, db))

# office home refresh
async def refresh_office_home(db: Session):
    prev_count = db.query(models.DocumentInfo).filter(
        and_(
            models.DocumentInfo.status == "Pending",
            models.DocumentInfo.rec_role == "office_staff"
        )
    ).count()
    
    while True:
        await asyncio.sleep(2)

        cur_count = db.query(models.DocumentInfo).filter(
            and_(
                models.DocumentInfo.status == "Pending",
                models.DocumentInfo.rec_role == "office_staff"
             )
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

# office manage accounts refresh
async def refresh_manage_acc(db: Session):
    prevActiveCount = db.query(models.UserInfo).filter(
        models.UserInfo.password != None
    ).count()
    
    prevAccountCount = db.query(models.UserInfo).count()
    
    while True:
        await asyncio.sleep(2)
        
        curActiveCount = db.query(models.UserInfo).filter(
            models.UserInfo.password != None
        ).count()
        
        curAccountCount = db.query(models.UserInfo).count()
        
        if (
            curActiveCount != prevActiveCount
            or
            curAccountCount != prevAccountCount
        ):
            prevActiveCount = curActiveCount
            prevAccountCount = curAccountCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
            
@app.get("/office_manage_refresh")
async def sse_endpoint(db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_manage_acc(db))

# office upload history refresh
async def refresh_upload_history(db: Session):
    prevHistoryCount = db.query(models.InboxDocs).count()
    
    while True:
        await asyncio.sleep(2)

        currHistoryCount = db.query(models.InboxDocs).count()
        
        if currHistoryCount != prevHistoryCount:
            prevHistoryCount = currHistoryCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }
            
@app.get("/refresh_upload_history")
async def sse_endpoint(db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_upload_history(db))

async def refresh_office_reports(db: Session):
    prevReportsCount = db.query(models.DocumentInfo).filter(
        models.DocumentInfo.rec_role == 'office_staff'
    ).count()
    
    prevApprovedCount, prevRejectedCount, prevPendingCount, prevUnderProcessCount = (
        crud.get_status_count(db, 'Approved', 'office_staff'),
        crud.get_status_count(db, 'Rejected', 'office_staff'),
        crud.get_status_count(db, 'Pending', 'office_staff'),
        crud.get_status_count(db, 'Under Process', 'office_staff')
    )
    
    while True:
        await asyncio.sleep(2)

        curReportsCount = db.query(models.DocumentInfo).filter(
            models.DocumentInfo.rec_role == 'office_staff'
        ).count()
        
        curApprovedCount, curRejectedCount, curPendingCount, curUnderProcessCount = (
            crud.get_status_count(db, 'Approved', 'office_staff'),
            crud.get_status_count(db, 'Rejected', 'office_staff'),
            crud.get_status_count(db, 'Pending', 'office_staff'),
            crud.get_status_count(db, 'Under Process', 'office_staff')
        )
        
        if (
            prevReportsCount != curReportsCount
            or
            curApprovedCount != prevApprovedCount
            or
            curPendingCount != prevPendingCount
            or
            curRejectedCount != prevRejectedCount
            or
            curUnderProcessCount != prevUnderProcessCount
        ):
            prevReportsCount = curReportsCount
            prevApprovedCount = curApprovedCount
            prevPendingCount = curPendingCount
            prevRejectedCount = curRejectedCount
            prevUnderProcessCount = curUnderProcessCount
            
            yield {
                'event': 'db_change',
                'data': 'database updated'
            }

# hod home refresh
async def refresh_hod_home(request: Request, db: Session):
    email = request.session.get('email')
    dept = (crud.get_user_by_email(db, email)).department
    
    prev_count = db.query(models.DocumentInfo).filter(
        and_(
            models.DocumentInfo.status == "Pending",
            models.DocumentInfo.rec_role == "hod",
            models.DocumentInfo.sender_department == dept
        )
    ).count()
    
    while True:
        await asyncio.sleep(2)

        cur_count = db.query(models.DocumentInfo).filter(
            and_(
                models.DocumentInfo.status == "Pending",
                models.DocumentInfo.rec_role == "hod",
                models.DocumentInfo.sender_department == dept
            )
        ).count()
        
        if cur_count != prev_count:
            prev_count = cur_count
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }

@app.get("/hod_home_refresh")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_hod_home(request, db))

# hod history refresh
async def refresh_hod_history(request: Request, db: Session):
    email = request.session.get('email')
    dept = (crud.get_user_by_email(db, email)).department
    
    prevHistoryCount = db.query(models.DocumentInfo).filter(
        and_(
            models.DocumentInfo.sender_department == dept,
            models.DocumentInfo.rec_role == "hod"
        )
    ).count()
    
    prevPendingCount, prevUnderProcessCount, prevRejectCount, prevApprovedCount = (
        crud.status_with_dept(db, 'Pending', 'hod', dept),
        crud.status_with_dept(db, 'Under Process', 'hod', dept),
        crud.status_with_dept(db, 'Rejected', 'hod', dept),
        crud.status_with_dept(db, 'Approved', 'hod', dept)
    )
    
    while True:
        await asyncio.sleep(2)

        currHistoryCount = db.query(models.DocumentInfo).filter(
            and_(
                models.DocumentInfo.sender_department == dept,
                models.DocumentInfo.rec_role == "hod"
            )
        ).count()
        
        curPendingCount, curUnderProcessCount, curRejectCount, curApprovedCount = (
            crud.status_with_dept(db, 'Pending', 'hod', dept),
            crud.status_with_dept(db, 'Under Process', 'hod', dept),
            crud.status_with_dept(db, 'Rejected', 'hod', dept),
            crud.status_with_dept(db, 'Approved', 'hod', dept)
        )

        if (
            currHistoryCount != prevHistoryCount
            or
            curApprovedCount != prevApprovedCount
            or
            curPendingCount != prevPendingCount
            or
            curRejectCount != prevRejectCount
            or
            curUnderProcessCount != prevUnderProcessCount
        ):
            prevHistoryCount = currHistoryCount
            prevApprovedCount = curApprovedCount
            prevPendingCount = curPendingCount
            prevRejectCount = curRejectCount
            prevUnderProcessCount = curUnderProcessCount
            
            yield {
                "event": "db_change",
                "data": "database updated"
            }

@app.get("/refresh_hod_history")
async def sse_endpoint(request: Request, db: Session = Depends(database.get_db)):
    return EventSourceResponse(refresh_hod_history(request, db))

# main backend
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
        appDoc = db.query(models.InboxDocs).filter(
            models.InboxDocs.doc_no == appNo
        ).first()
    if not appDoc:
        return RedirectResponse(url="/", status_code=303)
        
    appPath = str(appDoc.app_path)
    
    return templates.TemplateResponse(
        "view_all.html",
        {
            "request": request,
            "appPath": appPath.replace("app/", "/"),
            "appNo": appNo
        }
    )
    
#office staff backend
@app.get("/office/dashboard", response_class=HTMLResponse)
async def read_office_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):
    
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
            "role": role,
            "departments": departments
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

@app.get("/office/upload-history", response_class=HTMLResponse)
async def read_upload_all(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')
    
    if role != "office_staff":
        return RedirectResponse("/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    inboxDocs = crud.get_office_upload_history(db)

    return templates.TemplateResponse(
        "/office_staff/upload_history.html",
        {
            "request": request,
            "page": "history",
            "email": email,
            "role": role,
            "inboxDocs": inboxDocs,
            "isEmpty": (len(inboxDocs) == 0),
            "docType": docTypes
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
            "docType": docTypes,
            "roles": roles
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
    
    if appDoc.status == "Approved" or appDoc.status == "Rejected":
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
    
    approvedDocs = crud.get_user_approved_docs(db, email)

    return templates.TemplateResponse(
        "student/index.html",
        {
            "request": request,
            "page": "dashboard",
            "role": role,
            "approvedDocs": approvedDocs,
            "docType": docTypes
        }
    )

@app.get("/student/upload", response_class=HTMLResponse)
async def read_std_upload(
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

@app.get("/student/pending", response_class=HTMLResponse)
async def read_std_pending(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    pendingDocs = crud.get_user_pending_docs(db, email)

    return templates.TemplateResponse(
        "student/pending.html",
        {
            "request": request,
            "page": "pending",
            "role": role,
            "pendingDocs": pendingDocs,
            "docType": docTypes
        }
    )

@app.get("/student/inbox", response_class=HTMLResponse)
async def read_std_inbox(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    inboxDocs = crud.get_student_inbox(db, email)

    return templates.TemplateResponse(
        "student/inbox.html",
        {
            "request": request,
            "page": "inbox",
            "role": role,
            "inboxDocs": inboxDocs,
            "docTypes": docTypes
        }
    )

@app.get("/student/reports", response_class=HTMLResponse)
async def read_std_reports(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "student":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    allReports = crud.get_user_all_reports(db, email)

    return templates.TemplateResponse(
        "student/reports.html",
        {
            "request": request,
            "page": "reports",
            "role": role,
            "allReports": allReports,
            "docType": docTypes
        }
    )
    
#hod backend    
@app.get("/hod/dashboard", response_class=HTMLResponse)
async def read_hod_home(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    pendingDocs = crud.pending_docs_hod(db, email)

    return templates.TemplateResponse(
        "hod/index.html",
        {
            "request": request,
            "page": "home",
            "role": role,
            "pendingDocs": pendingDocs,
            "departments": departments,
            "docTypes": docTypes
        }
    )
    
@app.get("/hod/approved", response_class=HTMLResponse)
async def read_hod_approved(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    approvedDocs = crud.get_user_approved_docs(db, email)

    return templates.TemplateResponse(
        "hod/approved.html",
        {
            "request": request,
            "page": "approved",
            "role": role,
            "approvedDocs": approvedDocs,
            "departments": departments,
            "docTypes": docTypes
        }
    )
    
@app.get("/hod/upload", response_class=HTMLResponse)
async def read_hod_upload(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "hod/upload.html",
        {
            "request": request,
            "page": "upload",
            "email": email,
            "role": role,
        }
    )
    
@app.get("/hod/history", response_class=HTMLResponse)
async def read_hod_history(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    historyDocs = crud.get_history_hod(db, email)

    return templates.TemplateResponse(
        "hod/history.html",
        {
            "request": request,
            "page": "history",
            "role": role,
            "historyDocs": historyDocs,
            "docTypes": docTypes,
            "departments": departments
        }
    )
    

@app.get("/hod/pending", response_class=HTMLResponse)
async def read_std_pending(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    pendingDocs = crud.get_user_pending_docs(db, email)

    return templates.TemplateResponse(
        "hod/pending.html",
        {
            "request": request,
            "page": "pending",
            "role": role,
            "pendingDocs": pendingDocs,
            "docType": docTypes
        }
    )

    
@app.get("/hod/inbox", response_class=HTMLResponse)
async def read_hod_inbox(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)

    inboxDocs = crud.get_hod_inbox(db, email)

    return templates.TemplateResponse(
        "hod/inbox.html",
        {
            "request": request,
            "page": "inbox",
            "role": role,
            "inboxDocs": inboxDocs,
            "docTypes": docTypes,
            "departments": departments
        }
    )
    
@app.get("/hod/reports", response_class=HTMLResponse)
async def read_hod_reports(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "hod":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    allReports = crud.get_user_all_reports(db, email)

    return templates.TemplateResponse(
        "hod/reports.html",
        {
            "request": request,
            "page": "reports",
            "role": role,
            "docTypes": docTypes,
            "allReports": allReports,
            "departments": departments
        }
    )
    
@app.get("/hod/preview/{appNo}")
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
    
    if appDoc.status == "Approved" or appDoc.status == "Rejected":
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse(
        "/hod/view_doc.html",
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
 
@app.get("/faculty/dashboard", response_class=HTMLResponse)
async def read_faculty_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "faculty":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    approvedDocs = crud.get_user_approved_docs(db, email)

    return templates.TemplateResponse(
        "faculty/index.html",
        {
            "request": request,
            "page": "dashboard",
            "role": role,
            "docTypes": docTypes,
            "departments": departments,
            "approvedDocs": approvedDocs
        }
    )
 
@app.get("/faculty/upload", response_class=HTMLResponse)
async def read_faculty_upload(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "faculty":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "faculty/upload.html",
        {
            "request": request,
            "page": "upload",
            "role": role,
            "email": email,
            "docTypes": docTypes,
            "departments": departments,
        }
    )
 
@app.get("/faculty/pending", response_class=HTMLResponse)
async def read_faculty_pending(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "faculty":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    pendingDocs = crud.get_user_pending_docs(db, email)
    
    return templates.TemplateResponse(
        "faculty/pending.html",
        {
            "request": request,
            "page": "pending",
            "role": role,
            "email": email,
            "docTypes": docTypes,
            "departments": departments,
            "pendingDocs": pendingDocs
        }
    )
 
@app.get("/faculty/inbox", response_class=HTMLResponse)
async def read_faculty_inbox(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "faculty":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    inboxDocs = crud.get_faculty_inbox(db, email)
    
    return templates.TemplateResponse(
        "faculty/inbox.html",
        {
            "request": request,
            "page": "inbox",
            "role": role,
            "email": email,
            "docTypes": docTypes,
            "departments": departments,
            "inboxDocs": inboxDocs
        }
    )
 
@app.get("/faculty/reports", response_class=HTMLResponse)
async def read_faculty_reports(
    request: Request,
    db: Session = Depends(database.get_db)
):
    email = request.session.get('email')
    role = request.session.get('role')

    if role != "faculty":
        return RedirectResponse(url="/", status_code=303)
    if not email:
        return RedirectResponse(url="/login", status_code=303)
    
    allReports = crud.get_user_all_reports(db, email)
    
    return templates.TemplateResponse(
        "faculty/reports.html",
        {
            "request": request,
            "page": "reports",
            "role": role,
            "email": email,
            "docTypes": docTypes,
            "departments": departments,
            "allReports":allReports
        }
    )