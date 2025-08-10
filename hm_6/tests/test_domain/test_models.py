"""Tests for domain models."""

import pytest
from domain.models import Product, Order


class TestProduct:
    """Test Product model."""

    def test_create_product(self):
        """Test creating a valid product."""
        product = Product(id=1, name="Test Product", quantity=10, price=99.99)
        assert product.id == 1
        assert product.name == "Test Product"
        assert product.quantity == 10
        assert product.price == 99.99

    def test_product_negative_quantity(self):
        """Test that negative quantity raises error."""
        with pytest.raises(ValueError, match="quantity cannot be negative"):
            Product(id=1, name="Test", quantity=-1, price=10.0)

    def test_product_negative_price(self):
        """Test that negative price raises error."""
        with pytest.raises(ValueError, match="price cannot be negative"):
            Product(id=1, name="Test", quantity=10, price=-10.0)


class TestOrder:
    """Test Order model."""

    def test_create_empty_order(self):
        """Test creating an empty order."""
        order = Order(id=1)
        assert order.id == 1
        assert order.products == []
        assert order.is_empty()

    def test_add_product_to_order(self):
        """Test adding a product to an order."""
        order = Order(id=1)
        product = Product(id=1, name="Test", quantity=5, price=10.0)

        order.add_product(product)
        assert len(order.products) == 1
        assert order.products[0] == product
        assert not order.is_empty()

    def test_add_invalid_product(self):
        """Test that adding product with zero quantity raises error."""
        order = Order(id=1)
        product = Product(id=1, name="Test", quantity=0, price=10.0)

        with pytest.raises(ValueError, match="Cannot add product with zero or negative quantity"):
            order.add_product(product)

    def test_calculate_total(self):
        """Test calculating order total."""
        order = Order(id=1)
        order.add_product(Product(id=1, name="Product1", quantity=2, price=10.0))
        order.add_product(Product(id=2, name="Product2", quantity=3, price=5.0))

        assert order.calculate_total() == 35.0  # 2*10 + 3*5

    def test_calculate_total_empty_order(self):
        """Test calculating total for empty order."""
        order = Order(id=1)
        assert order.calculate_total() == 0.0