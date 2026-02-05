"""Data models for Instagram service responses."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class VideoInfo:
    """Information about an Instagram video."""

    video_id: str
    shortcode: str
    video_url: Optional[str]
    published_at: datetime
    caption: Optional[str]
    duration_seconds: Optional[int]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'shortcode': self.shortcode,
            'video_url': self.video_url,
            'published_at': self.published_at,
            'caption': self.caption,
            'duration_seconds': self.duration_seconds,
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
        }
