from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import AuditAction, User
from app.schemas import Token, UserCreate, UserOut
from app.security import (
    PasswordPolicyError,
    create_access_token,
    hash_password,
    validate_password_policy,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

## check password policy and register user
#checks policy using pydantic

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    
    try:
        validate_password_policy(payload.password, username=payload.username, email=payload.email)
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

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()  # get user.id before writing the audit row
    log_audit(db, AuditAction.USER_REGISTER, status="success", user=user, request=request)
    db.commit()
    db.refresh(user)
    return user

# OAuth2PasswordRequestForm's "username" field contains one of  : email or username.

@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

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

    token = create_access_token(subject=user.id)
    log_audit(db, AuditAction.USER_LOGIN_SUCCESS, status="success", user=user, request=request)
    db.commit()
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_active_user)):
    return current_user
