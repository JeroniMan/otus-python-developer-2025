"""Tests for domain services."""

import pytest
from unittest.mock import Mock, MagicMock

from domain.models import Product, Order
from domain.services import WarehouseService
from domain.exceptions import (
    ProductNotFoundError,
    InsufficientQuantityError,
    InvalidQuantityError
)


class TestWarehouseService:
    """Test WarehouseService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.product_repo = Mock()
        self.order_repo = Mock()
        self.service = WarehouseService(self.product_repo, self.order_repo)

    def test_create_product(self):
        """Test creating a product."""
        # Arrange
        self.product_repo.add.return_value = Product(id=1, name="Test", quantity=10, price=99.99)

        # Act
        product = self.service.create_product("Test", 10, 99.99)

        # Assert
        assert product.id == 1
        assert product.name == "Test"
        assert product.quantity == 10
        assert product.price == 99.99
        self.product_repo.add.assert_called_once()

    def test_create_product_negative_quantity(self):
        """Test creating product with negative quantity."""
        with pytest.raises(InvalidQuantityError):
            self.service.create_product("Test", -1, 10.0)

    def test_create_product_negative_price(self):
        """Test creating product with negative price."""
        with pytest.raises(ValueError):
            self.service.create_product("Test", 10, -10.0)

    def test_get_product(self):
        """Test getting a product."""
        # Arrange
        expected_product = Product(id=1, name="Test", quantity=10, price=99.99)
        self.product_repo.get.return_value = expected_product

        # Act
        product = self.service.get_product(1)

        # Assert
        assert product == expected_product
        self.product_repo.get.assert_called_once_with(1)

    def test_get_product_not_found(self):
        """Test getting non-existent product."""
        # Arrange
        self.product_repo.get.return_value = None

        # Act & Assert
        with pytest.raises(ProductNotFoundError):
            self.service.get_product(999)

    def test_list_products(self):
        """Test listing products."""
        # Arrange
        products = [
            Product(id=1, name="Product1", quantity=10, price=10.0),
            Product(id=2, name="Product2", quantity=20, price=20.0)
        ]
        self.product_repo.list.return_value = products

        # Act
        result = self.service.list_products()

        # Assert
        assert result == products
        self.product_repo.list.assert_called_once()

    def test_update_product_quantity(self):
        """Test updating product quantity."""
        # Arrange
        product = Product(id=1, name="Test", quantity=10, price=99.99)
        self.product_repo.get.return_value = product
        self.product_repo.update.return_value = product

        # Act
        updated = self.service.update_product_quantity(1, 20)

        # Assert
        assert updated.quantity == 20
        self.product_repo.update.assert_called_once()

    def test_update_product_negative_quantity(self):
        """Test updating product with negative quantity."""
        with pytest.raises(InvalidQuantityError):
            self.service.update_product_quantity(1, -1)

    def test_create_order(self):
        """Test creating an order."""
        # Arrange
        product1 = Product(id=1, name="Product1", quantity=10, price=10.0)
        product2 = Product(id=2, name="Product2", quantity=20, price=20.0)

        self.product_repo.get.side_effect = [product1, product2]
        self.product_repo.update.return_value = None

        order = Order(id=1)
        self.order_repo.add.return_value = order

        # Act
        result = self.service.create_order([(1, 2), (2, 3)])

        # Assert
        assert result.id == 1
        assert len(result.products) == 2
        assert self.product_repo.get.call_count == 2
        assert self.product_repo.update.call_count == 2

    def test_create_order_insufficient_quantity(self):
        """Test creating order with insufficient product quantity."""
        # Arrange
        product = Product(id=1, name="Product1", quantity=5, price=10.0)
        self.product_repo.get.return_value = product

        # Act & Assert
        with pytest.raises(InsufficientQuantityError):
            self.service.create_order([(1, 10)])

    def test_create_order_invalid_quantity(self):
        """Test creating order with invalid quantity."""
        with pytest.raises(InvalidQuantityError):
            self.service.create_order([(1, 0)])

    def test_get_order(self):
        """Test getting an order."""
        # Arrange
        expected_order = Order(id=1)
        self.order_repo.get.return_value = expected_order

        # Act
        order = self.service.get_order(1)

        # Assert
        assert order == expected_order
        self.order_repo.get.assert_called_once_with(1)

    def test_get_order_not_found(self):
        """Test getting non-existent order."""
        # Arrange
        self.order_repo.get.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            self.service.get_order(999)

    def test_cancel_order(self):
        """Test cancelling an order."""
        # Arrange
        products = [
            Product(id=1, name="Product1", quantity=2, price=10.0),
            Product(id=2, name="Product2", quantity=3, price=20.0)
        ]
        order = Order(id=1, products=products)

        warehouse_product1 = Product(id=1, name="Product1", quantity=8, price=10.0)
        warehouse_product2 = Product(id=2, name="Product2", quantity=17, price=20.0)

        self.order_repo.get.return_value = order
        self.product_repo.get.side_effect = [warehouse_product1, warehouse_product2]
        self.order_repo.delete.return_value = True

        # Act
        result = self.service.cancel_order(1)

        # Assert
        assert result is True
        assert warehouse_product1.quantity == 10  # 8 + 2
        assert warehouse_product2.quantity == 20  # 17 + 3
        assert self.product_repo.update.call_count == 2
        self.order_repo.delete.assert_called_once_with(1)