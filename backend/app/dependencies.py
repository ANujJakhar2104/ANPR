from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.database import get_db
from app.models import AuditAction, User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        log_audit(db, AuditAction.TOKEN_VERIFY_FAILURE, status="failure",
                   detail="JWT decode/verify failed", request=request)
        db.commit()
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        log_audit(db, AuditAction.TOKEN_VERIFY_FAILURE, status="failure",
                   detail=f"Token subject {user_id} has no matching user", request=request)
        db.commit()
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return current_user
