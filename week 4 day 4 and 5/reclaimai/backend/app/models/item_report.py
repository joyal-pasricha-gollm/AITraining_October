import uuid
from datetime import date,datetime,time
from sqlalchemy import CheckConstraint,Date,DateTime,Enum,ForeignKey,Integer,String,Text,Time,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database import Base
from app.models.enums import MatchingStatus,ReportStatus,ReportType
class ItemReport(Base):
    __tablename__="item_reports"; __table_args__=(
        CheckConstraint("version >= 1",name="version_positive"),
        CheckConstraint(
            "report_type <> 'FOUND' OR (verification_question IS NOT NULL AND verification_answer_hash IS NOT NULL)",
            name="found_verification_required",
        ),
        CheckConstraint(
            "report_type <> 'LOST' OR (verification_question IS NULL AND verification_answer_hash IS NULL AND storage_instructions IS NULL)",
            name="lost_private_fields_empty",
        ),
    )
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    reference:Mapped[str]=mapped_column(String(30),nullable=False,unique=True,index=True)
    report_type:Mapped[ReportType]=mapped_column(Enum(ReportType,name="report_type",native_enum=True),nullable=False,index=True)
    reporter_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="RESTRICT"),nullable=False,index=True)
    category_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("categories.id",ondelete="RESTRICT"),nullable=False,index=True)
    item_name:Mapped[str]=mapped_column(String(120),nullable=False,index=True)
    colour:Mapped[str]=mapped_column(String(40),nullable=False,index=True)
    brand:Mapped[str|None]=mapped_column(String(80),nullable=True,index=True)
    event_date:Mapped[date]=mapped_column(Date,nullable=False,index=True)
    approximate_time:Mapped[time|None]=mapped_column(Time,nullable=True)
    area:Mapped[str]=mapped_column(String(120),nullable=False,index=True)
    location_details:Mapped[str|None]=mapped_column(String(300),nullable=True)
    description:Mapped[str]=mapped_column(Text,nullable=False)
    distinguishing_features:Mapped[str|None]=mapped_column(Text,nullable=True)
    verification_question:Mapped[str|None]=mapped_column(String(300),nullable=True)
    verification_answer_hash:Mapped[str|None]=mapped_column(String(255),nullable=True)
    storage_instructions:Mapped[str|None]=mapped_column(String(300),nullable=True)
    image_url:Mapped[str|None]=mapped_column(String(500),nullable=True)
    status:Mapped[ReportStatus]=mapped_column(Enum(ReportStatus,name="report_status",native_enum=True),nullable=False,default=ReportStatus.ACTIVE,server_default=ReportStatus.ACTIVE.value,index=True)
    matching_status:Mapped[MatchingStatus]=mapped_column(Enum(MatchingStatus,name="matching_status",native_enum=True),nullable=False,default=MatchingStatus.PENDING,server_default=MatchingStatus.PENDING.value)
    version:Mapped[int]=mapped_column(Integer,nullable=False,default=1,server_default="1")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now(),onupdate=func.now())
    reporter=relationship("User",back_populates="reports",foreign_keys=[reporter_id]); category=relationship("Category",back_populates="reports")
    lost_matches=relationship("ItemMatch",back_populates="lost_report",foreign_keys="ItemMatch.lost_report_id")
    found_matches=relationship("ItemMatch",back_populates="found_report",foreign_keys="ItemMatch.found_report_id")
    lost_claims=relationship("Claim",back_populates="lost_report",foreign_keys="Claim.lost_report_id")
    found_claims=relationship("Claim",back_populates="found_report",foreign_keys="Claim.found_report_id")
    __mapper_args__={"version_id_col":version,"version_id_generator":False}
