"""
Database configuration for PostgreSQL connection
"""

from urllib.parse import quote_plus

from loguru import logger
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# =============================
# Database connection parameters
# =============================

DB_HOST = settings.DB_HOST
DB_PORT = settings.DB_PORT
DB_NAME = settings.DB_NAME
DB_USER = settings.DB_USER
DB_PASSWORD = settings.DB_PASSWORD
DB_SCHEMA = settings.DB_SCHEMA or 'public'

if not DB_PASSWORD:
    raise ValueError('DB_PASSWORD not set in environment variables')

# URL-encode the password to handle special characters
encoded_password = quote_plus(DB_PASSWORD)

DATABASE_URL = f'postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# =============================
# SQLAlchemy Engine
# =============================

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,  # tie to DEBUG flag
    connect_args={
        'options': f'-c search_path={DB_SCHEMA}',
        'connect_timeout': 10,
    },
)

# =============================
# Session & Base
# =============================

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# =============================
# Dependency
# =============================


def get_db():
    """
    FastAPI dependency to get DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================
# Utilities
# =============================


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            logger.success(f'✅ Database connection successful to {DB_HOST}/{DB_NAME}')
            return True
    except Exception as e:
        logger.error(f'❌ Database connection failed: {e}')
        return False


def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.success('✅ Database tables initialized')
    except Exception as e:
        logger.error(f'❌ Failed to initialize database: {e}')
        raise
