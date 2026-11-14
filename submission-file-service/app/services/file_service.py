import mimetypes
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings
from app.services.errors import ServiceError

BUILTIN_MIME = {
    ".pdf": {"application/pdf"}, ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"}, ".zip": {"application/zip", "application/x-zip-compressed"},
    ".png": {"image/png"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"},
}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


async def save_upload(upload: UploadFile) -> dict:
    settings = get_settings()
    original = (upload.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not original or original in {".", ".."} or "\x00" in original:
        raise ServiceError(400, "invalid_filename", "Nama berkas tidak valid")
    extension = Path(original).suffix.lower()
    if extension not in settings.extensions:
        raise ServiceError(415, "unsupported_file_type", "Format berkas tidak didukung")
    declared = (upload.content_type or "application/octet-stream").lower().split(";")[0].strip()
    accepted_mimes = settings.mime_types or BUILTIN_MIME.get(extension, set())
    if declared not in accepted_mimes:
        raise ServiceError(415, "unsupported_file_type", "MIME type berkas tidak sesuai")
    clean_stem = SAFE_NAME.sub("_", Path(original).stem).strip("._-")[:80] or "file"
    stored = f"{uuid4().hex}_{clean_stem}{extension}"
    root = settings.uploads_path
    destination = (root / stored).resolve()
    if destination.parent != root:
        raise ServiceError(400, "invalid_filename", "Nama berkas tidak valid")
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise ServiceError(413, "file_too_large", "Ukuran berkas melebihi batas")
                output.write(chunk)
        if size == 0:
            raise ServiceError(400, "empty_file", "Berkas tidak boleh kosong")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"original_filename": original, "stored_filename": stored,
            "file_path": str(destination), "file_type": declared, "file_size": size}
