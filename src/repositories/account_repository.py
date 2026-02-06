from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import Account, Video
from src.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_by_username(self, username: str) -> Optional[Account]:
        """Get account by username."""
        result = await self.session.execute(
            select(Account).where(Account.username == username)
        )
        return result.scalar_one_or_none()

    async def get_with_video_stats(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Account]:
        """Get accounts with video count."""
        result = await self.session.execute(
            select(Account)
            .options(selectinload(Account.videos))
            .order_by(Account.username)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id_with_videos(self, account_id: int) -> Optional[Account]:
        """Get account by ID with videos loaded."""
        result = await self.session.execute(
            select(Account)
            .options(selectinload(Account.videos))
            .where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update_by_id(
        self,
        account_id: int,
        **kwargs
    ) -> Account:
        """Create account if not exists by Instagram ID, otherwise update."""
        account = await self.get(account_id)

        if account:
            # Update existing account
            for key, value in kwargs.items():
                setattr(account, key, value)
            await self.session.flush()
            await self.session.refresh(account)
            return account
        else:
            # Create new account with Instagram ID as PK
            if "username" not in kwargs:
                raise ValueError("username is required when creating new account")
            return await self.create(id=account_id, **kwargs)
