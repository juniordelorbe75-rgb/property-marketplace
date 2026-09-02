import logging
import os
from time import perf_counter
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.config import parse_admin_user_ids, parse_cors_origins
from backend.routes.properties import router as property_router
from backend.routes.users import router as user_router
from backend.routes.favorites import router as favorite_router
from backend.routes.inquiries import router as inquiry_router
from backend.routes.uploads import UPLOAD_DIRECTORY, router as upload_router
from backend.routes.reports import router as report_router
from backend.routes.auth import router as auth_router


load_dotenv()
logger = logging.getLogger(__name__)

allowed_origins = parse_cors_origins(
    os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
)
parse_admin_user_ids(os.getenv("ADMIN_USER_IDS"))

app = FastAPI(
    title = "Property Marketplace API",
    description = "API for buying, selling, renting and searching properties",
    version = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count"],
)

app.include_router(property_router)
app.include_router(user_router)
app.include_router(favorite_router)
app.include_router(inquiry_router)
app.include_router(upload_router)
app.include_router(report_router)
app.include_router(auth_router)

UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads/property-images",
    StaticFiles(directory=UPLOAD_DIRECTORY),
    name="property-images",
)


@app.middleware("http")
async def add_request_tracing(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    is_sensitive_response = (
        bool(request.headers.get("authorization"))
        or request.url.path.startswith("/users/")
        or request.url.path.startswith("/auth/")
        or response.status_code >= 400
    )
    if is_sensitive_response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    logger.info(
        "%s %s completed with %s in %.1fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    error: SQLAlchemyError,
):
    logger.error(
        "Database operation failed for %s %s (%s) request_id=%s",
        request.method,
        request.url.path,
        type(error).__name__,
        getattr(request.state, "request_id", "unknown"),
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database operation failed. Please try again.",
            "request_id": getattr(request.state, "request_id", None),
        },
        headers={
            "Retry-After": "3",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    error: Exception,
):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unexpected application failure for %s %s (%s) request_id=%s",
        request.method,
        request.url.path,
        type(error).__name__,
        request_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "request_id": request_id,
        },
        headers={
            "X-Request-ID": request_id,
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )

@app.get("/health")
def health_check():

    return {
        "status": "ok"
    }


@app.get("/ready")
def readiness_check(session: Session = Depends(get_db)):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from error

    return {
        "status": "ready",
        "database": "ok",
    }


@app.get("/")
def home():
    return {
        "message": "Property Marketplace API is running"
    }
