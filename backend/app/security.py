import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# A short list of common weak passwords worth blocking outright.
# Not exhaustive - swap in a real breached-password check (e.g. HaveIBeenPwned
# k-anonymity API) before shipping this to production.
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


def validate_password_policy(
    password: str,
    policy,
    username: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """
    Enforce the password policy. `policy` is a models.PasswordPolicy row (or
    any object with the same attributes) - admin-editable, not hardcoded.
    Raises PasswordPolicyError on the first violation found.
    """
    if len(password) < policy.min_length:
        raise PasswordPolicyError(f"Password must be at least {policy.min_length} characters long")
    if len(password) > policy.max_length:
        raise PasswordPolicyError(f"Password must be at most {policy.max_length} characters long")
    if policy.require_uppercase and not _UPPER.search(password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter")
    if policy.require_lowercase and not _LOWER.search(password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter")
    if policy.require_digit and not _DIGIT.search(password):
        raise PasswordPolicyError("Password must contain at least one digit")
    if policy.require_special and not _SPECIAL.search(password):
        raise PasswordPolicyError("Password must contain at least one special character")
    if policy.block_common_passwords and password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError("This password is too common - choose something less guessable")
    if policy.block_username_in_password:
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
    """Returns the decoded payload, or raises jose.JWTError if the token is invalid/expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
