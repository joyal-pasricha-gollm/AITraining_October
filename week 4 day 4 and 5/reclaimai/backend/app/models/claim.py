import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint,DateTime,Enum,ForeignKey,Index,Integer,String,Text,func,text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database import Base
from app.models.enums import ClaimStatus
class Claim(Base):
    __tablename__="claims"; __table_args__=(
        CheckConstraint("version >= 1",name="version_positive"),
        Index(
            "uq_claim_active_pair_claimant",
            "lost_report_id",
            "found_report_id",
            "claimant_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING','UNDER_REVIEW','APPROVED')"),
        ),
    )
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    lost_report_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("item_reports.id",ondelete="RESTRICT"),nullable=False,index=True)
    found_report_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("item_reports.id",ondelete="RESTRICT"),nullable=False,index=True)
    claimant_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="RESTRICT"),nullable=False,index=True)
    ownership_explanation:Mapped[str]=mapped_column(Text,nullable=False); verification_answer_hash:Mapped[str]=mapped_column(String(255),nullable=False)
    status:Mapped[ClaimStatus]=mapped_column(Enum(ClaimStatus,name="claim_status",native_enum=True),nullable=False,default=ClaimStatus.PENDING,server_default=ClaimStatus.PENDING.value,index=True)
    review_comment:Mapped[str|None]=mapped_column(Text,nullable=True); reviewer_id:Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="RESTRICT"),nullable=True,index=True)
    version:Mapped[int]=mapped_column(Integer,nullable=False,default=1,server_default="1")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now()); reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    lost_report=relationship("ItemReport",back_populates="lost_claims",foreign_keys=[lost_report_id]); found_report=relationship("ItemReport",back_populates="found_claims",foreign_keys=[found_report_id]); claimant=relationship("User",back_populates="submitted_claims",foreign_keys=[claimant_id]); reviewer=relationship("User",back_populates="reviewed_claims",foreign_keys=[reviewer_id])
    __mapper_args__={"version_id_col":version,"version_id_generator":False}
