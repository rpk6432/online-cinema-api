from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session

# Usage in route handlers: async def endpoint(db: DBSession):
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
