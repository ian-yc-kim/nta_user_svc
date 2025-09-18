import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

users_router = APIRouter()

# Note: registration endpoint has been moved to auth_router (/api/auth/register).
# Keep this router available for other user-related endpoints.
