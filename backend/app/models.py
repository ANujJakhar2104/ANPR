import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("DetectionJob", back_populates="owner", cascade="all, delete-orphan")


class AuditAction(str, enum.Enum):
    USER_REGISTER = "USER_REGISTER"
    USER_LOGIN_SUCCESS = "USER_LOGIN_SUCCESS"
    USER_LOGIN_FAILURE = "USER_LOGIN_FAILURE"
    TOKEN_VERIFY_FAILURE = "TOKEN_VERIFY_FAILURE"
    DETECTION_IMAGE_REQUEST = "DETECTION_IMAGE_REQUEST"
    DETECTION_IMAGE_SUCCESS = "DETECTION_IMAGE_SUCCESS"
    DETECTION_IMAGE_FAILURE = "DETECTION_IMAGE_FAILURE"
    DETECTION_VIDEO_REQUEST = "DETECTION_VIDEO_REQUEST"
    DETECTION_VIDEO_SUCCESS = "DETECTION_VIDEO_SUCCESS"
    DETECTION_VIDEO_FAILURE = "DETECTION_VIDEO_FAILURE"
    JOB_STATUS_CHECK = "JOB_STATUS_CHECK"
    RESULT_DOWNLOAD = "RESULT_DOWNLOAD"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String, nullable=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    status = Column(String, nullable=False, default="success") 
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
