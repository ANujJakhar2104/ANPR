import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.export import export_response
from app.models import AuditAction, AuditLog, Detection, DetectionJob, JobStatus, PasswordPolicy, RoleModel, User
from app.role_policy import get_active_policy
from app.schemas import (
    AdminSummaryOut,
    AuditLogOut,
    Page,
    PasswordPolicyOut,
    PasswordPolicyUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    SystemHealthOut,
    UserOut,
    UserRoleUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/system-health", response_model=SystemHealthOut)
def system_health(request: Request, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    ram = psutil.virtual_memory()
    disk_path = settings.OUTPUT_DIR if os.path.exists(settings.OUTPUT_DIR) else "/"
    disk = psutil.disk_usage(disk_path)

    interfaces = []
    io_by_nic = psutil.net_io_counters(pernic=True)
    for name, stats in psutil.net_if_stats().items():
        io = io_by_nic.get(name)
        interfaces.append({
            "name": name,
            "is_up": stats.isup,
            "speed_mbps": stats.speed,
            "bytes_sent": io.bytes_sent if io else 0,
            "bytes_recv": io.bytes_recv if io else 0,
        })

    log_audit(db, AuditAction.SYSTEM_HEALTH_CHECK, user=current_user, request=request)
    db.commit()

    return SystemHealthOut(
        cpu_percent=psutil.cpu_percent(interval=0.2),
        cpu_count=psutil.cpu_count() or 0,
        ram_percent=ram.percent,
        ram_used_gb=round(ram.used / (1024 ** 3), 2),
        ram_total_gb=round(ram.total / (1024 ** 3), 2),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / (1024 ** 3), 2),
        disk_total_gb=round(disk.total / (1024 ** 3), 2),
        interfaces=interfaces,
        uptime_seconds=round(time.time() - psutil.boot_time(), 1),
    )


@router.get("/summary", response_model=AdminSummaryOut)
def summary(db: Session = Depends(get_db)):
    roles = db.query(RoleModel).all()
    users_by_role = {role.name: db.query(User).filter(User.role_id == role.id).count() for role in roles}
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return AdminSummaryOut(
        total_users=db.query(User).count(),
        users_by_role=users_by_role,
        total_detections=db.query(Detection).count(),
        detections_last_24h=db.query(Detection).filter(Detection.created_at >= since).count(),
        total_video_jobs=db.query(DetectionJob).count(),
        jobs_pending_or_processing=db.query(DetectionJob)
            .filter(DetectionJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])).count(),
        jobs_failed=db.query(DetectionJob).filter(DetectionJob.status == JobStatus.FAILED).count(),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = db.query(RoleModel).filter(RoleModel.id == payload.role_id).first()
    if new_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    old_role_name = target.role.name
    target.role_id = new_role.id
    log_audit(db, AuditAction.ADMIN_ROLE_CHANGE, user=current_user,
               detail=f"{target.username}: {old_role_name} -> {new_role.name}", request=request)
    db.commit()
    db.refresh(target)
    return target


# --- roles: admin-managed, replaces the old fixed basic/pro/admin enum ------

@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db)):
    return db.query(RoleModel).order_by(RoleModel.created_at.asc()).all()


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(RoleModel).filter(RoleModel.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists")

    if payload.is_default:
        db.query(RoleModel).update({RoleModel.is_default: False})

    role = RoleModel(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        can_use_video=payload.can_use_video,
        is_admin=payload.is_admin,
        is_default=payload.is_default,
        is_system=False,
    )
    db.add(role)
    db.flush()
    log_audit(db, AuditAction.ADMIN_ROLE_CREATED, user=current_user, detail=role.name, request=request)
    db.commit()
    db.refresh(role)
    return role


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: str,
    payload: RoleUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Guard against locking everyone out: don't let the last admin-capable
    # role lose is_admin, and don't let the last default role lose is_default.
    if payload.is_admin is False and role.is_admin:
        other_admin = db.query(RoleModel).filter(RoleModel.id != role.id, RoleModel.is_admin.is_(True)).first()
        if other_admin is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="At least one role must have admin access")

    if payload.is_default is True:
        db.query(RoleModel).filter(RoleModel.id != role.id).update({RoleModel.is_default: False})
    elif payload.is_default is False and role.is_default:
        other_default = db.query(RoleModel).filter(RoleModel.id != role.id, RoleModel.is_default.is_(True)).first()
        if other_default is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="At least one role must be the default for new signups")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)

    log_audit(db, AuditAction.ADMIN_ROLE_UPDATED, user=current_user, detail=role.name, request=request)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Built-in roles can't be deleted")
    in_use = db.query(User).filter(User.role_id == role.id).count()
    if in_use:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"{in_use} user(s) still have this role - reassign them first")

    log_audit(db, AuditAction.ADMIN_ROLE_DELETED, user=current_user, detail=role.name, request=request)
    db.delete(role)
    db.commit()
    return None


# --- password policy: admin-editable, singleton row -------------------------

@router.get("/password-policy", response_model=PasswordPolicyOut)
def get_password_policy(db: Session = Depends(get_db)):
    policy = get_active_policy(db)
    db.commit()
    return policy


@router.patch("/password-policy", response_model=PasswordPolicyOut)
def update_password_policy(
    payload: PasswordPolicyUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = get_active_policy(db)
    updates = payload.model_dump(exclude_unset=True)
    if "min_length" in updates and "max_length" in updates:
        if updates["min_length"] > updates["max_length"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="min_length can't be greater than max_length")
    for field, value in updates.items():
        setattr(policy, field, value)

    log_audit(db, AuditAction.ADMIN_PASSWORD_POLICY_UPDATED, user=current_user,
               detail=", ".join(f"{k}={v}" for k, v in updates.items()), request=request)
    db.commit()
    db.refresh(policy)
    return policy


# --- audit log: filter, paginate, export ------------------------------------

def _apply_audit_filters(query, action: Optional[str], status_filter: Optional[str],
                          username: Optional[str], date_from: Optional[datetime], date_to: Optional[datetime]):
    if action:
        query = query.filter(AuditLog.action == action)
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)
    return query


@router.get("/audit-logs", response_model=Page[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    action: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    query = _apply_audit_filters(db.query(AuditLog), action, status_filter, username, date_from, date_to)
    total = query.count()
    rows = (
        query.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(items=rows, total=total, page=page, page_size=page_size)


AUDIT_EXPORT_COLUMNS = [
    ("timestamp", "Timestamp"),
    ("username", "Username"),
    ("action", "Action"),
    ("status", "Status"),
    ("detail", "Detail"),
    ("ip_address", "IP"),
]


@router.get("/audit-logs/export/{format}")
def export_audit_logs(
    format: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    action: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    if format not in ("csv", "html", "pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be csv, html, or pdf")

    query = _apply_audit_filters(db.query(AuditLog), action, status_filter, username, date_from, date_to)
    rows = query.order_by(AuditLog.timestamp.desc()).limit(5000).all()
    row_dicts = [{
        "timestamp": r.timestamp, "username": r.username, "action": r.action.value,
        "status": r.status, "detail": r.detail, "ip_address": r.ip_address,
    } for r in rows]

    log_audit(db, AuditAction.AUDIT_EXPORT, user=current_user,
               detail=f"format={format} rows={len(row_dicts)}", request=request)
    db.commit()

    return export_response(format, "Audit Log", "audit-log", AUDIT_EXPORT_COLUMNS, row_dicts)
