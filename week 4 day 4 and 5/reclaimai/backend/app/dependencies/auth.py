import uuid
from typing import Annotated
import jwt
from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
bearer_scheme=HTTPBearer(auto_error=False)
DatabaseSession=Annotated[Session,Depends(get_db)]
def get_current_user(
    credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer_scheme)],
    database_session:DatabaseSession,
)->User:
    error=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"code":"UNAUTHENTICATED","message":"Authentication credentials are invalid."},headers={"WWW-Authenticate":"Bearer"})
    if credentials is None: raise error
    try:
        subject=decode_access_token(credentials.credentials).get("sub")
        if not subject: raise error
        user_id=uuid.UUID(subject)
    except (jwt.InvalidTokenError,ValueError,TypeError) as exc: raise error from exc
    user=database_session.get(User,user_id)
    if user is None or not user.is_active: raise error
    return user
CurrentUser=Annotated[User,Depends(get_current_user)]
def get_optional_current_user(
    credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer_scheme)],
    database_session:DatabaseSession,
)->User|None:
    if credentials is None:
        return None
    try:
        subject=decode_access_token(credentials.credentials).get("sub")
        if not subject:
            return None
        user_id=uuid.UUID(subject)
    except (jwt.InvalidTokenError,ValueError,TypeError):
        return None
    user=database_session.get(User,user_id)
    return user if user is not None and user.is_active else None
OptionalCurrentUser=Annotated[User|None,Depends(get_optional_current_user)]
def require_admin(current_user:CurrentUser)->User:
    if current_user.role!=UserRole.ADMIN: raise HTTPException(status_code=403,detail={"code":"FORBIDDEN","message":"Administrator permission is required."})
    return current_user
AdminUser=Annotated[User,Depends(require_admin)]
