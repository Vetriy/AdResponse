import pytest

from app.models import AdvertisingReport
from app.services.uploads import is_image_upload, validate_upload_filename, validate_upload_size


def test_upload_filename_validation_allows_only_safe_extensions() -> None:
    assert validate_upload_filename("report.pdf") == ".pdf"
    assert validate_upload_filename("photo.webp") == ".webp"
    assert is_image_upload("photo.jpg") is True
    assert is_image_upload("report.xlsx") is False

    with pytest.raises(ValueError):
        validate_upload_filename("script.exe")


def test_upload_size_validation_rejects_empty_and_large_files() -> None:
    validate_upload_size(1024)

    with pytest.raises(ValueError):
        validate_upload_size(0)

    with pytest.raises(ValueError):
        validate_upload_size(11 * 1024 * 1024)


def test_advertising_report_model_keeps_file_metadata() -> None:
    report = AdvertisingReport(
        client_user_id=1,
        appeal_id=None,
        uploaded_by_user_id=2,
        title="Отчет за апрель",
        description="Краткая сводка по рекламе",
        original_filename="april.pdf",
        stored_filename="safe.pdf",
        stored_path="storage/uploads/reports/safe.pdf",
        content_type="application/pdf",
        size_bytes=2048,
    )

    assert report.title == "Отчет за апрель"
    assert report.original_filename == "april.pdf"
    assert report.size_bytes == 2048
