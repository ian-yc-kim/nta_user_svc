from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from .base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    bio = Column(String(1000), nullable=True)
    hobby = Column(String(255), nullable=True)
    occupation = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    profile_photo_path = Column(String(1024), nullable=True)

    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # Back-populate relationship to User
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, user_id={self.user_id})>"
