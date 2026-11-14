import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, Header, Request, UploadFile

from app.database.connection import connect
from app.middleware.request_id import get_request_id
from app.services.assignment_service import ensure_assignment_exists
from app.services.auth_service import authenticate
from app.services.errors import ServiceError
from app.services.file_service import save_upload
from app.services.notification_service import notify_submission
from app.models.submission import Submission
from app.utils.response import success

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_submissions(request: Request, assignment_id: str, authorization: str | None = Header(default=None)):
    user = await authenticate(authorization, get_request_id(request))
    del user  # Authorization is required; assignment-level access policy belongs to the agreed Auth/Assignment contract.
    if not assignment_id.strip():
        raise ServiceError(400, "invalid_assignment_id", "assignment_id wajib diisi")
    with connect() as db:
        rows = db.execute("SELECT * FROM submission WHERE assignment_id=? ORDER BY created_at DESC", (assignment_id,)).fetchall()
    return success(request, {"items": [Submission.from_row(row).public_dict() for row in rows], "count": len(rows)})


@router.post("")
async def create_submission(request: Request, assignment_id: str = Form(...), file: UploadFile = File(...),
                            authorization: str | None = Header(default=None)):
    request_id = get_request_id(request)
    user = await authenticate(authorization, request_id)
    if not assignment_id.strip():
        raise ServiceError(400, "invalid_assignment_id", "assignment_id wajib diisi")
    await ensure_assignment_exists(assignment_id, request_id)
    saved = await save_upload(file)
    now = datetime.now(timezone.utc).isoformat()
    submission = Submission(id=str(uuid4()), assignment_id=assignment_id, user_id=user["id"],
                            file_id=str(uuid4()), **saved, status="submitted", created_at=now, updated_at=now)
    try:
        with connect() as db:
            db.execute("""INSERT INTO submission VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       tuple(vars(submission).values()))
    except sqlite3.Error as exc:
        Path(saved["file_path"]).unlink(missing_ok=True)
        logger.exception("Could not persist submission metadata request_id=%s", request_id)
        raise ServiceError(500, "storage_error", "Submission gagal disimpan") from exc
    await notify_submission({"submission_id": submission.id, "assignment_id": assignment_id,
                             "user_id": user["id"], "file_id": submission.file_id}, request_id)
    return success(request, {"submission": submission.public_dict()}, 201)


@router.delete("/{submission_id}")
async def delete_submission(submission_id: str, request: Request,
                            authorization: str | None = Header(default=None)):
    await authenticate(authorization, get_request_id(request))
    with connect() as db:
        row = db.execute("SELECT * FROM submission WHERE id=?", (submission_id,)).fetchone()
        if row is None:
            raise ServiceError(404, "submission_not_found", "Submission tidak ditemukan")
        file_path = Path(row["file_path"]).resolve()
        upload_root = Path(__import__("app.config", fromlist=["get_settings"]).get_settings().uploads_path)
        if file_path.parent != upload_root:
            logger.error("Stored file path escaped upload directory submission_id=%s", submission_id)
            raise ServiceError(500, "storage_error", "Lokasi berkas tidak valid")
        db.execute("DELETE FROM submission WHERE id=?", (submission_id,))
    try:
        file_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.exception("Metadata deleted but file cleanup failed submission_id=%s", submission_id)
        raise ServiceError(500, "file_cleanup_failed", "Metadata terhapus, tetapi berkas gagal dibersihkan") from exc
    return success(request, {"id": submission_id, "deleted": True})
