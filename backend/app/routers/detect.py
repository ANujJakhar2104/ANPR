import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.anpr import pipeline
from app.audit import log_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.dependencies import get_current_active_user, require_video
from app.export import export_response
from app.models import AuditAction, Detection, DetectionJob, DetectionSource, JobStatus, User
from app.schemas import DetectionRecordOut, ImageDetectionResponse, JobOut, Page

router = APIRouter(prefix="/detect", tags=["detect"])

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}


def _save_upload(upload: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(upload.filename or "")[1].lower()
    dest_path = os.path.join(dest_dir, f"{uuid.uuid4()}{ext}")
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest_path


def _persist_detections(db: Session, user_id: str, source: DetectionSource,
                         detections: list[dict], job_id: Optional[str] = None) -> None:
    for d in detections:
        db.add(Detection(
            user_id=user_id,
            job_id=job_id,
            source=source,
            car_id=str(d["car_id"]),
            car_bbox=json.dumps(d.get("car_bbox")),
            license_plate_bbox=json.dumps(d.get("license_plate_bbox")),
            license_plate_bbox_score=str(d.get("license_plate_bbox_score")),
            license_number=d.get("license_number"),
            license_number_score=str(d["license_number_score"]) if d.get("license_number_score") is not None else None,
            raw_ocr_text=d.get("raw_ocr_text"),
            char_analysis=json.dumps(d["char_analysis"]) if d.get("char_analysis") else None,
        ))


@router.post("/image", response_model=ImageDetectionResponse)
def detect_image(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Available to every role (basic and up) - RBAC only gates video."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"Unsupported image type '{ext}'. Allowed: {sorted(ALLOWED_IMAGE_EXT)}")

    log_audit(db, AuditAction.DETECTION_IMAGE_REQUEST, user=current_user,
               detail=file.filename, request=request)
    db.commit()

    saved_path = _save_upload(file, os.path.join(settings.UPLOAD_DIR, current_user.id))

    try:
        detections, annotated_b64 = pipeline.detect_image(saved_path)
    except Exception as exc:
        log_audit(db, AuditAction.DETECTION_IMAGE_FAILURE, status="failure",
                   user=current_user, detail=str(exc), request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail="Detection failed") from exc

    _persist_detections(db, current_user.id, DetectionSource.IMAGE, detections)
    log_audit(db, AuditAction.DETECTION_IMAGE_SUCCESS, user=current_user,
               detail=f"{len(detections)} plate(s) matched", request=request)
    db.commit()

    return ImageDetectionResponse(detections=detections, annotated_image_base64=annotated_b64)


def _process_video_job(job_id: str, video_path: str, work_dir: str, user_id: str, username: str) -> None:
    """Runs in a background thread - owns its own DB session."""
    db = SessionLocal()
    try:
        job = db.query(DetectionJob).filter(DetectionJob.id == job_id).first()
        if job is None:
            return
        job.status = JobStatus.PROCESSING
        db.commit()

        try:
            artifacts = pipeline.run_full_video_pipeline(video_path, work_dir)
            job.csv_path = artifacts["csv_path"]
            job.interpolated_csv_path = artifacts["interpolated_csv_path"]
            job.output_video_path = artifacts["output_video_path"]
            job.status = JobStatus.COMPLETED
            _persist_detections(db, user_id, DetectionSource.VIDEO, artifacts["detections"], job_id=job_id)
            log_audit(db, AuditAction.DETECTION_VIDEO_SUCCESS, username=username,
                       detail=f"job {job_id} completed, {len(artifacts['detections'])} vehicle(s)")
        except Exception as exc:  # noqa: BLE001 - persist any failure onto the job row
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            log_audit(db, AuditAction.DETECTION_VIDEO_FAILURE, status="failure",
                       username=username, detail=f"job {job_id}: {exc}")

        db.commit()
    finally:
        db.close()


@router.post("/video", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def detect_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    current_user: User = Depends(require_video),
    db: Session = Depends(get_db),
):
    """Requires the can_use_video capability - see require_video in dependencies.py."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"Unsupported video type '{ext}'. Allowed: {sorted(ALLOWED_VIDEO_EXT)}")

    saved_path = _save_upload(file, os.path.join(settings.UPLOAD_DIR, current_user.id))

    job = DetectionJob(
        user_id=current_user.id,
        status=JobStatus.PENDING,
        input_filename=file.filename or os.path.basename(saved_path),
    )
    db.add(job)
    db.flush()

    log_audit(db, AuditAction.DETECTION_VIDEO_REQUEST, user=current_user,
               detail=f"job {job.id}: {file.filename}", request=request)
    db.commit()
    db.refresh(job)

    work_dir = os.path.join(settings.OUTPUT_DIR, current_user.id, job.id)
    background_tasks.add_task(_process_video_job, job.id, saved_path, work_dir, current_user.id, current_user.username)

    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return (
        db.query(DetectionJob)
        .filter(DetectionJob.user_id == current_user.id)
        .order_by(DetectionJob.created_at.desc())
        .all()
    )


def _get_owned_job(job_id: str, current_user: User, db: Session) -> DetectionJob:
    job = db.query(DetectionJob).filter(DetectionJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != current_user.id and not current_user.role.is_admin:
        # 404, not 403 - don't confirm the job exists to a non-owner
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    log_audit(db, AuditAction.JOB_STATUS_CHECK, user=current_user, detail=job_id, request=request)
    db.commit()
    return job


@router.get("/jobs/{job_id}/download")
def download_result(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    if job.status != JobStatus.COMPLETED or not job.output_video_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not completed yet")

    log_audit(db, AuditAction.RESULT_DOWNLOAD, user=current_user, detail=job_id, request=request)
    db.commit()

    return FileResponse(job.output_video_path, media_type="video/mp4",
                         filename=f"{job.input_filename}_annotated.mp4")


# --- recent detections: filter, paginate, export, drill into char analysis --

def _apply_detection_filters(
    query, current_user: User,
    source: Optional[str], plate: Optional[str],
    date_from: Optional[datetime], date_to: Optional[datetime],
    user_id: Optional[str],
):
    # Non-admins only ever see their own rows, regardless of what they pass.
    if current_user.role.is_admin and user_id:
        query = query.filter(Detection.user_id == user_id)
    elif not current_user.role.is_admin:
        query = query.filter(Detection.user_id == current_user.id)

    if source:
        query = query.filter(Detection.source == source)
    if plate:
        like = f"%{plate.upper()}%"
        query = query.filter(or_(Detection.license_number.ilike(like), Detection.raw_ocr_text.ilike(like)))
    if date_from:
        query = query.filter(Detection.created_at >= date_from)
    if date_to:
        query = query.filter(Detection.created_at <= date_to)
    return query


def _detection_to_dict(d: Detection) -> dict:
    return {
        "id": d.id,
        "user_id": d.user_id,
        "job_id": d.job_id,
        "source": d.source.value if hasattr(d.source, "value") else d.source,
        "car_id": d.car_id,
        "license_number": d.license_number,
        "license_number_score": d.license_number_score,
        "raw_ocr_text": d.raw_ocr_text,
        "char_analysis": json.loads(d.char_analysis) if d.char_analysis else None,
        "created_at": d.created_at,
    }


@router.get("/detections", response_model=Page[DetectionRecordOut])
def list_detections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    source: Optional[str] = Query(None, description="image | video"),
    plate: Optional[str] = Query(None, description="substring match on plate text"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user_id: Optional[str] = Query(None, description="admin only - filter to one user"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    query = _apply_detection_filters(db.query(Detection), current_user, source, plate, date_from, date_to, user_id)
    total = query.count()
    rows = (
        query.order_by(Detection.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(items=[_detection_to_dict(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/detections/{detection_id}", response_model=DetectionRecordOut)
def get_detection(
    detection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    row = db.query(Detection).filter(Detection.id == detection_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    if row.user_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return _detection_to_dict(row)


DETECTION_EXPORT_COLUMNS = [
    ("created_at", "Timestamp"),
    ("source", "Source"),
    ("car_id", "Car ID"),
    ("license_number", "Plate"),
    ("license_number_score", "Confidence"),
    ("raw_ocr_text", "Raw OCR"),
    ("user_id", "User ID"),
]


@router.get("/detections/export/{format}")
def export_detections(
    format: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    plate: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user_id: Optional[str] = None,
):
    if format not in ("csv", "html", "pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be csv, html, or pdf")

    query = _apply_detection_filters(db.query(Detection), current_user, source, plate, date_from, date_to, user_id)
    rows = [_detection_to_dict(r) for r in query.order_by(Detection.created_at.desc()).limit(5000).all()]

    log_audit(db, AuditAction.DETECTIONS_EXPORT, user=current_user,
               detail=f"format={format} rows={len(rows)}", request=request)
    db.commit()

    return export_response(format, "Recent Detections", "detections", DETECTION_EXPORT_COLUMNS, rows)
