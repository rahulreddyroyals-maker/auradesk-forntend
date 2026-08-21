import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

sys.path.append(str(Path(__file__).resolve().parents[3]))  # backend/ root, so `app` imports work

from app.core.config import settings  # noqa: E402
from app.models import Base  # noqa: E402

# Migrations need DDL rights (CREATE TABLE, CREATE TYPE, etc.) that the
# restricted `auradesk_app` runtime role deliberately doesn't have (see
# sql/restrict_app_role.sql) — always run migrations as the admin role.
MIGRATION_DATABASE_URL = settings.DATABASE_URL_ADMIN or settings.DATABASE_URL

config = context.config

# NOTE: we deliberately do NOT call config.set_main_option("sqlalchemy.url", ...)
# here. Alembic's Config stores that value in a Python ConfigParser, which
# treats "%" as special interpolation syntax — and a URL-encoded Postgres
# password (e.g. "%40" for "@") breaks it with a cryptic
# "invalid interpolation syntax" error. We build the engine directly from
# settings.DATABASE_URL instead, bypassing ConfigParser entirely.

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=MIGRATION_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(MIGRATION_DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
