import io
import os
import pytest
from pathlib import Path
from PIL import Image

import nta_user_svc.config as config
from nta_user_svc.storage.files import save_profile_photo, remove_file, get_full_file_path


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(data)


def make_image_bytes(fmt: str = "JPEG", size=(10, 10), color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", size, color)
    bio = io.BytesIO()
    img.save(bio, format=fmt)
    return bio.getvalue()


def test_save_profile_photo_accepts_valid_images(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    user_id = 1
    for fmt, filename, content_type in [("JPEG", "photo.jpg", "image/jpeg"), ("PNG", "photo.png", "image/png"), ("WEBP", "photo.webp", "image/webp")]:
        data = make_image_bytes(fmt=fmt)
        upload = DummyUploadFile(filename=filename, content_type=content_type, data=data)
        relative = save_profile_photo(upload, user_id)
        assert relative.startswith(f"{user_id}/")
        full = get_full_file_path(relative)
        assert full.exists()
        # cleanup
        remove_file(relative)


def test_save_profile_photo_rejects_oversize(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 10)  # very small

    data = make_image_bytes(fmt="JPEG")
    upload = DummyUploadFile(filename="big.jpg", content_type="image/jpeg", data=data)
    with pytest.raises(ValueError):
        save_profile_photo(upload, 2)


def test_save_profile_photo_rejects_invalid_file_format(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    # Create a text file but name it .jpg and claim image/jpeg
    data = b"this is not an image"
    upload = DummyUploadFile(filename="evil.jpg", content_type="image/jpeg", data=data)
    with pytest.raises(ValueError):
        save_profile_photo(upload, 3)


def test_save_profile_photo_unique_filenames(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    data = make_image_bytes(fmt="JPEG")
    upload1 = DummyUploadFile(filename="a.jpg", content_type="image/jpeg", data=data)
    upload2 = DummyUploadFile(filename="a.jpg", content_type="image/jpeg", data=data)
    r1 = save_profile_photo(upload1, 4)
    r2 = save_profile_photo(upload2, 4)
    assert r1 != r2
    remove_file(r1)
    remove_file(r2)


def test_files_stored_in_user_subdirectory(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    data = make_image_bytes(fmt="PNG")
    upload = DummyUploadFile(filename="x.png", content_type="image/png", data=data)
    relative = save_profile_photo(upload, 42)
    assert relative.startswith("42/")
    full = get_full_file_path(relative)
    assert full.exists()
    assert full.parent == (Path(str(tmp_path)) / "42")
    remove_file(relative)


def test_remove_file_deletes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    monkeypatch.setattr(config, "MAX_PHOTO_SIZE_BYTES", 200000)

    data = make_image_bytes(fmt="PNG")
    upload = DummyUploadFile(filename="r.png", content_type="image/png", data=data)
    relative = save_profile_photo(upload, 99)
    full = get_full_file_path(relative)
    assert full.exists()
    remove_file(relative)
    assert not full.exists()


def test_get_full_file_path_prevents_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))

    with pytest.raises(ValueError):
        get_full_file_path("../etc/passwd")
    with pytest.raises(ValueError):
        get_full_file_path("42/../../evil.jpg")


def test_get_full_file_path_invalid_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE_PHOTO_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        get_full_file_path(123)  # not a string
    with pytest.raises(ValueError):
        get_full_file_path("")
