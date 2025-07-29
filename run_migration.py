from app import create_app
from extensions import db
from alembic import command
from alembic.config import Config

app = create_app()

with app.app_context():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "20250626_remove_confidence")
    print("Migration to remove confidence column completed successfully.")
