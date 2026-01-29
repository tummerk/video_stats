from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, BigInteger, DateTime, ForeignKey, Index
from src.models.base import BaseModel


class Metrics(BaseModel):
    """Video metrics model for tracking engagement over time."""

    __tablename__ = "metrics"

    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id"), nullable=False
    )
    view_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    save_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    video: Mapped["Video"] = relationship(
        "Video", back_populates="metrics"
    )

    # Indexes
    __table_args__ = (
        Index("video_measured_idx", "video_id", "measured_at"),
    )

    def __repr__(self) -> str:
        return f"<Metrics(id={self.id}, video_id={self.video_id}, measured_at={self.measured_at})>"
