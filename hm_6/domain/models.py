from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Product:
    """Product entity."""
    id: Optional[int]
    name: str
    quantity: int
    price: float

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("Product quantity cannot be negative")
        if self.price < 0:
            raise ValueError("Product price cannot be negative")


@dataclass
class Order:
    """Order entity."""
    id: Optional[int]
    products: List[Product] = field(default_factory=list)

    def add_product(self, product: Product):
        """Add a product to the order."""
        if product.quantity <= 0:
            raise ValueError("Cannot add product with zero or negative quantity")
        self.products.append(product)

    def calculate_total(self) -> float:
        """Calculate total order price."""
        return sum(p.price * p.quantity for p in self.products)

    def is_empty(self) -> bool:
        """Check if order is empty."""
        return len(self.products) == 0