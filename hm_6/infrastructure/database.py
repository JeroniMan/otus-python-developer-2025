from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .orm import Base

DATABASE_URL = "sqlite:///warehouse.db"


def get_engine(database_url: str = DATABASE_URL):
    """Create database engine."""
    return create_engine(database_url, echo=False)


def get_session_factory(engine):
    """Create session factory."""
    return sessionmaker(bind=engine)


def init_db(database_url: str = DATABASE_URL):
    """Initialize database."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine