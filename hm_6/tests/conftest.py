"""Pytest configuration and shared fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.orm import Base


@pytest.fixture(scope="function")
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session_factory(in_memory_db):
    """Create a session factory for testing."""
    return sessionmaker(bind=in_memory_db)


@pytest.fixture(scope="function")
def session(session_factory):
    """Create a database session for testing."""
    session = session_factory()
    yield session
    session.close()