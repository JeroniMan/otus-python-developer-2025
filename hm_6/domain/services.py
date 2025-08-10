from typing import List, Optional
from .models import Product, Order
from .repositories import ProductRepository, OrderRepository
from .exceptions import (
    ProductNotFoundError,
    InsufficientQuantityError,
    InvalidQuantityError
)


class WarehouseService:
    """Domain service for warehouse operations."""

    def __init__(self, product_repo: ProductRepository, order_repo: OrderRepository):
        self.product_repo = product_repo
        self.order_repo = order_repo

    def create_product(self, name: str, quantity: int, price: float) -> Product:
        """Create a new product in the warehouse."""
        if quantity < 0:
            raise InvalidQuantityError("Product quantity cannot be negative")
        if price < 0:
            raise ValueError("Product price cannot be negative")

        product = Product(id=None, name=name, quantity=quantity, price=price)
        return self.product_repo.add(product)

    def get_product(self, product_id: int) -> Product:
        """Get a product by ID."""
        product = self.product_repo.get(product_id)
        if not product:
            raise ProductNotFoundError(f"Product with id {product_id} not found")
        return product

    def list_products(self) -> List[Product]:
        """List all products in the warehouse."""
        return self.product_repo.list()

    def update_product_quantity(self, product_id: int, quantity: int) -> Product:
        """Update product quantity."""
        if quantity < 0:
            raise InvalidQuantityError("Product quantity cannot be negative")

        product = self.get_product(product_id)
        product.quantity = quantity
        return self.product_repo.update(product)

    def create_order(self, product_ids: List[tuple[int, int]]) -> Order:
        """
        Create a new order with products.

        Args:
            product_ids: List of tuples (product_id, quantity)

        Returns:
            Created order
        """
        order = Order(id=None, products=[])

        for product_id, quantity in product_ids:
            if quantity <= 0:
                raise InvalidQuantityError(f"Invalid quantity {quantity} for product {product_id}")

            product = self.get_product(product_id)

            if product.quantity < quantity:
                raise InsufficientQuantityError(
                    f"Insufficient quantity for product {product.name}. "
                    f"Available: {product.quantity}, Requested: {quantity}"
                )

            # Create order item with requested quantity
            order_item = Product(
                id=product.id,
                name=product.name,
                quantity=quantity,
                price=product.price
            )
            order.add_product(order_item)

            # Update product quantity in warehouse
            product.quantity -= quantity
            self.product_repo.update(product)

        return self.order_repo.add(order)

    def get_order(self, order_id: int) -> Order:
        """Get an order by ID."""
        order = self.order_repo.get(order_id)
        if not order:
            raise ValueError(f"Order with id {order_id} not found")
        return order

    def list_orders(self) -> List[Order]:
        """List all orders."""
        return self.order_repo.list()

    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order and return products to warehouse.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancelled successfully
        """
        order = self.get_order(order_id)

        # Return products to warehouse
        for item in order.products:
            product = self.get_product(item.id)
            product.quantity += item.quantity
            self.product_repo.update(product)

        return self.order_repo.delete(order_id)