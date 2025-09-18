from .base import Base
from ..database import get_db

# Import models so that Alembic's target_metadata picks them up and so
# application imports can do: from nta_user_svc.models import User, Profile
from .user import User
from .profile import Profile

__all__ = ["Base", "get_db", "User", "Profile"]
