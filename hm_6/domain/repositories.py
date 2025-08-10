from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Product, Order


class ProductRepository(ABC):
    """Abstract repository for Product entity."""

    @abstractmethod
    def add(self, product: Product) -> Product:
        """Add a new product to the repository."""
        pass

    @abstractmethod
    def get(self, product_id: int) -> Optional[Product]:
        """Get a product by ID."""
        pass

    @abstractmethod
    def list(self) -> List[Product]:
        """List all products."""
        pass

    @abstractmethod
    def update(self, product: Product) -> Product:
        """Update an existing product."""
        pass

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        """Delete a product by ID."""
        pass


class OrderRepository(ABC):
    """Abstract repository for Order entity."""

    @abstractmethod
    def add(self, order: Order) -> Order:
        """Add a new order to the repository."""
        pass

    @abstractmethod
    def get(self, order_id: int) -> Optional[Order]:
        """Get an order by ID."""
        pass

    @abstractmethod
    def list(self) -> List[Order]:
        """List all orders."""
        pass

    @abstractmethod
    def update(self, order: Order) -> Order:
        """Update an existing order."""
        pass

    @abstractmethod
    def delete(self, order_id: int) -> bool:
        """Delete an order by ID."""
        pass