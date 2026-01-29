from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Index
from src.models.base import BaseModel


class MetricSchedule(BaseModel):
    """Schedule for automatic metrics collection."""

    __tablename__ = "metric_schedules"

    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id"), nullable=False
    )
    schedule_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # '60min', '3h', '24h', '48h', '72h', 'daily'
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, completed, failed
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    video: Mapped["Video"] = relationship(
        "Video", back_populates="metric_schedules"
    )

    # Indexes
    __table_args__ = (
        Index("video_schedule_idx", "video_id", "scheduled_at"),
        Index("status_scheduled_idx", "status", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<MetricSchedule(id={self.id}, video_id={self.video_id}, "
            f"type='{self.schedule_type}', status='{self.status}')>"
        )
