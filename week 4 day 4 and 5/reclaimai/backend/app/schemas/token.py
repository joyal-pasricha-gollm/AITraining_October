from pydantic import BaseModel,ConfigDict,EmailStr,Field

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email:EmailStr
    password:str=Field(min_length=1,max_length=128)
    model_config=ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    access_token:str
    token_type:str="bearer"
    user:UserResponse

class TokenPayload(BaseModel): sub:str
