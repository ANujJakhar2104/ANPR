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
