from abc import ABC, abstractmethod
from typing import Any


class UnitOfWork(ABC):
    """Abstract Unit of Work pattern."""

    @abstractmethod
    def __enter__(self) -> 'UnitOfWork':
        """Enter the context manager."""
        pass

    @abstractmethod
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""
        pass