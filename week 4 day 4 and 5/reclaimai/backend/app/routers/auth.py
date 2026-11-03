from fastapi import APIRouter,HTTPException,status
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from app.core.security import create_access_token,hash_password,verify_password
from app.dependencies.auth import DatabaseSession
from app.models.user import User
from app.schemas.token import LoginRequest,TokenResponse
from app.schemas.user import UserRegister,UserResponse
router=APIRouter(prefix="/api/v1/auth",tags=["Authentication"])
@router.post("/register",response_model=UserResponse,status_code=201)
def register(data:UserRegister,db:DatabaseSession):
    email=str(data.email).lower()
    if db.scalar(select(User).where(func.lower(User.email)==email)): raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"An account with this email already exists."})
    user=User(full_name=data.full_name,email=email,password_hash=hash_password(data.password)); db.add(user)
    try: db.commit(); db.refresh(user)
    except IntegrityError as e: db.rollback(); raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"An account with this email already exists."}) from e
    return user
@router.post("/login",response_model=TokenResponse)
def login(data:LoginRequest,db:DatabaseSession):
    user=db.scalar(select(User).where(func.lower(User.email)==str(data.email).strip().lower()))
    if user is None or not user.is_active or not verify_password(data.password,user.password_hash):
        raise HTTPException(401,detail={"code":"INVALID_CREDENTIALS","message":"Email or password is incorrect."},headers={"WWW-Authenticate":"Bearer"})
    return TokenResponse(access_token=create_access_token(str(user.id)),user=UserResponse.model_validate(user))
