import uuid
from datetime import date,datetime,time,timedelta
from pydantic import BaseModel,ConfigDict,Field,HttpUrl,ValidationInfo,field_validator,model_validator
from app.models.enums import MatchingStatus,ReportStatus,ReportType
class ReportCreate(BaseModel):
    report_type:ReportType; category_id:uuid.UUID; item_name:str=Field(min_length=2,max_length=120); colour:str=Field(min_length=2,max_length=40); brand:str|None=Field(None,max_length=80); event_date:date; approximate_time:time|None=None; area:str=Field(min_length=2,max_length=120); location_details:str|None=Field(None,max_length=300); description:str=Field(min_length=10,max_length=1500); distinguishing_features:str|None=Field(None,max_length=800); verification_question:str|None=Field(None,min_length=10,max_length=300);     verification_answer:str|None=Field(None,min_length=2,max_length=300); storage_instructions:str|None=Field(None,max_length=300); image_url:HttpUrl|None=Field(None,max_length=500)
    model_config=ConfigDict(extra="forbid")
    @field_validator("item_name","colour","brand","area","location_details","description","distinguishing_features","verification_question","verification_answer","storage_instructions",mode="before")
    @classmethod
    def trim_text(cls,value,info:ValidationInfo):
        if not isinstance(value,str):
            return value
        value=value.strip()
        return None if value=="" and info.field_name in {"brand","location_details","distinguishing_features","verification_question","verification_answer","storage_instructions"} else value
    @model_validator(mode="after")
    def validate_report(self):
        if self.event_date>date.today()+timedelta(days=1): raise ValueError("Event date cannot be more than one day in the future.")
        if self.report_type==ReportType.FOUND and (not self.verification_question or not self.verification_answer): raise ValueError("Found reports require a verification question and answer.")
        if self.report_type==ReportType.LOST and (self.verification_question or self.verification_answer or self.storage_instructions):
            raise ValueError("Private verification and storage fields are only allowed for found reports.")
        return self
class ReportUpdate(BaseModel):
    category_id:uuid.UUID|None=None; item_name:str|None=Field(None,min_length=2,max_length=120); colour:str|None=Field(None,min_length=2,max_length=40); brand:str|None=Field(None,max_length=80); event_date:date|None=None; approximate_time:time|None=None; area:str|None=Field(None,min_length=2,max_length=120); location_details:str|None=Field(None,max_length=300); description:str|None=Field(None,min_length=10,max_length=1500); distinguishing_features:str|None=Field(None,max_length=800); verification_question:str|None=Field(None,min_length=10,max_length=300); verification_answer:str|None=Field(None,min_length=2,max_length=300); storage_instructions:str|None=Field(None,max_length=300); image_url:HttpUrl|None=Field(None,max_length=500)
    model_config=ConfigDict(extra="forbid")
    @field_validator("item_name","colour","brand","area","location_details","description","distinguishing_features","verification_question","verification_answer","storage_instructions",mode="before")
    @classmethod
    def trim_text(cls,value,info:ValidationInfo):
        if not isinstance(value,str):
            return value
        value=value.strip()
        return None if value=="" and info.field_name in {"brand","location_details","distinguishing_features","verification_question","verification_answer","storage_instructions"} else value
    @field_validator("event_date")
    @classmethod
    def event_date_not_too_far_in_future(cls,value):
        if value is not None and value>date.today()+timedelta(days=1):
            raise ValueError("Event date cannot be more than one day in the future.")
        return value
    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("category_id","item_name","colour","event_date","area","description"):
            if field in self.model_fields_set and getattr(self,field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self
class ReportResponse(BaseModel):
    id:uuid.UUID; reference:str; report_type:ReportType; reporter_id:uuid.UUID; category_id:uuid.UUID; item_name:str; colour:str; brand:str|None; event_date:date; approximate_time:time|None; area:str; location_details:str|None; description:str; distinguishing_features:str|None; verification_question:str|None; storage_instructions:str|None; image_url:str|None; status:ReportStatus; matching_status:MatchingStatus; version:int; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
class PublicReportResponse(BaseModel):
    id:uuid.UUID; reference:str; report_type:ReportType; category_id:uuid.UUID; item_name:str; colour:str; brand:str|None; event_date:date; area:str; description:str; distinguishing_features:str|None; image_url:str|None; status:ReportStatus; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class ReportListResponse(BaseModel): items:list[PublicReportResponse]; page:int; page_size:int; total:int
class PrivateReportListResponse(BaseModel): items:list[ReportResponse]; page:int; page_size:int; total:int
class AdminReportListResponse(BaseModel): items:list[ReportResponse]; page:int; page_size:int; total:int
class ClaimQuestionResponse(BaseModel): question:str
class ReportWithdraw(BaseModel):
    reason:str=Field(min_length=3,max_length=500)
    model_config=ConfigDict(extra="forbid")
    @field_validator("reason",mode="before")
    @classmethod
    def trim_reason(cls,value): return value.strip() if isinstance(value,str) else value
