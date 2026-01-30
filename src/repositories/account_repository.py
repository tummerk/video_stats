from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import Account
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

    async def create_or_update_by_username(
        self,
        username: str,
        **kwargs
    ) -> Account:
        """Create account if not exists, otherwise update."""
        account = await self.get_by_username(username)

        if account:
            # Update existing account
            for key, value in kwargs.items():
                setattr(account, key, value)
            await self.session.flush()
            await self.session.refresh(account)
            return account
        else:
            # Create new account
            return await self.create(username=username, **kwargs)

    async def get_with_video_stats(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Account]:
        """Get accounts with video count."""
        from src.models import Video

        result = await self.session.execute(
            select(
                Account,
                func.count(Video.id).label('video_count')
            )
            .outerjoin(Video, Account.id == Video.account_id)
            .group_by(Account.id)
            .order_by(Account.username)
            .limit(limit)
            .offset(offset)
        )

        accounts = []
        for row in result:
            account = row[0]
            account.video_count = row[1]
            accounts.append(account)

        return accounts

    async def get_by_id_with_videos(self, account_id: int) -> Optional[Account]:
        """Get account with videos relationship loaded."""
        result = await self.session.execute(
            select(Account)
            .options(selectinload(Account.videos))
            .where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        """Count all accounts."""
        result = await self.session.execute(
            select(func.count(Account.id))
        )
        return result.scalar()
