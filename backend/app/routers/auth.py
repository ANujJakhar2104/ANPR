from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import AuditAction, User
from app.role_policy import get_active_policy, get_default_role
from app.schemas import PasswordPolicyOut, Token, UserCreate, UserOut
from app.security import (
    PasswordPolicyError,
    create_access_token,
    hash_password,
    validate_password_policy,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/password-policy", response_model=PasswordPolicyOut)
def public_password_policy(db: Session = Depends(get_db)):
    """
    Unauthenticated on purpose - the register page's live checklist needs
    these rules before the person has an account. The admin-only copy at
    GET /admin/password-policy returns the identical data; this just makes
    it reachable pre-login.
    """
    policy = get_active_policy(db)
    db.commit()
    return policy


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Password policy is admin-editable data now, so it's validated here
    # (where we have a db session) rather than at the Pydantic-schema level.
    policy = get_active_policy(db)
    try:
        validate_password_policy(payload.password, policy, username=payload.username, email=payload.email)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    existing = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.username)
    ).first()
    if existing:
        log_audit(db, AuditAction.USER_REGISTER, status="failure",
                   username=payload.username,
                   detail="Email or username already registered", request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already registered")

    default_role = get_default_role(db)
    if default_role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail="No default role configured - contact an administrator")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role_id=default_role.id,
    )
    db.add(user)
    db.flush()  # get user.id before writing the audit row
    log_audit(db, AuditAction.USER_REGISTER, status="success", user=user, request=request)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm's "username" field carries either the email or the username.
    identifier = form_data.username
    user = db.query(User).filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        log_audit(db, AuditAction.USER_LOGIN_FAILURE, status="failure",
                   username=identifier, detail="Bad credentials", request=request)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_audit(db, AuditAction.USER_LOGIN_FAILURE, status="failure", user=user,
                   detail="Account disabled", request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(subject=user.id, extra_claims={"is_admin": user.role.is_admin})
    log_audit(db, AuditAction.USER_LOGIN_SUCCESS, status="success", user=user, request=request)
    db.commit()
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_active_user)):
    return current_user
