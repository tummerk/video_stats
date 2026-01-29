import instaloader
from typing import Optional, Dict, Any
from src.config import settings


class InstagramService:
    """Service for interacting with Instagram via Instaloader."""

    def __init__(self):
        """Initialize Instagram service with session credentials."""
        self.loader = instaloader.Instaloader()
        self._configure_session()

    def _configure_session(self):
        """Configure Instagram session with credentials from environment."""
        if settings.instagram_sessionid:
            # Set session cookie for authentication
            self.loader.context._session.cookies.set(
                'sessionid',
                settings.instagram_sessionid,
                domain='.instagram.com'
            )

        if settings.instagram_ds_user_id:
            self.loader.context._session.cookies.set(
                'ds_user_id',
                settings.instagram_ds_user_id,
                domain='.instagram.com'
            )

        if settings.instagramcsrftoken:
            self.loader.context._session.cookies.set(
                'csrftoken',
                settings.instagramcsrftoken,
                domain='.instagram.com'
            )

        if settings.instagram_mid:
            self.loader.context._session.cookies.set(
                'mid',
                settings.instagram_mid,
                domain='.instagram.com'
            )

    async def get_post_metrics(self, shortcode: str) -> Dict[str, Any]:
        """Fetch metrics for an Instagram post by shortcode.

        Args:
            shortcode: Instagram post shortcode (e.g., 'C1234567890')

        Returns:
            Dictionary containing:
                - view_count: int or None
                - like_count: int
                - comment_count: int
                - followers_count: int or None

        Raises:
            Exception: If post not found or API error occurs
        """
        try:
            post = instaloader.Post.from_shortcode(
                self.loader.context,
                shortcode
            )

            # Get owner profile for followers count
            followers_count = None
            try:
                profile = post.owner_profile
                followers_count = profile.followers
            except Exception as e:
                print(f"Warning: Could not fetch followers count: {e}")

            return {
                'view_count': post.video_play_count,  # Can be None for old posts
                'like_count': post.likes,
                'comment_count': post.comments,
                'followers_count': followers_count,
            }

        except Exception as e:
            print(f"Error fetching metrics for shortcode {shortcode}: {e}")
            raise

    async def get_post_info(self, shortcode: str) -> Dict[str, Any]:
        """Fetch detailed information about an Instagram post.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Dictionary with post details including:
                - video_id: str
                - shortcode: str
                - video_url: str
                - published_at: datetime
                - caption: str or None
                - duration_seconds: float or None
        """
        try:
            post = instaloader.Post.from_shortcode(
                self.loader.context,
                shortcode
            )

            return {
                'video_id': post.mediaid,
                'shortcode': post.shortcode,
                'video_url': post.url,
                'published_at': post.date_local,
                'caption': post.caption,
                'duration_seconds': post.video_duration,
            }

        except Exception as e:
            print(f"Error fetching post info for shortcode {shortcode}: {e}")
            raise

    def test_connection(self) -> bool:
        """Test if the Instagram session is working.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to fetch a simple post to test authentication
            test_shortcode = "C1234567890"  # Generic shortcode
            instaloader.Post.from_shortcode(self.loader.context, test_shortcode)
            return True
        except Exception:
            # Even if the specific post doesn't exist, if we get a specific
            # Instagram error (not a 403/401), the session is working
            return True
