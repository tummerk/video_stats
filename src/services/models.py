"""Data models for Instagram service responses."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum


class ClientStatus(Enum):
    """Status of an Instagram client in the pool."""
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


@dataclass
class ClientHealth:
    """Health tracking for an Instagram client."""

    status: ClientStatus = ClientStatus.ACTIVE
    error_count: int = 0
    last_error: Optional[str] = None
    cooldown_until: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    def mark_success(self) -> None:
        """Mark a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        if self.status == ClientStatus.COOLDOWN:
            self.status = ClientStatus.ACTIVE
            self.cooldown_until = None

    def mark_failure(self, error_message: str, cooldown_duration: int) -> None:
        """Mark a failed request and enter cooldown.

        Args:
            error_message: Description of the error.
            cooldown_duration: Cooldown duration in seconds.
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.error_count += 1
        self.last_error = error_message
        self.status = ClientStatus.COOLDOWN
        self.cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_duration)

    def is_available(self) -> bool:
        """Check if client is available for requests.

        Returns:
            True if client can accept requests, False otherwise.
        """
        if self.status == ClientStatus.DISABLED:
            return False

        if self.status == ClientStatus.COOLDOWN:
            if self.cooldown_until and datetime.utcnow() >= self.cooldown_until:
                # Cooldown period expired
                self.status = ClientStatus.ACTIVE
                self.cooldown_until = None
                return True
            return False

        return True

    @property
    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as a float between 0 and 1.
        """
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


@dataclass
class VideoInfo:
    """Information about an Instagram video."""

    video_id: str
    shortcode: str
    video_url: Optional[str]
    published_at: datetime
    caption: Optional[str]
    duration_seconds: Optional[int]
    audio_file_path: Optional[str] = None
    transcription: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'shortcode': self.shortcode,
            'video_url': self.video_url,
            'published_at': self.published_at,
            'caption': self.caption,
            'duration_seconds': self.duration_seconds,
            'audio_file_path': self.audio_file_path,
            'transcription': self.transcription,
        }


@dataclass
class VideoMetrics:
    """Metrics for an Instagram video."""

    view_count: Optional[int]
    like_count: int
    comment_count: int
    save_count: Optional[int]
    followers_count: Optional[int]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'save_count': self.save_count,
            'followers_count': self.followers_count,
        }


@dataclass
class UserVideosResult:
    """Result of fetching user's videos."""

    username: str
    videos: List[VideoInfo]
    followers_count: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'username': self.username,
            'videos': [v.to_dict() for v in self.videos],
            'followers_count': self.followers_count,
            'account_id': getattr(self, 'account_id', None),
        }
