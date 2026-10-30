import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, get_current_user, require_roles
from app.models import (
    AuditLog, Booking, BookingItem, BookingTicket, Event, EventReview, Notification,
    OrganizerApplication, Payment, RefundRequest, SessionEvent, ShowSeatHold, User,
    Venue,
)
from app.schemas import (
    EventModerationDecision, OrganizerApplicationCreate, OrganizerApplicationDecision,
    ProfileUpdate, RefundDecision, RefundRequestCreate, ReviewCreate, UserStatusUpdate,
)

router = APIRouter(prefix="/portal", tags=["Customer, Organizer and Admin Portal"])


def audit(db, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, details: dict | None = None):
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details or {}, default=str),
    ))


def notify(db, user_id: int, title: str, message: str, kind: str = "info", link: str | None = None):
    db.add(Notification(user_id=user_id, title=title, message=message, kind=kind, link=link))


def public_user(user: User) -> dict:
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "phone": user.phone, "role": user.role, "is_active": user.is_active,
        "created_at": user.created_at,
    }


@router.get("/profile")
def get_profile(user: Annotated[User, Depends(get_current_user)]):
    return public_user(user)


@router.patch("/profile")
def update_profile(payload: ProfileUpdate, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=422, detail="Provide at least one profile field")
    if "name" in data and data["name"] is not None:
        user.name = data["name"].strip()
    if "phone" in data:
        user.phone = data["phone"].strip() if data["phone"] else None
    audit(db, user.id, "profile.updated", "user", user.id, data)
    db.commit()
    db.refresh(user)
    return public_user(user)


