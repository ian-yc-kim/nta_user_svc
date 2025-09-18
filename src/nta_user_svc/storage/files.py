import io
import os
import uuid
import logging
from pathlib import Path
from typing import Union

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

import nta_user_svc.config as config

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_PIL_FORMAT_MAP = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


def _ensure_base_dir() -> Path:
    try:
        base = Path(config.PROFILE_PHOTO_DIR).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def save_profile_photo(file_stream: UploadFile, user_id: int) -> str:
    """
    Save an uploaded profile photo and return its relative path ("{user_id}/{uuid}.{ext}").
    Performs extension, MIME and content verification and enforces size limit.
    """
    try:
        if file_stream is None:
            raise ValueError("no file provided")

        # Validate filename and extension
        filename = getattr(file_stream, "filename", None)
        if not filename:
            raise ValueError("uploaded file must have a filename")

        ext = Path(filename).suffix.lower()
        if ext == ".jpeg":
            ext = ".jpg"

        if ext not in _ALLOWED_EXTENSIONS:
            raise ValueError(f"unsupported file extension: {ext}")

        # Validate content type
        content_type = getattr(file_stream, "content_type", "")
        if content_type not in _ALLOWED_MIME:
            raise ValueError(f"unsupported content type: {content_type}")

        # Read at most MAX + 1 bytes to detect oversize
        max_bytes = int(config.MAX_PHOTO_SIZE_BYTES)
        file_obj = getattr(file_stream, "file", None)
        if file_obj is None:
            raise ValueError("uploaded file object is missing")

        # Ensure we read from start
        try:
            file_obj.seek(0)
        except Exception:
            pass

        data = file_obj.read(max_bytes + 1)
        if len(data) == 0:
            raise ValueError("empty file")
        if len(data) > max_bytes:
            raise ValueError("file too large")

        # Verify image via PIL
        try:
            img = Image.open(io.BytesIO(data))
            img_format = img.format
            img.verify()  # verify integrity
        except UnidentifiedImageError as e:
            logger.error(e, exc_info=True)
            raise ValueError("invalid image content")
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ValueError("invalid image content")

        # Map PIL format to extension and compare
        expected_ext = _PIL_FORMAT_MAP.get(img_format)
        if not expected_ext:
            raise ValueError("unsupported image format")

        if expected_ext != ext:
            # allow jpg/jpeg interchange: we normalized .jpeg -> .jpg above
            raise ValueError("image format mismatch")

        # All validations passed. Prepare destination
        base = _ensure_base_dir()
        try:
            user_dir = base / str(int(user_id))
        except Exception:
            raise ValueError("invalid user_id")

        # create user directory with restrictive permissions where possible
        try:
            user_dir.mkdir(parents=True, exist_ok=True)
            try:
                user_dir.chmod(0o700)
            except Exception:
                # Not fatal when chmod fails (e.g., on Windows)
                pass
        except Exception as e:
            logger.error(e, exc_info=True)
            raise OSError("failed to create user directory")

        unique_name = f"{uuid.uuid4().hex}{ext}"
        relative_path = f"{user_dir.name}/{unique_name}"
        dest_path = (user_dir / unique_name).resolve()

        # Ensure dest_path is under base to prevent traversal
        try:
            dest_path.relative_to(base)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ValueError("invalid destination path")

        # Write atomically using a temp file
        try:
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            with open(tmp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, dest_path)
        except Exception as e:
            logger.error(e, exc_info=True)
            # Attempt cleanup
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise OSError("failed to write file to disk")

        return relative_path
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def get_full_file_path(relative_filepath: str) -> Path:
    """
    Convert a relative filepath (as stored) into an absolute Path under PROFILE_PHOTO_DIR.
    Prevents directory traversal by resolving and ensuring the path is a child of base.
    """
    try:
        if not relative_filepath or not isinstance(relative_filepath, str):
            raise ValueError("relative_filepath must be a non-empty string")

        base = Path(config.PROFILE_PHOTO_DIR).expanduser().resolve()
        candidate = (base / relative_filepath).resolve()
        try:
            candidate.relative_to(base)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ValueError("invalid relative path")
        return candidate
    except Exception as e:
        logger.error(e, exc_info=True)
        raise


def remove_file(relative_filepath: str) -> None:
    """
    Remove a stored file given its relative filepath.
    """
    try:
        full_path = get_full_file_path(relative_filepath)
        try:
            full_path.unlink()
        except FileNotFoundError:
            # Already gone: not an error
            return
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
