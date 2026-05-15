from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_ROOT = Path("storage/uploads")
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    stored_filename: str
    stored_path: str
    content_type: str | None
    size_bytes: int


def validate_upload_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Недопустимый тип файла. Разрешены: {allowed}.")
    return suffix


def validate_upload_size(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValueError("Файл пустой.")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("Файл больше 10 МБ.")


def is_image_upload(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def public_upload_name(original_filename: str) -> str:
    return Path(original_filename).name.replace("\x00", "").strip() or "file"


async def save_upload_file(upload: UploadFile, folder: str) -> StoredUpload:
    original_filename = public_upload_name(upload.filename or "")
    suffix = validate_upload_filename(original_filename)
    stored_filename = f"{uuid4().hex}{suffix}"
    target_dir = UPLOAD_ROOT / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / stored_filename

    size = 0
    with target_path.open("wb") as file:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE_BYTES:
                file.close()
                target_path.unlink(missing_ok=True)
                raise ValueError("Файл больше 10 МБ.")
            file.write(chunk)

    validate_upload_size(size)
    return StoredUpload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        stored_path=str(target_path),
        content_type=upload.content_type,
        size_bytes=size,
    )
