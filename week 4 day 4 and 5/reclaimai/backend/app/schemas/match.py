import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict
from app.models.enums import MatchLevel
class MatchResponse(BaseModel):
    id:uuid.UUID; lost_report_id:uuid.UUID; found_report_id:uuid.UUID; category_score:int; location_score:int; date_score:int; colour_score:int; brand_score:int; name_score:int; description_score:int; total_score:int; match_level:MatchLevel; explanation:dict; algorithm_version:str; calculated_at:datetime
    model_config=ConfigDict(from_attributes=True)
