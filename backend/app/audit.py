from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, User


def log_audit(
    db: Session,
    action: AuditAction,
    status: str = "success",
    user: Optional[User] = None,
    username: Optional[str] = None,
    detail: Optional[str] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """
    Writes one audit log row. Call this from every route that touches
    authentication or the detection pipeline - success AND failure.

    Committed independently of the caller's own transaction state isn't
    required here because FastAPI's get_db dependency commits/closes per
    request; callers should still db.commit() after calling this if they
    haven't already, so the log is never silently rolled back with the
    business change.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        username=username or (user.username if user else None),
        action=action,
        status=status,
        detail=detail,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(entry)
    db.flush()
    return entry
