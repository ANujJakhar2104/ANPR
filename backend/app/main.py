from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.anpr.pipeline import load_models
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import PasswordPolicy, RoleModel, User
from app.routers import admin, auth, detect

# Seeded once on first startup; after that these are plain rows an admin can
# rename, retarget or add to freely via /admin/roles.
_DEFAULT_ROLES = [
    dict(name="basic", display_name="Basic", description="Image detection only.",
         can_use_video=False, is_admin=False, is_default=True, is_system=True),
    dict(name="pro", display_name="Pro", description="Image and video detection.",
         can_use_video=True, is_admin=False, is_default=False, is_system=True),
    dict(name="admin", display_name="Admin", description="Full access, including user and role management.",
         can_use_video=True, is_admin=True, is_default=False, is_system=True),
]


def _seed_roles_and_policy() -> None:
    db = SessionLocal()
    try:
        if db.query(RoleModel).count() == 0:
            for data in _DEFAULT_ROLES:
                db.add(RoleModel(**data))
            db.commit()
        if db.query(PasswordPolicy).filter(PasswordPolicy.id == "default").first() is None:
            db.add(PasswordPolicy(id="default"))
            db.commit()
    finally:
        db.close()


def _bootstrap_first_admin() -> None:
    """Idempotent: promotes FIRST_ADMIN_EMAIL to the admin role if it exists
    and isn't already one. No-op if unset or already applied. See config.py
    for why this exists - nobody can promote the first admin via the API,
    since that endpoint itself requires being an admin already."""
    if not settings.FIRST_ADMIN_EMAIL:
        return
    db = SessionLocal()
    try:
        admin_role = db.query(RoleModel).filter(RoleModel.is_admin.is_(True)).first()
        if admin_role is None:
            return
        user = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
        if user and user.role_id != admin_role.id:
            user.role_id = admin_role.id
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_roles_and_policy()
    _bootstrap_first_admin()
    load_models()  # load YOLO weights once, not per-request
    yield


app = FastAPI(title="ANPR API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(detect.router)
app.include_router(admin.router)


@app.get("/health")
def liveness():
    """Unauthenticated, no system internals - just proves the process is up.
    Real metrics (CPU/RAM/disk/network) live at /admin/system-health, which
    is authenticated and audit-logged."""
    return {"status": "ok"}
