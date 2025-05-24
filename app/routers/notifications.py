from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.notification import Notification
from app.core.security import get_current_user

router = APIRouter()

@router.get("/notifications")
def get_notifications(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Notification).filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Database & Security
from app.db.database import get_db
from app.core.security import get_current_user

# Models
from app.models.notification import Notification

router = APIRouter()

# Retrieve notifications for the current user, ordered by most recent
@router.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Fetch a list of notifications for the current user, ordered by timestamp descending.
    """
    return (
        db.query(Notification)
        .filter_by(user_id=current_user.id)
        .order_by(Notification.timestamp.desc())
        .all()
    )
