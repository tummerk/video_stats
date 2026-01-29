from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
