from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class TripCreate(BaseModel):
    employee_id: str = Field(min_length=2, max_length=50)
    destination: str = Field(min_length=2, max_length=120)
    start_date: date
    end_date: date
    purpose: str = Field(min_length=2, max_length=300)

    @field_validator("employee_id", "destination", "purpose")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.start_date < date.today():
            raise ValueError("start_date must be today or later")
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("trip duration cannot exceed 31 days")
        return self

class Trip(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trip_id: int
    employee_id: str
    destination: str
    start_date: date
    end_date: date
    purpose: str
    status: str
    created_at: datetime

class AskRequest(BaseModel):
    session_id: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    question: str = Field(min_length=2, max_length=500)
    trip_id: int | None = Field(default=None, ge=1)

    @field_validator("session_id", "question")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

class AskResponse(BaseModel):
    session_id: str
    trip_id: int
    answer: str
    source: Literal["trip+live-weather", "trip-only"]
