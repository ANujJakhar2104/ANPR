import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RoleModel(Base):
    """
    Admin-managed roles. Replaces the old fixed basic/pro/admin enum.
    Permissions are explicit capability flags rather than a ranked level,
    so an admin can create e.g. "Auditor" (can_use_video=False, is_admin=False,
    plus whatever future flags get added) without it slotting into a hierarchy.
    """
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, index=True, nullable=False)  # machine slug, e.g. "pro"
    display_name = Column(String, nullable=False)  # shown in the UI, e.g. "Pro"
    description = Column(String, nullable=True)

    # Capability flags - add new ones here as the product grows.
    can_use_video = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Exactly one role should have is_default=True at any time - it's what
    # /auth/register assigns new users. Enforced in code (admin.py), not a
    # DB constraint, since SQLite partial-unique-indexes are a hassle.
    is_default = Column(Boolean, default=False, nullable=False)
    # Built-in roles (basic/pro/admin) can't be deleted, only edited, so the
    # app always has at least one admin-capable and one default role.
    is_system = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(String, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("RoleModel", back_populates="users")
    jobs = relationship("DetectionJob", back_populates="owner", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="owner", cascade="all, delete-orphan")


class PasswordPolicy(Base):
    """
    Singleton table (one row, id='default') - admin-editable password rules.
    security.validate_password_policy() reads this instead of hardcoded
    constants, and the register page's live checklist mirrors the same rules
    via GET /admin/password-policy/public.
    """
    __tablename__ = "password_policy"

    id = Column(String, primary_key=True, default=lambda: "default")
    min_length = Column(Integer, default=10, nullable=False)
    max_length = Column(Integer, default=128, nullable=False)
    require_uppercase = Column(Boolean, default=True, nullable=False)
    require_lowercase = Column(Boolean, default=True, nullable=False)
    require_digit = Column(Boolean, default=True, nullable=False)
    require_special = Column(Boolean, default=True, nullable=False)
    block_common_passwords = Column(Boolean, default=True, nullable=False)
    block_username_in_password = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditAction(str, enum.Enum):
    USER_REGISTER = "User has Registered"
    USER_LOGIN_SUCCESS = "User has Logged In Successfully"
    USER_LOGIN_FAILURE = "User has Failed to Log In"
    TOKEN_VERIFY_FAILURE = "Token Verification Failed"
    ROLE_DENIED = "Role Access has been Denied"
    DETECTION_IMAGE_REQUEST = "Detection Image has been Requested"
    DETECTION_IMAGE_SUCCESS = "Detection Image has been Processed Successfully"
    DETECTION_IMAGE_FAILURE = "Detection Image has been Processing Failed"
    DETECTION_VIDEO_REQUEST = "Detection Video has been Requested"
    DETECTION_VIDEO_SUCCESS = "Detection Video has been Processed Successfully"
    DETECTION_VIDEO_FAILURE = "Detection Video has been Processing Failed"
    JOB_STATUS_CHECK = "Job Status Checked"
    RESULT_DOWNLOAD = "Results Downloaded"
    DETECTIONS_EXPORT = "Detections have been Exported"
    AUDIT_EXPORT = "Audit Logs have been Exported"
    ADMIN_ROLE_CHANGE = "Admin Role has been Changed"
    ADMIN_ROLE_CREATED = "Admin Role has been Created"
    ADMIN_ROLE_UPDATED = "Admin Role has been Updated"
    ADMIN_ROLE_DELETED = "Admin Role has been Deleted"
    ADMIN_PASSWORD_POLICY_UPDATED = "Admin Password Policy has been Updated"
    SYSTEM_HEALTH_CHECK = "System Health has been Checked"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # Denormalized so the record survives even if the user is later deleted
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String, nullable=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    status = Column(String, nullable=False, default="success")  # "success" | "failure"
    detail = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DetectionJob(Base):
    __tablename__ = "detection_jobs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    input_filename = Column(String, nullable=False)
    csv_path = Column(String, nullable=True)
    interpolated_csv_path = Column(String, nullable=True)
    output_video_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="jobs")


class DetectionSource(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("detection_jobs.id", ondelete="CASCADE"), nullable=True)
    source = Column(Enum(DetectionSource), nullable=False)

    car_id = Column(String, nullable=False)
    car_bbox = Column(String, nullable=True)
    license_plate_bbox = Column(String, nullable=True)
    license_plate_bbox_score = Column(String, nullable=True)

    license_number = Column(String, nullable=True)
    license_number_score = Column(String, nullable=True)
    raw_ocr_text = Column(String, nullable=True)
    char_analysis = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    owner = relationship("User", back_populates="detections")
