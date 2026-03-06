import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # Use PostgreSQL in production, SQLite locally
    _db_url = os.environ.get("DATABASE_URL", "").strip()

    # If DATABASE_URL is empty or not set, use local SQLite
    if not _db_url:
        _db_url = "sqlite:///finance.db"

    # Railway gives postgres:// but SQLAlchemy needs postgresql://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
