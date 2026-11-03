import uuid
from datetime import datetime
from sqlalchemy import Boolean,DateTime,Enum,String,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database import Base
from app.models.enums import UserRole
class User(Base):
    __tablename__="users"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    full_name:Mapped[str]=mapped_column(String(100),nullable=False)
    email:Mapped[str]=mapped_column(String(254),nullable=False,unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(255),nullable=False)
    role:Mapped[UserRole]=mapped_column(Enum(UserRole,name="user_role",native_enum=True),nullable=False,default=UserRole.USER,server_default=UserRole.USER.value)
    is_active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True,server_default="true")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now(),onupdate=func.now())
    reports=relationship("ItemReport",back_populates="reporter",foreign_keys="ItemReport.reporter_id")
    submitted_claims=relationship("Claim",back_populates="claimant",foreign_keys="Claim.claimant_id")
    reviewed_claims=relationship("Claim",back_populates="reviewer",foreign_keys="Claim.reviewer_id")
    audit_events=relationship("AuditEvent",back_populates="actor")
