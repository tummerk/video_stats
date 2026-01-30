from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime
from src.models.base import BaseModel


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat tracking for monitoring worker status."""

    __tablename__ = "worker_heartbeat"

    worker_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )  # running, stopped, error
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<WorkerHeartbeat(id={self.id}, worker_name='{self.worker_name}', status='{self.status}')>"
