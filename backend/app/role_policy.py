"""
Shared lookups used by both routers/auth.py (register) and routers/admin.py
(role & policy management). Kept separate from models.py so it can hold
actual query logic, not just table definitions.
"""
from sqlalchemy.orm import Session

from app.models import PasswordPolicy, RoleModel


def get_default_role(db: Session) -> RoleModel:
    """The role assigned to newly registered users."""
    role = db.query(RoleModel).filter(RoleModel.is_default.is_(True)).first()
    if role is None:
        # Shouldn't happen once main.py's seeding has run, but fall back to
        # *some* role rather than letting registration hard-fail.
        role = db.query(RoleModel).order_by(RoleModel.created_at.asc()).first()
    return role


def get_active_policy(db: Session) -> PasswordPolicy:
    policy = db.query(PasswordPolicy).filter(PasswordPolicy.id == "default").first()
    if policy is None:
        policy = PasswordPolicy(id="default")
        db.add(policy)
        db.flush()
    return policy
