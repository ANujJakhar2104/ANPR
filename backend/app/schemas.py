from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.security import validate_password_policy


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

    @field_validator("password")
    @classmethod
    def password_ok(cls, v: str, info) -> str:
        validate_password_policy(v)
        return v


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DetectionOut(BaseModel):
    car_id: int
    car_bbox: list[float]
    license_plate_bbox: list[float]
    license_plate_bbox_score: float
    license_number: Optional[str] = None
    license_number_score: Optional[float] = None


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