@router.post("/organizer-applications", status_code=status.HTTP_201_CREATED)
def apply_as_organizer(payload: OrganizerApplicationCreate, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    if user.role != "customer":
        raise HTTPException(status_code=409, detail="Only customer accounts can submit an organizer application")
    existing = db.scalar(select(OrganizerApplication).where(OrganizerApplication.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail=f"An organizer application already exists with status: {existing.status}")
    application = OrganizerApplication(
        user_id=user.id,
        organization_name=payload.organization_name.strip(),
        contact_phone=payload.contact_phone.strip(),
        website=str(payload.website) if payload.website else None,
        description=payload.description.strip(),
    )
    db.add(application)
    audit(db, user.id, "organizer_application.submitted", "organizer_application", None, {"organization_name": application.organization_name})
    db.commit()
    db.refresh(application)
    return {
        "id": application.id, "organization_name": application.organization_name,
        "status": application.status, "created_at": application.created_at,
    }


@router.get("/organizer-applications/me")
def my_organizer_application(db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    item = db.scalar(select(OrganizerApplication).where(OrganizerApplication.user_id == user.id))
    if not item:
        return None
    return {
        "id": item.id, "organization_name": item.organization_name,
        "contact_phone": item.contact_phone, "website": item.website,
        "description": item.description, "status": item.status,
        "review_note": item.review_note, "created_at": item.created_at,
        "reviewed_at": item.reviewed_at,
    }


@router.get("/admin/organizer-applications")
def list_organizer_applications(
    db: DbSession,
    _: Annotated[User, Depends(require_roles("admin"))],
    status_filter: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(OrganizerApplication).order_by(OrganizerApplication.created_at.desc())
    count_stmt = select(func.count(OrganizerApplication.id))
    if status_filter != "all":
        stmt = stmt.where(OrganizerApplication.status == status_filter)
        count_stmt = count_stmt.where(OrganizerApplication.status == status_filter)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [{
            "id": item.id, "user": public_user(item.user),
            "organization_name": item.organization_name, "contact_phone": item.contact_phone,
            "website": item.website, "description": item.description, "status": item.status,
            "created_at": item.created_at,
        } for item in items],
        "page": page, "page_size": page_size, "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/admin/organizer-applications/{application_id}/decision")
def decide_organizer_application(
    application_id: int,
    payload: OrganizerApplicationDecision,
    db: DbSession,
    admin: Annotated[User, Depends(require_roles("admin"))],
):
    item = db.scalar(select(OrganizerApplication).where(OrganizerApplication.id == application_id).with_for_update())
    if not item:
        raise HTTPException(status_code=404, detail="Organizer application not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="This application has already been reviewed")
    user = db.get(User, item.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Applicant account no longer exists")
    item.status = "approved" if payload.decision == "approve" else "rejected"
    item.reviewed_by = admin.id
    item.reviewed_at = datetime.now()
    item.review_note = payload.note
    if payload.decision == "approve":
        user.role = "organizer"
    notify(
        db, user.id,
        "Organizer application approved" if payload.decision == "approve" else "Organizer application update",
        "Your organizer account is now active." if payload.decision == "approve" else (payload.note or "Your organizer application was not approved."),
        "success" if payload.decision == "approve" else "warning",
        "/portal",
    )
    audit(db, admin.id, f"organizer_application.{payload.decision}d", "organizer_application", item.id, {"user_id": user.id, "note": payload.note})
    db.commit()
    return {"id": item.id, "status": item.status, "user": public_user(user), "review_note": item.review_note}


@router.get("/dashboard")
def dashboard(db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    if user.role == "admin":
        return {
            "role": "admin",
            "users": db.scalar(select(func.count(User.id))) or 0,
            "active_users": db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
            "venues": db.scalar(select(func.count(Venue.id)).where(Venue.is_active.is_(True))) or 0,
            "events": db.scalar(select(func.count(Event.id))) or 0,
            "pending_events": db.scalar(select(func.count(Event.id)).where(Event.status == "pending_approval")) or 0,
            "pending_organizer_applications": db.scalar(select(func.count(OrganizerApplication.id)).where(OrganizerApplication.status == "pending")) or 0,
            "pending_refunds": db.scalar(select(func.count(RefundRequest.id)).where(RefundRequest.status == "requested")) or 0,
            "confirmed_bookings": db.scalar(select(func.count(Booking.id)).where(Booking.status == "confirmed")) or 0,
            "gross_sales": db.scalar(select(func.coalesce(func.sum(Booking.total_amount), 0)).where(Booking.status == "confirmed")) or Decimal("0.00"),
        }
    if user.role == "organizer":
        event_ids = select(Event.id).where(Event.organizer_id == user.id)
        return {
            "role": "organizer",
            "events": db.scalar(select(func.count(Event.id)).where(Event.organizer_id == user.id)) or 0,
            "pending_events": db.scalar(select(func.count(Event.id)).where(Event.organizer_id == user.id, Event.status == "pending_approval")) or 0,
            "confirmed_bookings": db.scalar(select(func.count(Booking.id)).join(SessionEvent, Booking.session_id == SessionEvent.id).where(SessionEvent.event_id.in_(event_ids), Booking.status == "confirmed")) or 0,
            "gross_sales": db.scalar(select(func.coalesce(func.sum(Booking.total_amount), 0)).join(SessionEvent, Booking.session_id == SessionEvent.id).where(SessionEvent.event_id.in_(event_ids), Booking.status == "confirmed")) or Decimal("0.00"),
        }
    return {
        "role": "customer",
        "bookings": db.scalar(select(func.count(Booking.id)).where(Booking.user_id == user.id)) or 0,
        "upcoming_bookings": db.scalar(select(func.count(Booking.id)).join(SessionEvent, Booking.session_id == SessionEvent.id).where(Booking.user_id == user.id, Booking.status == "confirmed", SessionEvent.starts_at >= datetime.now())) or 0,
        "unread_notifications": db.scalar(select(func.count(Notification.id)).where(Notification.user_id == user.id, Notification.read_at.is_(None))) or 0,
    }


@router.get("/events/mine")
def organizer_events(
    db: DbSession,
    user: Annotated[User, Depends(require_roles("organizer", "admin"))],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Event).order_by(Event.created_at.desc())
    count_stmt = select(func.count(Event.id))
    if user.role == "organizer":
        stmt = stmt.where(Event.organizer_id == user.id)
        count_stmt = count_stmt.where(Event.organizer_id == user.id)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [{
            "id": e.id, "title": e.title, "description": e.description,
            "status": e.status, "city_id": e.city_id, "venue_id": e.venue_id,
            "category_id": e.category_id, "poster_url": e.poster_url,
            "created_at": e.created_at,
        } for e in items],
        "page": page, "page_size": page_size, "total": total,
    }


@router.post("/events/{event_id}/submit")
def submit_event_for_approval(
    event_id: int,
    db: DbSession,
    organizer: Annotated[User, Depends(require_roles("organizer"))],
):
    event = db.scalar(select(Event).where(Event.id == event_id, Event.organizer_id == organizer.id).with_for_update())
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=409, detail="Only draft or rejected events can be submitted")
    if not db.scalar(select(SessionEvent.id).where(SessionEvent.event_id == event.id, SessionEvent.status == "scheduled", SessionEvent.starts_at > datetime.now())):
        raise HTTPException(status_code=409, detail="Add at least one future scheduled session before submission")
    event.status = "pending_approval"
    for admin in db.scalars(select(User).where(User.role == "admin", User.is_active.is_(True))).all():
        notify(db, admin.id, "Event requires review", f"{event.title} was submitted by {organizer.name}.", "moderation", "/portal")
    audit(db, organizer.id, "event.submitted_for_approval", "event", event.id)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "status": event.status}


@router.get("/admin/events/pending")
def pending_events(db: DbSession, _: Annotated[User, Depends(require_roles("admin"))]):
    events = db.scalars(select(Event).where(Event.status == "pending_approval").order_by(Event.created_at)).all()
    return [{
        "id": e.id, "title": e.title, "description": e.description,
        "organizer": public_user(e.organizer), "city": e.city.name,
        "venue": e.venue.name, "created_at": e.created_at,
    } for e in events]


@router.post("/admin/events/{event_id}/decision")
def moderate_event(
    event_id: int,
    payload: EventModerationDecision,
    db: DbSession,
    admin: Annotated[User, Depends(require_roles("admin"))],
):
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Event is not awaiting moderation")
    event.status = "published" if payload.decision == "approve" else "rejected"
    notify(db, event.organizer_id, "Event approved" if payload.decision == "approve" else "Event needs changes",
           f"{event.title}: " + ("your event is now public." if payload.decision == "approve" else (payload.note or "Please update and resubmit.")),
           "success" if payload.decision == "approve" else "warning", "/portal")
    audit(db, admin.id, f"event.{payload.decision}d", "event", event.id, {"note": payload.note})
    db.commit()
    db.refresh(event)
    return {"id": event.id, "status": event.status}


@router.get("/admin/users")
def admin_users(
    db: DbSession,
    _: Annotated[User, Depends(require_roles("admin"))],
    q: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, pattern="^(customer|organizer|admin)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    stmt = select(User).order_by(User.created_at.desc())
    count_stmt = select(func.count(User.id))
    if q:
        stmt = stmt.where((User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
        count_stmt = count_stmt.where((User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [public_user(item) for item in items], "page": page, "page_size": page_size, "total": total}


@router.patch("/admin/users/{user_id}/status")
def set_user_status(user_id: int, payload: UserStatusUpdate, db: DbSession, admin: Annotated[User, Depends(require_roles("admin"))]):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own admin account")
    if target.role == "admin" and target.id != admin.id:
        raise HTTPException(status_code=403, detail="Use a separate super-admin procedure to disable another admin")
    target.is_active = payload.is_active
    audit(db, admin.id, "user.status_changed", "user", target.id, {"is_active": target.is_active})
    db.commit()
    return public_user(target)


@router.patch("/admin/venues/{venue_id}/status")
def set_venue_status(venue_id: int, payload: UserStatusUpdate, db: DbSession, admin: Annotated[User, Depends(require_roles("admin"))]):
    venue = db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    venue.is_active = payload.is_active
    audit(db, admin.id, "venue.status_changed", "venue", venue.id, {"is_active": venue.is_active})
    db.commit()
    return {"id": venue.id, "name": venue.name, "is_active": venue.is_active}


@router.get("/notifications")
def list_notifications(
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
):
    stmt = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items = db.scalars(stmt).all()
    return {"items": [{
        "id": n.id, "title": n.title, "message": n.message,
        "kind": n.kind, "link": n.link, "read_at": n.read_at,
        "created_at": n.created_at,
    } for n in items]}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read_at = item.read_at or datetime.now()
    db.commit()
    return {"id": item.id, "read_at": item.read_at}


@router.post("/notifications/read-all")
def mark_all_notifications_read(db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)).values(read_at=datetime.now()))
    db.commit()
    return {"status": "ok"}


@router.get("/events/{event_id}/reviews")
def list_event_reviews(event_id: int, db: DbSession):
    if not db.get(Event, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    items = db.scalars(select(EventReview).where(EventReview.event_id == event_id).order_by(EventReview.created_at.desc()).limit(100)).all()
    aggregate = db.execute(select(func.avg(EventReview.rating), func.count(EventReview.id)).where(EventReview.event_id == event_id)).one()
    return {
        "average_rating": round(float(aggregate[0] or 0), 2),
        "review_count": int(aggregate[1] or 0),
        "items": [{
            "id": item.id, "rating": item.rating, "comment": item.comment,
            "user_name": item.user.name, "created_at": item.created_at,
        } for item in items],
    }


@router.post("/events/{event_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_event_review(
    event_id: int,
    payload: ReviewCreate,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
):
    event = db.get(Event, event_id)
    if not event or event.status != "published":
        raise HTTPException(status_code=404, detail="Published event not found")
    booking = db.scalar(select(Booking).where(
        Booking.id == payload.booking_id,
        Booking.user_id == user.id,
        Booking.status == "confirmed",
    ).with_for_update())
    if not booking or booking.session.event_id != event.id or booking.session.ends_at > datetime.now():
        raise HTTPException(status_code=403, detail="A completed, confirmed booking for this event is required to review it")
    review = EventReview(event_id=event.id, user_id=user.id, booking_id=booking.id, rating=payload.rating, comment=payload.comment)
    db.add(review)
    audit(db, user.id, "event.review_created", "event", event.id, {"rating": payload.rating})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This booking or event already has a review")
    db.refresh(review)
    return {"id": review.id, "event_id": event.id, "rating": review.rating, "comment": review.comment}


@router.post("/bookings/{booking_id}/refund-request", status_code=status.HTTP_201_CREATED)
def request_refund(booking_id: int, payload: RefundRequestCreate, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id).with_for_update())
    if not booking or booking.status != "confirmed":
        raise HTTPException(status_code=404, detail="Confirmed booking not found")
    if booking.session.starts_at <= datetime.now():
        raise HTTPException(status_code=409, detail="Refund requests must be submitted before the show starts")
    payment = db.scalar(select(Payment).where(Payment.booking_id == booking.id, Payment.status == "succeeded").order_by(Payment.id.desc()))
    if not payment:
        raise HTTPException(status_code=409, detail="No successful payment record exists for this booking")
    request_item = RefundRequest(
        booking_id=booking.id, user_id=user.id, payment_id=payment.id,
        reason=payload.reason.strip(), amount=booking.total_amount,
    )
    db.add(request_item)
    notify(db, user.id, "Refund request received", f"Refund request for booking {booking.booking_reference} is awaiting review.", "refund")
    audit(db, user.id, "refund.requested", "booking", booking.id, {"amount": str(booking.total_amount), "payment_provider": payment.provider})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A refund request already exists for this booking")
    db.refresh(request_item)
    return {"id": request_item.id, "booking_id": booking.id, "amount": request_item.amount, "status": request_item.status}


@router.get("/admin/refunds")
def list_refunds(db: DbSession, _: Annotated[User, Depends(require_roles("admin"))], status_filter: str = Query(default="requested", pattern="^(requested|approved|rejected|processed|all)$")):
    stmt = select(RefundRequest).order_by(RefundRequest.created_at.desc())
    if status_filter != "all":
        stmt = stmt.where(RefundRequest.status == status_filter)
    items = db.scalars(stmt.limit(200)).all()
    return {"items": [{
        "id": item.id, "booking_id": item.booking_id, "user": public_user(item.user),
        "reason": item.reason, "amount": item.amount, "status": item.status,
        "created_at": item.created_at, "resolution_note": item.resolution_note,
    } for item in items]}


@router.post("/admin/refunds/{refund_id}/decision")
def decide_refund(refund_id: int, payload: RefundDecision, db: DbSession, admin: Annotated[User, Depends(require_roles("admin"))]):
    item = db.scalar(select(RefundRequest).where(RefundRequest.id == refund_id).with_for_update())
    if not item:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if item.status not in {"requested", "approved"}:
        raise HTTPException(status_code=409, detail="This refund request has already been resolved")
    if payload.decision == "approve":
        item.status = "approved"
    elif payload.decision == "reject":
        item.status = "rejected"
    else:
        payment = db.get(Payment, item.payment_id) if item.payment_id else None
        if not payment:
            raise HTTPException(status_code=409, detail="Payment record not found")
        if payment.provider != "demo_upi" and payment.provider != "demo_upi_qr" and payment.provider != "demo_card" and payment.provider != "demo_netbanking":
            raise HTTPException(status_code=409, detail="A live provider refund adapter is not configured; do not mark a real refund as processed")
        payment.status = "refunded"
        item.booking.status = "cancelled"
        item.status = "processed"
    item.reviewed_by = admin.id
    item.reviewed_at = datetime.now()
    item.resolution_note = payload.note
    notify(db, item.user_id, "Refund request updated", f"Your refund request is now {item.status}.", "refund")
    audit(db, admin.id, f"refund.{item.status}", "refund_request", item.id, {"booking_id": item.booking_id, "note": payload.note})
    db.commit()
    return {"id": item.id, "status": item.status, "note": item.resolution_note}


@router.post("/tickets/check-in")
def check_in_ticket(
    ticket_code: str = Query(min_length=12, max_length=64),
    db: DbSession = None,
    staff: User = Depends(require_roles("admin", "organizer")),
):
    ticket = db.scalar(select(BookingTicket).where(BookingTicket.ticket_code == ticket_code).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket code not found")
    booking = db.get(Booking, ticket.booking_id)
    if not booking or booking.status != "confirmed":
        raise HTTPException(status_code=409, detail="Booking is not valid for check-in")
    if ticket.checked_in_at:
        raise HTTPException(status_code=409, detail=f"Ticket already checked in at {ticket.checked_in_at.isoformat()}")
    session = booking.session
    event = session.event
    if staff.role == "organizer" and (not event or event.organizer_id != staff.id):
        raise HTTPException(status_code=403, detail="You can only check in tickets for your own events")
    ticket.checked_in_at = datetime.now()
    ticket.checked_in_by = staff.id
    audit(db, staff.id, "ticket.checked_in", "booking_ticket", ticket.id, {"booking_id": booking.id})
    db.commit()
    return {"status": "checked_in", "booking_reference": booking.booking_reference, "checked_in_at": ticket.checked_in_at}


@router.get("/organizer/analytics")
def organizer_analytics(db: DbSession, organizer: Annotated[User, Depends(require_roles("organizer"))]):
    rows = db.execute(
        select(
            Event.id, Event.title,
            func.count(func.distinct(Booking.id)),
            func.coalesce(func.sum(Booking.total_amount), 0),
        )
        .outerjoin(SessionEvent, SessionEvent.event_id == Event.id)
        .outerjoin(Booking, Booking.session_id == SessionEvent.id)
        .where(Event.organizer_id == organizer.id, Booking.status == "confirmed")
        .group_by(Event.id, Event.title)
    ).all()
    return {"events": [{
        "event_id": row[0], "title": row[1],
        "confirmed_bookings": int(row[2] or 0), "gross_sales": row[3],
    } for row in rows]}


@router.get("/admin/audit")
def list_audit_logs(
    db: DbSession,
    _: Annotated[User, Depends(require_roles("admin"))],
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, max_length=100),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = db.scalars(stmt).all()
    return {"items": [{
        "id": row.id, "actor_id": row.actor_id, "action": row.action,
        "entity_type": row.entity_type, "entity_id": row.entity_id,
        "details": row.details, "created_at": row.created_at,
    } for row in rows]}


@router.get("/reports/sales")
def sales_report(
    db: DbSession,
    _: Annotated[User, Depends(require_roles("admin"))],
    days: int = Query(default=30, ge=1, le=365),
):
    since = datetime.now().date()
    rows = db.execute(
        select(
            func.date(Booking.created_at),
            func.count(Booking.id),
            func.coalesce(func.sum(Booking.total_amount), 0),
        ).where(Booking.status == "confirmed", Booking.created_at >= datetime.combine(since, datetime.min.time()).replace(day=since.day) - __import__("datetime").timedelta(days=days - 1))
        .group_by(func.date(Booking.created_at)).order_by(func.date(Booking.created_at))
    ).all()
    return {"days": days, "series": [{
        "date": str(row[0]), "confirmed_bookings": int(row[1] or 0),
        "gross_sales": row[2],
    } for row in rows]}


@router.post("/admin/maintenance/cleanup")
def run_inventory_cleanup(db: DbSession, admin: Annotated[User, Depends(require_roles("admin"))]):
    now = datetime.now()
    holds = db.execute(ShowSeatHold.__table__.delete().where(ShowSeatHold.expires_at <= now)).rowcount or 0
    expired = db.execute(update(Booking).where(Booking.status == "pending", Booking.expires_at.is_not(None), Booking.expires_at <= now).values(status="expired")).rowcount or 0
    audit(db, admin.id, "maintenance.inventory_cleanup", "system", None, {"holds_removed": holds, "bookings_expired": expired})
    db.commit()
    return {"holds_removed": holds, "bookings_expired": expired, "ran_at": now}
