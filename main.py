import secrets

from fastapi import FastAPI
from api.api import api_router

app = FastAPI()


from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from api.api import api_router
from core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.session import get_db
from worker.task import delever_mail
from faker import Faker
import random



# app = FastAPI(
#     title="master API",
#     version="0.1.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )
app = FastAPI(
    title="master API",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
)

fake = Faker("en_IN")


class DeliverMailRequest(BaseModel):
    authority_name: str
    subject: str
    body: str
    receiver_emails: list[str]
    cc_emails: list[str] | None = None
    bcc_emails: list[str] | None = None
    body_type: str = "html"
    priority_level: int = Field(default=5, ge=0, le=10)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if settings.PYTHON_ENV == "production" else ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,     # Critical for cookie-based authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "X-API-Key"],
)

# 🛡️ Global Exception Handler (Standardized Responses)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "errors": None
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msg = errors[0].get("msg") if errors else "Validation failed"
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": error_msg,
            "data": None,
            "error": "Validation Error"
        }
    )


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "connect-src 'self' https://cdn.jsdelivr.net;"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(api_router, prefix="/api")

@app.post("/api/send-email", status_code=202)
def queue_email(
    payload: DeliverMailRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    if not settings.MASTER_API_KEY or not secrets.compare_digest(
        x_api_key, settings.MASTER_API_KEY
    ):
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        delever_mail(**payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not queue email task") from exc

    return {"success": True, "message": "mail send to the api"}

@app.get("/api/college-student-data", status_code=202)
def fake_data(
):
    try:
        name = fake.name()
        mobile = random.randint(6000000000, 9999999999)
        roll_number = f"24CSEAIML{random.randint(100, 999)}"
        return {
            "success": True,
            "message": "fetched data",
            "data": {
                "name": name,
                "mobile_no": mobile,
                "roll_number": roll_number
            },
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"reason:- {str(e)}",
            "data": None,
            "error": str(e)
        }
    


@app.api_route("/", methods=["GET", "HEAD"])
async def root(key: str, db: Session = Depends(get_db)):
    try:
        if key != settings.API_ACCESS_KEY:
            raise HTTPException(status_code=401, detail="Invalid key")

        db.execute(text("SELECT 1"))

        return {"status": "ok"}

    except HTTPException as http:
        raise http
    except Exception as e:
        print(f"\nERROR:- {str(e)}\n")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        