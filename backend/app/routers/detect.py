import os
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.anpr import pipeline
from app.audit import log_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.dependencies import get_current_active_user
from app.models import AuditAction, DetectionJob, JobStatus, User
from app.schemas import ImageDetectionResponse, JobOut

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


@router.post("/image", response_model=ImageDetectionResponse)
def detect_image(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
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

    log_audit(db, AuditAction.DETECTION_IMAGE_SUCCESS, user=current_user,
               detail=f"{len(detections)} plate(s) matched", request=request)
    db.commit()

    return ImageDetectionResponse(detections=detections, annotated_image_base64=annotated_b64)


# runs in background thread, so it can take a long time without blocking the request/response cycle

def _process_video_job(job_id: str, video_path: str, work_dir: str, username: str) -> None:

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
            log_audit(db, AuditAction.DETECTION_VIDEO_SUCCESS, username=username,
                       detail=f"job {job_id} completed")
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
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
    background_tasks.add_task(_process_video_job, job.id, saved_path, work_dir, current_user.username)

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
    if job.user_id != current_user.id and not current_user.is_admin:
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
