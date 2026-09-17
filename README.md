# ANPR Console

A backend + frontend around your existing YOLOv8 + SORT + EasyOCR license-plate
pipeline, with JWT authentication, usage-tiered RBAC, password-policy
enforcement, per-character OCR analysis, an admin dashboard with live system
health, and CSV/HTML/PDF export on both the audit log and detection history.

## What's actually yours vs. what's new

Your original detection logic is preserved as-is:
- `backend/app/anpr/util.py` — the exact character-mapping tables, format
  validation, and `get_car()` matching logic from your `util.py`.
- `backend/app/anpr/pipeline.py` — your `main.py` frame loop (vehicle detect
  → plate detect → crop → grayscale → threshold → OCR), your
  `add_missing_data.py` interpolation, and your `visualize.py` rendering,
  each turned into a plain function so a route can call it per-request
  instead of it running as a standalone script.
- `backend/app/anpr/sort/sort.py` — **placeholder only.** Your `src/sort/sort.py`
  wasn't part of what you uploaded, so it couldn't be reproduced exactly.
  Drop your existing file in here before running video detection — see the
  comment at the top of that file.

Everything else (auth, RBAC, users, audit logs, detection history, admin
dashboard, the frontend) is new scaffolding around that logic.

## Architecture

```
frontend (Next.js)  ──JWT──>  backend (FastAPI)
                                 ├── /auth/register, /auth/login, /auth/me
                                 ├── /detect/image        (sync, any role)
                                 ├── /detect/video         (async job, PRO+ only)
                                 ├── /detect/detections/*  (history: filter, paginate, export)
                                 ├── /detect/jobs/*        (poll status, download result)
                                 └── /admin/*              (ADMIN only - see below)
                               SQLite: users, audit_logs, detection_jobs, detections
```

- **Auth**: `passlib[bcrypt]` for hashing (pinned to `bcrypt==4.0.1` - see the
  note below on why), `python-jose` for JWTs (HS256, 60 min expiry by
  default).
- **RBAC is usage-tiered, ranked, not just admin/not-admin** (`app/models.py::Role`,
  `ROLE_RANK`): `basic` gets photo detection only, `pro` unlocks video too,
  `admin` sits above both and additionally unlocks the whole `/admin/*`
  surface. `require_role(minimum)` in `dependencies.py` does a ranked
  comparison, so `admin` automatically satisfies any lower requirement
  without needing to be listed everywhere. New registrations default to
  `basic`. **Bootstrapping your first admin**: register normally, set
  `FIRST_ADMIN_EMAIL` in `.env` to that account's email, restart the
  backend once - it force-promotes that user on startup (idempotent, safe
  to leave set permanently). After that, promote everyone else from
  Admin → Users in the frontend.
- **Password policy** (`app/security.py::validate_password_policy`): ≥10
  characters, upper + lower + digit + special character, rejects a short
  list of common passwords, and rejects passwords containing the username
  or email.
- **Audit logging** (`app/audit.py`, `AuditLog` model): every register,
  login (success/failure), role check that got denied, detection
  request/outcome, job check, download, export, and role change writes a
  row - who, what, when, from what IP, success or failure. Viewable and
  exportable (CSV/HTML/PDF) from Admin → Audit log.
- **Detection history** (`Detection` model): every plate match - from a
  photo upload or a completed video job - gets persisted, not just
  returned once and forgotten. Video jobs persist one row per unique
  vehicle (its highest-confidence reading), not one row per frame.
  Filterable by source/plate-text/date, paginated, exportable, and each row
  can be expanded into a **character-by-character breakdown**
  (`anpr/util.py::analyze_characters`): for each of the plate's 10
  positions, what EasyOCR actually read vs. what your format-correction
  logic corrected it to, and whether that position expected a letter or a
  digit. Only meaningful when the raw OCR text was exactly 10 characters,
  since that's the shape your existing `format_license()` operates on -
  otherwise you still see the raw OCR guess, just without a position
  breakdown.
- **Admin dashboard** (`/admin`, ADMIN only): an Overview tab with
  user/detection/job counts plus **live system health** - CPU, RAM,
  storage, and per-network-interface throughput via `psutil`, polling
  every 5s; an Audit log tab (filter, paginate, export); and a Users tab to
  change anyone's role.
- **Video jobs are async** because a multi-minute clip shouldn't block an
  HTTP request - see the "known gaps" section below for the durability
  caveat that comes with that choice.
- **Every job, detection, and (for non-admins) export is scoped to its
  owner.** Non-admins can only ever see or export their own rows,
  regardless of what filters they pass - enforced server-side in
  `_apply_detection_filters`, not just hidden in the UI.

## Running it locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set SECRET_KEY (openssl rand -hex 32), model paths, etc.
# drop yolov8n.pt and license_plate_detector.pt into ./models/
# drop your existing src/sort/sort.py content into app/anpr/sort/sort.py
uvicorn app.main:app --reload
```
Docs at `http://localhost:8000/docs`.

**Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
App at `http://localhost:3000`.

**Or both at once with Docker Compose** (from the repo root, after doing the
`.env` and model-weight setup above):
```bash
docker compose up --build
```

## If you're upgrading from an earlier copy of this project

The data model changed (`User.is_admin` became `User.role`, plus a new
`detections` table) and `create_all` only adds missing tables - it doesn't
alter existing ones. **Delete `backend/data/anpr.db` and restart** so it
regenerates with the new schema. There's no migration path here since this
is dev-stage without Alembic; if you need to preserve real data before a
schema change like this in the future, that's the moment to introduce
Alembic migrations instead of relying on `create_all`.

## Known gaps to close before production

- Access tokens only, no refresh flow — sessions end when the 60-minute
  token expires and the person has to log in again.
- JWT lives in `localStorage` on the frontend for simplicity; an httpOnly
  cookie set by the backend would keep it out of reach of any injected JS.
- No rate limiting on `/auth/login` — add one (e.g. `slowapi`) before this
  is public, so it isn't a brute-force target.
- SQLite is fine for one instance; move `DATABASE_URL` to Postgres for
  concurrent writers, and at that point introduce Alembic for schema changes.
- `BackgroundTasks` runs in-process — if the server restarts mid-job, that
  job (and now, its detections) is lost, stuck at `processing`. Celery +
  Redis (or any durable queue) fixes that.
- Exports cap at 5,000 rows (`app/routers/detect.py` /
  `app/routers/admin.py`) to keep the synchronous PDF/HTML render fast -
  raise the cap or move export to a background job if you need more.
