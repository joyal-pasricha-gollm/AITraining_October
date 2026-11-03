import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict,EmailStr,Field,field_validator
from app.models.enums import UserRole
class UserRegister(BaseModel):
    full_name:str=Field(min_length=2,max_length=100); email:EmailStr; password:str=Field(min_length=8,max_length=128)
    model_config=ConfigDict(extra="forbid")
    @field_validator("full_name",mode="before")
    @classmethod
    def clean_name(cls,v): return " ".join(v.split())
    @field_validator("email")
    @classmethod
    def clean_email(cls,v): return str(v).strip().lower()
    @field_validator("password")
    @classmethod
    def valid_password(cls,v):
        if not any(c.isupper() for c in v) or not any(c.islower() for c in v) or not any(c.isdigit() for c in v): raise ValueError("Password must contain uppercase, lowercase and numeric characters.")
        return v
class UserResponse(BaseModel):
    id:uuid.UUID; full_name:str; email:EmailStr; role:UserRole; is_active:bool; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
