import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.core.errors import http_exception_handler, validation_exception_handler
from app.database import engine
from app.routers import admin, auth, categories, claims, dashboard, matches, reports, users
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger=logging.getLogger("reclaimai.api")
app=FastAPI(title=settings.app_name,description="Backend API for ReclaimAI",version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location","X-Request-ID"],
)


@app.middleware("http")
async def request_context(request:Request,call_next):
    request_id=uuid.uuid4().hex
    request.state.request_id=request_id
    started=time.perf_counter()
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        round((time.perf_counter()-started)*1000),
    )
    return response


app.add_exception_handler(StarletteHTTPException,http_exception_handler)
app.add_exception_handler(RequestValidationError,validation_exception_handler)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request:Request,exc:Exception):
    logger.error(
        "request_failed request_id=%s error_type=%s",
        getattr(request.state,"request_id",""),
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error":{
                "code":"INTERNAL_ERROR",
                "message":"The request could not be completed.",
                "fields":{},
                "request_id":getattr(request.state,"request_id",""),
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request:Request,exc:SQLAlchemyError):
    logger.error(
        "database_request_failed request_id=%s error_type=%s",
        getattr(request.state,"request_id",""),
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=503,
        content={
            "error":{
                "code":"UNAVAILABLE",
                "message":"The database is temporarily unavailable.",
                "fields":{},
                "request_id":getattr(request.state,"request_id",""),
            }
        },
    )


for router in [auth.router,users.router,categories.router,reports.router,matches.router,claims.router,dashboard.router,admin.router]:
    app.include_router(router)


@app.get("/")
def root():
    return {
        "application":"ReclaimAI",
        "message":"ReclaimAI API is running",
        "version":settings.app_version,
        "environment":settings.app_environment,
    }


@app.get("/api/v1/health")
def health():
    return {"status":"healthy","service":settings.app_name}


@app.get("/api/v1/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            row=connection.execute(
                text("SELECT current_database() database_name, current_user database_user")
            ).mappings().one()
        return {"status":"healthy","database":row["database_name"],"database_user":row["database_user"]}
    except SQLAlchemyError as exc:
        raise StarletteHTTPException(
            status_code=503,
            detail={
                "code":"UNAVAILABLE",
                "message":"The API could not connect to the database.",
            },
        ) from exc


@app.get("/api/v1/health/schema")
def schema_health():
    required={
        "users","categories","item_reports","item_matches","claims","audit_events",
        "idempotency_records","alembic_version",
    }
    available=set(inspect(engine).get_table_names())
    missing=sorted(required-available)
    if missing:
        raise StarletteHTTPException(
            503,
            detail={
                "code":"DATABASE_SCHEMA_INCOMPLETE",
                "message":"Required database tables are missing.",
                "missing_tables":missing,
            },
        )
    return {"status":"healthy","required_table_count":len(required),"tables":sorted(required)}
