from pydantic import BaseModel
from datetime import datetime

class EventVersionOut(BaseModel):
    id: int
    event_id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: str
    is_recurring: bool
    recurrence_pattern: str
    updated_at: datetime
    updated_by: int

    class Config:
        from_attributes = True
