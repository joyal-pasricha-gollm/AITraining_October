from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _error(code: str, message: str, request_id: str, fields: dict | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": request_id,
        }
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get("code")
    if code is None:
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "INVALID_TRANSITION",
            422: "VALIDATION_ERROR",
        }.get(exc.status_code, "REQUEST_FAILED")
    message = detail.get("message", str(exc.detail) if not detail else "The request could not be completed.")
    body = _error(code, message, _request_id(request), detail.get("fields"))
    for key in ("missing_tables",):
        if key in detail:
            body["error"][key] = detail[key]
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path", "header")]
        name = ".".join(location) or "request"
        fields.setdefault(name, "Check this value and try again.")
    return JSONResponse(
        status_code=422,
        content=_error("VALIDATION_ERROR", "Some fields are invalid.", _request_id(request), fields),
    )
