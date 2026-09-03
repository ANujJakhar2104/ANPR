import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_COMMON_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "qwerty123",
    "letmein1", "welcome1", "iloveyou", "admin123", "changeme",
}

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]")


class PasswordPolicyError(ValueError):
    """Raised with a human-readable reason a password was rejected."""

## found error first and then raise password policy error with reason.
def validate_password_policy(password: str, username: Optional[str] = None, email: Optional[str] = None) -> None:
   
    if len(password) < 10:
        raise PasswordPolicyError("Password must be at least 10 characters long")
    if len(password) > 128:
        raise PasswordPolicyError("Password must be at most 128 characters long")
    if not _UPPER.search(password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter")
    if not _LOWER.search(password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter")
    if not _DIGIT.search(password):
        raise PasswordPolicyError("Password must contain at least one digit")
    if not _SPECIAL.search(password):
        raise PasswordPolicyError("Password must contain at least one special character")
    if password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError("This password is too common - choose something less guessable")
    if username and username.lower() in password.lower():
        raise PasswordPolicyError("Password must not contain your username")
    if email and email.split("@")[0].lower() in password.lower():
        raise PasswordPolicyError("Password must not contain your email address")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
