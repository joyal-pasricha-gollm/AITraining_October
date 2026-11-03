from fastapi import APIRouter
from app.dependencies.auth import CurrentUser
from app.schemas.user import UserResponse
router=APIRouter(prefix="/api/v1/users",tags=["Users"])
@router.get("/me",response_model=UserResponse)
def me(current_user:CurrentUser):return current_user
