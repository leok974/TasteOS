from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List

class CookCompleteRequest(BaseModel):
    servings_made: Optional[float] = None
    leftover_servings: Optional[float] = None
    create_leftover: bool = False
    final_notes: Optional[str] = None

class CookRecap(BaseModel):
    final_step_index: int
    completion_rate: float
    timers_used: List[dict]
    adjustments: List[dict]
    servings_made: Optional[float]
    leftovers_created: bool

class CookCompleteResponse(BaseModel):
    session_id: str
    completed_at: datetime
    recap: CookRecap
    note_entry_id: Optional[str]
    leftover_id: Optional[str]

class RecipeLearningsResponse(BaseModel):
    highlights: List[str]
    common_tags: List[str]
    recent_recaps: List[dict]
