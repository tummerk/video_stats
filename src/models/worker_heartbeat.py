from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer
from src.models.base import BaseModel


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat status tracking."""

    __tablename__ = "worker_heartbeats"

    worker_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
