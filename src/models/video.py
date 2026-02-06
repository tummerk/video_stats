from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index, BigInteger
from src.models.base import BaseModel


class Video(BaseModel):
    """Instagram video/reel model."""

    __tablename__ = "videos"

    video_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    shortcode: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    audio_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    transcription: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key (use BigInteger to match Account.id)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts.id"), nullable=False)

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account", back_populates="videos"
    )
    metrics: Mapped[List["Metrics"]] = relationship(
        "Metrics", back_populates="video", cascade="all, delete-orphan"
    )
    metric_schedules: Mapped[List["MetricSchedule"]] = relationship(
        "MetricSchedule", back_populates="video", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("account_published_idx", "account_id", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, shortcode='{self.shortcode}', account_id={self.account_id})>"
