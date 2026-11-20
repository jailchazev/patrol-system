from logging.config import fileConfig
from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

migrate_ext = current_app.extensions["migrate"]
db = migrate_ext.db
target_metadata = db.metadata


def get_engine():
    try:
        return db.engine
    except AttributeError:
        return db.get_engine()


def get_engine_url():
    return str(get_engine().url).replace("%", "%%")


def run_migrations_offline():
    context.configure(
        url=get_engine_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
