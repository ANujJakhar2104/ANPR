from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, field_validator

T = TypeVar("T")


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_ok(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("Username must be between 3 and 32 characters")
        if not v.replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, '.' and '_'")
        return v

    # Password strength is no longer checked here: the policy now lives in
    # the DB (admin-editable), so it's validated in the route where we have
    # a db session - see routers/auth.py.


class RoleOut(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    can_use_video: bool
    is_admin: bool
    is_default: bool
    is_system: bool

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    can_use_video: bool = False
    is_admin: bool = False
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str) -> str:
        v = v.strip().lower().replace(" ", "_")
        if not (2 <= len(v) <= 32):
            raise ValueError("Role name must be between 2 and 32 characters")
        if not v.replace("_", "").isalnum():
            raise ValueError("Role name may only contain letters, numbers and underscores")
        return v


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    can_use_video: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_default: Optional[bool] = None


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    role: RoleOut
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role_id: str


class PasswordPolicyOut(BaseModel):
    min_length: int
    max_length: int
    require_uppercase: bool
    require_lowercase: bool
    require_digit: bool
    require_special: bool
    block_common_passwords: bool
    block_username_in_password: bool

    class Config:
        from_attributes = True


class PasswordPolicyUpdate(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    require_uppercase: Optional[bool] = None
    require_lowercase: Optional[bool] = None
    require_digit: Optional[bool] = None
    require_special: Optional[bool] = None
    block_common_passwords: Optional[bool] = None
    block_username_in_password: Optional[bool] = None

    @field_validator("min_length")
    @classmethod
    def min_length_ok(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (6 <= v <= 64):
            raise ValueError("min_length must be between 6 and 64")
        return v

    @field_validator("max_length")
    @classmethod
    def max_length_ok(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (8 <= v <= 256):
            raise ValueError("max_length must be between 8 and 256")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CharAnalysisEntry(BaseModel):
    position: int
    raw_char: str
    corrected_char: str
    expected_type: str
    was_corrected: bool


class DetectionOut(BaseModel):
    """One match from a single synchronous /detect/image call."""
    car_id: int
    car_bbox: Optional[list[float]] = None
    license_plate_bbox: list[float]
    license_plate_bbox_score: float
    license_number: Optional[str] = None
    license_number_score: Optional[float] = None
    raw_ocr_text: Optional[str] = None
    char_analysis: Optional[list[CharAnalysisEntry]] = None


class ImageDetectionResponse(BaseModel):
    detections: list[DetectionOut]
    annotated_image_base64: str


class JobOut(BaseModel):
    id: str
    status: str
    input_filename: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DetectionRecordOut(BaseModel):
    """One persisted row from the `detections` table - what /detect/detections lists."""
    id: str
    user_id: str
    job_id: Optional[str] = None
    source: str
    car_id: str
    license_number: Optional[str] = None
    license_number_score: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    char_analysis: Optional[list[CharAnalysisEntry]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class AuditLogOut(BaseModel):
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    username: Optional[str] = None
    action: str
    status: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class SystemHealthOut(BaseModel):
    cpu_percent: float
    cpu_count: int
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    interfaces: list[dict]
    uptime_seconds: float


class AdminSummaryOut(BaseModel):
    total_users: int
    users_by_role: dict[str, int]
    total_detections: int
    detections_last_24h: int
    total_video_jobs: int
    jobs_pending_or_processing: int
    jobs_failed: int
