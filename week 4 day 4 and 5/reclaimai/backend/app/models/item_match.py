import uuid
from datetime import datetime
from sqlalchemy import Boolean,CheckConstraint,DateTime,Enum,ForeignKey,Integer,String,UniqueConstraint,func
from sqlalchemy.dialects.postgresql import JSONB,UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.database import Base
from app.models.enums import MatchLevel
class ItemMatch(Base):
    __tablename__="item_matches"
    __table_args__=(UniqueConstraint("lost_report_id","found_report_id",name="lost_found_pair"),CheckConstraint("category_score BETWEEN 0 AND 25",name="category_score_range"),CheckConstraint("location_score BETWEEN 0 AND 20",name="location_score_range"),CheckConstraint("date_score BETWEEN 0 AND 15",name="date_score_range"),CheckConstraint("colour_score BETWEEN 0 AND 10",name="colour_score_range"),CheckConstraint("brand_score BETWEEN 0 AND 10",name="brand_score_range"),CheckConstraint("name_score BETWEEN 0 AND 10",name="name_score_range"),CheckConstraint("description_score BETWEEN 0 AND 10",name="description_score_range"),CheckConstraint("total_score BETWEEN 0 AND 100",name="total_score_range"))
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    lost_report_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("item_reports.id",ondelete="RESTRICT"),nullable=False,index=True)
    found_report_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("item_reports.id",ondelete="RESTRICT"),nullable=False,index=True)
    category_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0"); location_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0")
    date_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0"); colour_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0")
    brand_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0"); name_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0")
    description_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0"); total_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0,server_default="0",index=True)
    match_level:Mapped[MatchLevel]=mapped_column(Enum(MatchLevel,name="match_level",native_enum=True),nullable=False,index=True)
    explanation:Mapped[dict]=mapped_column(JSONB,nullable=False,default=dict,server_default="{}")
    algorithm_version:Mapped[str]=mapped_column(String(50),nullable=False,default="rules-v1",server_default="rules-v1")
    is_active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True,server_default="true",index=True)
    calculated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    lost_report=relationship("ItemReport",back_populates="lost_matches",foreign_keys=[lost_report_id]); found_report=relationship("ItemReport",back_populates="found_matches",foreign_keys=[found_report_id])
