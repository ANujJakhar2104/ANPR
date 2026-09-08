# ANPR Console

A backend + frontend around your existing YOLOv8 + SORT + PaddleOCR license-plate pipeline, with JWT authentication, password-policy enforcement, and audit logging on every action.

## What's actually yours vs. what's new

Your original detection logic is preserved and optimized:
- `backend/app/anpr/util.py` — Contains the core text extraction and cleaning logic. Recently upgraded with dynamic image scaling and Otsu's binarization to successfully strip "INDIA" holograms and "IND" watermarks from High-Security Registration Plates (HSRP).
- `backend/app/anpr/pipeline.py` — Your `main.py` frame loop (vehicle detect → plate detect → crop → dynamic scale → binarize → PaddleOCR), your `add_missing_data.py` interpolation, and your `visualize.py` rendering, each turned into a plain function so a route can call it per-request instead of running as a standalone script.
- `backend/app/anpr/sort/sort.py` — **Placeholder only.** Your `src/sort/sort.py` wasn't part of the upload. Drop your existing file in here before running video detection—see the comment at the top of that file.

Everything else (auth, users, audit logs, job queueing, the frontend) is new scaffolding around that logic.

## Architecture

frontend (Next.js)  ──JWT──>  backend (FastAPI)
├── /auth/register, /auth/login, /auth/me
├── /detect/image   (sync: detect on one frame)
├── /detect/video    (async: queues a job)
└── /detect/jobs/*   (poll status, download result)
SQLite: users, audit_logs, detection_jobs


- **Auth**: `passlib[bcrypt]` for hashing, `python-jose` for JWTs (HS256, 60 min expiry by default). Every protected route resolves the user from the `Authorization: Bearer <token>` header via `get_current_active_user`.
- **Password policy** (`app/security.py::validate_password_policy`): ≥10 characters, upper + lower + digit + special character, rejects a short list of common passwords, and rejects passwords containing the username or email. Enforced both in the Pydantic schema and again in the route. The frontend's register page mirrors these rules live as you type.
- **Audit logging** (`app/audit.py`, `app/models.py::AuditLog`): Every register/login (success *and* failure), every image/video detection request and outcome, every job status check, and every result download writes one row—who, what, when, from what IP, success or failure. It's a plain SQL table (`audit_logs`).
- **Video jobs are async** because a multi-minute clip shouldn't block an HTTP request. Upload returns a `job_id` immediately (`FastAPI BackgroundTasks` runs the pipeline); the frontend polls `/detect/jobs/{id}` until it's `completed` or `failed`, then downloads the annotated `.mp4`. Image detection stays synchronous since one frame is fast. 
- **Every job and file is scoped to its owner.** Jobs are looked up by `user_id == current_user.id`; a mismatch returns 404 (not 403) so an attacker can't even confirm another user's job ID exists.

## Running it locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# Install strictly matched Paddle versions to ensure Windows CPU compatibility
pip install paddlepaddle==2.6.2 paddleocr==2.8.1
pip install -r requirements.txt

cp .env.example .env
# edit .env: set SECRET_KEY (openssl rand -hex 32), model paths, etc.
# drop yolov8n.pt and license_plate_detector.pt into ./models/
# drop your existing src/sort/sort.py content into app/anpr/sort/sort.py

uvicorn app.main:app --reload
Docs at http://localhost:8000/docs.

Frontend

Bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
App at http://localhost:3000.

Or both at once with Docker Compose (from the repo root, after doing the .env and model-weight setup above):

Bash
docker compose up --build
