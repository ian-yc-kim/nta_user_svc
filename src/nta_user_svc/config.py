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
