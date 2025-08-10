from typing import Any
from sqlalchemy.orm import Session

from domain.unit_of_work import UnitOfWork
from .repositories import SqlAlchemyProductRepository, SqlAlchemyOrderRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session: Session = None
        self.products: SqlAlchemyProductRepository = None
        self.orders: SqlAlchemyOrderRepository = None

    def __enter__(self) -> 'SqlAlchemyUnitOfWork':
        """Enter the context manager."""
        self.session = self.session_factory()
        self.products = SqlAlchemyProductRepository(self.session)
        self.orders = SqlAlchemyOrderRepository(self.session)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.session.close()

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()