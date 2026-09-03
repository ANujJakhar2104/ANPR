# ANPR Console

A backend + frontend around your existing YOLOv8 + SORT + EasyOCR license-plate
pipeline, with JWT authentication, password-policy enforcement, and audit
logging on every action.

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

Everything else (auth, users, audit logs, job queueing, the frontend) is new
scaffolding around that logic.

## Architecture

```
frontend (Next.js)  ──JWT──>  backend (FastAPI)
                                 ├── /auth/register, /auth/login, /auth/me
                                 ├── /detect/image   (sync: detect on one frame)
                                 ├── /detect/video    (async: queues a job)
                                 └── /detect/jobs/*   (poll status, download result)
                               SQLite: users, audit_logs, detection_jobs
```

- **Auth**: `passlib[bcrypt]` for hashing, `python-jose` for JWTs (HS256,
  60 min expiry by default). Every protected route resolves the user from
  the `Authorization: Bearer <token>` header via `get_current_active_user`.
- **Password policy** (`app/security.py::validate_password_policy`): ≥10
  characters, upper + lower + digit + special character, rejects a short
  list of common passwords, and rejects passwords containing the username
  or email. Enforced both in the Pydantic schema (fast client-side-style
  feedback) and again in the route (so it can check against the specific
  user's email/username). The frontend's register page mirrors these rules
  live as you type.
- **Audit logging** (`app/audit.py`, `app/models.py::AuditLog`): every
  register/login (success *and* failure), every image/video detection
  request and outcome, every job status check, and every result download
  writes one row — who, what, when, from what IP, success or failure. It's
  a plain SQL table (`audit_logs`), so you can query it directly or expose
  an admin endpoint over it later.
- **Video jobs are async** because a multi-minute clip shouldn't block an
  HTTP request. Upload returns a `job_id` immediately (`FastAPI
  BackgroundTasks` runs the pipeline); the frontend polls
  `/detect/jobs/{id}` until it's `completed` or `failed`, then downloads
  the annotated `.mp4`. Image detection stays synchronous since one frame
  is fast. If you outgrow `BackgroundTasks` (e.g. need retries or multiple
  worker processes), swap it for Celery + Redis — you're already using that
  combination elsewhere, and only `_process_video_job` in
  `routers/detect.py` would need to move into a Celery task.
- **Every job and file is scoped to its owner.** Jobs are looked up by
  `user_id == current_user.id`; a mismatch returns 404 (not 403) so an
  attacker can't even confirm another user's job ID exists.

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

## Known gaps to close before production

- Access tokens only, no refresh flow — sessions end when the 60-minute
  token expires and the person has to log in again.
- JWT lives in `localStorage` on the frontend for simplicity; an httpOnly
  cookie set by the backend would keep it out of reach of any injected JS.
- No rate limiting on `/auth/login` — add one (e.g. `slowapi`) before this
  is public, so it isn't a brute-force target.
- SQLite is fine for one instance; move `DATABASE_URL` to Postgres for
  concurrent writers.
- `BackgroundTasks` runs in-process — if the server restarts mid-job, that
  job is lost (stuck at `processing`). Celery + Redis (or any durable
  queue) fixes that.
