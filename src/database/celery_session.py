from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from core.config import settings

database_url = settings.database_url.replace("+asyncpg", "+psycopg2")

engine = create_engine(database_url, poolclass=NullPool)

celery_session = sessionmaker(engine, expire_on_commit=False)
