from sqlalchemy.pool import NullPool
from sqlmodel import create_engine

from app.config.base import CONFIG

# Serverless: an invocation can't keep a pool alive between requests,
# so each session opens its own connection and Neon's pooler does the
# pooling. psycopg's automatic prepared statements are off because a
# transaction-mode pooler can hand the next query to another backend.
DB_ENGINE = create_engine(
    CONFIG.DATABASE_URL,
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
)
