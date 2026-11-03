import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.models.enums import ClaimStatus
class ClaimCreate(BaseModel):
    lost_report_id:uuid.UUID; found_report_id:uuid.UUID; ownership_explanation:str=Field(min_length=20,max_length=1500); verification_answer:str=Field(min_length=2,max_length=300)
    model_config=ConfigDict(extra="forbid")
    @field_validator("ownership_explanation","verification_answer",mode="before")
    @classmethod
    def trim_claim_text(cls,value): return value.strip()
class ClaimReview(BaseModel):
    status:ClaimStatus
    review_comment:str|None=Field(default=None,min_length=3,max_length=1500)
    model_config=ConfigDict(extra="forbid")
    @field_validator("review_comment",mode="before")
    @classmethod
    def trim_comment(cls,value): return value.strip() if value is not None else value
class ClaimResponse(BaseModel):
    id:uuid.UUID; lost_report_id:uuid.UUID; found_report_id:uuid.UUID; claimant_id:uuid.UUID; status:ClaimStatus; ownership_explanation:str; review_comment:str|None; reviewer_id:uuid.UUID|None; version:int; created_at:datetime; reviewed_at:datetime|None; completed_at:datetime|None
    model_config=ConfigDict(from_attributes=True)
class ClaimListResponse(BaseModel): items:list[ClaimResponse]; page:int; page_size:int; total:int
