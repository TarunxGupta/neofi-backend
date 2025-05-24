from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint
from app.db.database import Base

class EventPermission(Base):
    __tablename__ = "event_permissions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(String, nullable=False)  # viewer, editor

    __table_args__ = (UniqueConstraint("event_id", "user_id", name="_event_user_uc"),)
