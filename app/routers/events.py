from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.schemas.event import EventCreate, EventOut, EventUpdate
from app.schemas.permission import ShareRequest, SharedUserOut
from app.schemas.event_version import EventVersionOut

from app.models.event import Event
from app.models.permission import EventPermission
from app.models.user import User
from app.models.event_version import EventVersion
from app.models.notification import Notification

from app.db.database import SessionLocal
from app.core.security import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def notify_event_participants(db, event_id: int, message: str):
    user_ids = db.query(EventPermission.user_id).filter_by(event_id=event_id).all()
    for (user_id,) in user_ids:
        db.add(Notification(user_id=user_id, event_id=event_id, message=message))
    db.commit()

@router.post("/events", response_model=EventOut)
def create_event(event: EventCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    conflict = db.query(Event).filter(
        Event.id != None,
        Event.start_time < event.end_time,
        Event.end_time > event.start_time,
        or_(Event.owner_id == current_user.id,
            Event.id.in_(db.query(EventPermission.event_id).filter(EventPermission.user_id == current_user.id)))
    ).first()

    if conflict:
        raise HTTPException(status_code=400, detail="Conflicting event exists in this time range")

    new_event = Event(**event.dict(), owner_id=current_user.id)
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@router.post("/events/batch")
def batch_create_events(events: list[EventCreate], db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    created = []
    for e in events:
        new_event = Event(**e.dict(), owner_id=current_user.id)
        db.add(new_event)
        db.flush()
        created.append(new_event)
    db.commit()
    return created

@router.get("/events", response_model=list[EventOut])
def get_events(skip: int = Query(0, ge=0), limit: int = Query(10, le=100), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    owned_events = db.query(Event).filter(Event.owner_id == current_user.id)
    shared_event_ids = db.query(EventPermission.event_id).filter(EventPermission.user_id == current_user.id)
    events = db.query(Event).filter(Event.id.in_(shared_event_ids.union_all(owned_events.with_entities(Event.id)))).offset(skip).limit(limit).all()
    return events

@router.get("/events/{event_id}", response_model=EventOut)
def get_event_by_id(event_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id and not db.query(EventPermission).filter_by(event_id=event_id, user_id=current_user.id).first():
        raise HTTPException(status_code=403, detail="Access denied")
    return event

@router.put("/events/{event_id}")
def update_event(event_id: int, updated_data: EventUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.owner_id != current_user.id:
        if not db.query(EventPermission).filter_by(event_id=event_id, user_id=current_user.id, role="editor").first():
            raise HTTPException(status_code=403, detail="Not allowed to update this event")

    conflict = db.query(Event).filter(
        Event.id != event.id,
        Event.start_time < updated_data.end_time,
        Event.end_time > updated_data.start_time,
        or_(Event.owner_id == current_user.id,
            Event.id.in_(db.query(EventPermission.event_id).filter(EventPermission.user_id == current_user.id)))
    ).first()

    if conflict:
        raise HTTPException(status_code=400, detail="Conflicting event exists during this time")

    version = EventVersion(event_id=event.id, updated_by=current_user.id, **{k: getattr(event, k) for k in EventUpdate.__annotations__})
    db.add(version)

    for key, value in updated_data.dict().items():
        setattr(event, key, value)

    db.commit()
    notify_event_participants(db, event_id, "Event has been updated.")
    return {"message": "Event updated and version saved"}

@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete this event")

    notify_event_participants(db, event_id, "An event you were part of has been deleted.")

    db.query(EventPermission).filter_by(event_id=event_id).delete()
    db.query(EventVersion).filter_by(event_id=event_id).delete()
    db.delete(event)
    db.commit()
    return {"message": f"Event {event_id} deleted"}

@router.post("/events/{event_id}/share")
def share_event(event_id: int, request: ShareRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event or event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to share this event")

    for user in request.users:
        if user.user_id == current_user.id:
            continue
        existing = db.query(EventPermission).filter_by(event_id=event_id, user_id=user.user_id).first()
        if existing:
            existing.role = user.role
        else:
            db.add(EventPermission(event_id=event_id, user_id=user.user_id, role=user.role))

    db.commit()
    notify_event_participants(db, event_id, "You have been granted access to an event.")
    return {"message": "Event shared successfully"}

@router.get("/events/{event_id}/permissions", response_model=list[SharedUserOut])
def list_permissions(event_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event or event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(EventPermission).filter_by(event_id=event_id).all()

@router.put("/events/{event_id}/permissions/{user_id}")
def update_permission(event_id: int, user_id: int, new_role: SharedUserOut, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event or event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    permission = db.query(EventPermission).filter_by(event_id=event_id, user_id=user_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    permission.role = new_role.role
    db.commit()
    return {"message": "Permission updated"}

@router.delete("/events/{event_id}/permissions/{user_id}")
def delete_permission(event_id: int, user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event or event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    permission = db.query(EventPermission).filter_by(event_id=event_id, user_id=user_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(permission)
    db.commit()
    return {"message": "Access removed"}

@router.get("/events/{event_id}/changelog", response_model=list[EventVersionOut])
def get_changelog(event_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id and not db.query(EventPermission).filter_by(event_id=event_id, user_id=current_user.id).first():
        raise HTTPException(status_code=403, detail="Not allowed to view changelog")
    return db.query(EventVersion).filter_by(event_id=event_id).order_by(EventVersion.updated_at.desc()).all()

@router.get("/events/{event_id}/diff/{v1}/{v2}")
def get_diff(event_id: int, v1: int, v2: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id and not db.query(EventPermission).filter_by(event_id=event_id, user_id=current_user.id).first():
        raise HTTPException(status_code=403, detail="Not allowed to view diff")

    ver1 = db.query(EventVersion).filter_by(id=v1, event_id=event_id).first()
    ver2 = db.query(EventVersion).filter_by(id=v2, event_id=event_id).first()

    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    diffs = {field: {"v1": getattr(ver1, field), "v2": getattr(ver2, field)}
             for field in EventUpdate.__annotations__ if getattr(ver1, field) != getattr(ver2, field)}
    return {"diff": diffs}

@router.post("/events/{event_id}/rollback/{version_id}")
def rollback_event(event_id: int, version_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can rollback")

    version = db.query(EventVersion).filter_by(id=version_id, event_id=event_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    db.add(EventVersion(event_id=event.id, updated_by=current_user.id, **{k: getattr(event, k) for k in EventUpdate.__annotations__}))

    for field in EventUpdate.__annotations__:
        setattr(event, field, getattr(version, field))

    db.commit()
    notify_event_participants(db, event_id, f"Event was rolled back to version {version_id}.")
    return {"message": f"Rolled back to version {version_id}"}

@router.get("/events/{event_id}/history/{version_id}", response_model=EventVersionOut)
def get_event_version_by_id(event_id: int, version_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    event = db.query(Event).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.owner_id != current_user.id and not db.query(EventPermission).filter_by(event_id=event_id, user_id=current_user.id).first():
        raise HTTPException(status_code=403, detail="Not allowed to view history")

    version = db.query(EventVersion).filter_by(id=version_id, event_id=event_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version