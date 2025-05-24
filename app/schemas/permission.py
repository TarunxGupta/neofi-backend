from pydantic import BaseModel
from typing import List

class ShareUser(BaseModel):
    user_id: int
    role: str  # viewer / editor

class SharedUserOut(BaseModel):
    user_id: int
    role: str

    class Config:
        from_attributes = True


class ShareRequest(BaseModel):
    users: List[ShareUser]
