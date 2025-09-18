import os
import logging
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
SERVICE_PORT = os.getenv("SERVICE_PORT", 8000)

try:
    PASSWORD_HASH_ROUNDS = int(os.getenv("PASSWORD_HASH_ROUNDS", 12))
except (TypeError, ValueError) as e:
    # Log the error and fall back to default rounds
    logging.error("Invalid PASSWORD_HASH_ROUNDS value, falling back to 12", exc_info=True)
    PASSWORD_HASH_ROUNDS = 12

# JWT configuration: load from environment and fail fast if secret not present
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

try:
    JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", 24))
except (TypeError, ValueError) as e:
    logging.error("Invalid JWT_EXP_HOURS value, falling back to 24", exc_info=True)
    JWT_EXP_HOURS = 24

# File storage configuration
# Default to a secure location outside the web root
_PROFILE_PHOTO_DIR_DEFAULT = os.getenv("PROFILE_PHOTO_DIR", "/var/lib/nta_user_svc_uploads")
try:
    # Normalize and store as absolute path string
    PROFILE_PHOTO_DIR = os.path.abspath(os.path.expanduser(_PROFILE_PHOTO_DIR_DEFAULT))
except Exception as e:
    logging.error("Failed to resolve PROFILE_PHOTO_DIR, falling back to /tmp/nta_user_svc_uploads", exc_info=True)
    PROFILE_PHOTO_DIR = os.path.abspath(os.path.expanduser("/tmp/nta_user_svc_uploads"))

try:
    MAX_PHOTO_SIZE_BYTES = int(os.getenv("MAX_PHOTO_SIZE_BYTES", 1048576))
except (TypeError, ValueError) as e:
    logging.error("Invalid MAX_PHOTO_SIZE_BYTES value, falling back to 1048576", exc_info=True)
    MAX_PHOTO_SIZE_BYTES = 1048576
