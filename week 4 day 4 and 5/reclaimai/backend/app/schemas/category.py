import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
class CategoryCreate(BaseModel):
    name:str=Field(min_length=2,max_length=60); description:str|None=Field(default=None,max_length=300)
    model_config=ConfigDict(extra="forbid")
    @field_validator("name",mode="before")
    @classmethod
    def clean_name(cls,v): return " ".join(v.split()) if isinstance(v,str) else v
    @field_validator("description",mode="before")
    @classmethod
    def clean_description(cls,v): return v.strip() if isinstance(v,str) else v
class CategoryUpdate(BaseModel):
    name:str|None=Field(default=None,min_length=2,max_length=60); description:str|None=Field(default=None,max_length=300); is_active:bool|None=None
    model_config=ConfigDict(extra="forbid")
    @field_validator("name",mode="before")
    @classmethod
    def clean_name(cls,v): return " ".join(v.split()) if isinstance(v,str) else v
    @field_validator("description",mode="before")
    @classmethod
    def clean_description(cls,v): return v.strip() if isinstance(v,str) else v
    @model_validator(mode="after")
    def reject_null_required_fields(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Category name cannot be null.")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("Category active state cannot be null.")
        return self
class CategoryResponse(BaseModel):
    id:uuid.UUID; name:str; description:str|None; is_active:bool; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class CategoryListResponse(BaseModel): items:list[CategoryResponse]; total:int
