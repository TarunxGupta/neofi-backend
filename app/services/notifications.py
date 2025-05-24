from app.models.notification import Notification
from app.models.permission import EventPermission

def notify_event_participants(db, event_id: int, message: str):
    """
    Sends a notification with the given message to all users
    who have permission for the specified event.
    """
    user_ids = db.query(EventPermission.user_id).filter_by(event_id=event_id).all()
    
    notifications = [
        Notification(user_id=user_id, event_id=event_id, message=message)
        for (user_id,) in user_ids
    ]
    
    db.add_all(notifications)
    db.commit()
