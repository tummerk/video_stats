from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer
from src.models.base import BaseModel


class Account(BaseModel):
    """Instagram account model."""

    __tablename__ = "accounts"

    # Override id to store Instagram user_pk manually
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    profile_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    videos: Mapped[List["Video"]] = relationship(
        "Video", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, username='{self.username}')>"
