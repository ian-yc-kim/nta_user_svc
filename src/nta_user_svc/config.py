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
