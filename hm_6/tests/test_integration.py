"""Integration tests for the warehouse system."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.models import Product, Order
from domain.services import WarehouseService
from domain.exceptions import InsufficientQuantityError, ProductNotFoundError
from infrastructure.orm import Base
from infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def uow():
    """Create a test unit of work."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return SqlAlchemyUnitOfWork(session_factory)


class TestWarehouseIntegration:
    """Integration tests for the complete warehouse system."""

    def test_complete_order_workflow(self, uow):
        """Test complete order workflow from product creation to order."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Step 1: Create products
            laptop = service.create_product("Laptop", 10, 1500.00)
            mouse = service.create_product("Mouse", 50, 25.00)
            keyboard = service.create_product("Keyboard", 30, 75.00)

            # Step 2: Verify products are created
            products = service.list_products()
            assert len(products) == 3

            # Step 3: Create an order
            order = service.create_order([
                (laptop.id, 2),
                (mouse.id, 5),
                (keyboard.id, 2)
            ])

            # Step 4: Verify order
            assert order.id is not None
            assert len(order.products) == 3
            total = order.calculate_total()
            assert total == 3275.00  # 2*1500 + 5*25 + 2*75

            # Step 5: Verify inventory was updated
            updated_laptop = service.get_product(laptop.id)
            assert updated_laptop.quantity == 8

            updated_mouse = service.get_product(mouse.id)
            assert updated_mouse.quantity == 45

            updated_keyboard = service.get_product(keyboard.id)
            assert updated_keyboard.quantity == 28

    def test_insufficient_inventory_scenario(self, uow):
        """Test handling of insufficient inventory."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create product with limited quantity
            product = service.create_product("Limited Item", 5, 100.00)

            # Try to order more than available
            with pytest.raises(InsufficientQuantityError) as exc_info:
                service.create_order([(product.id, 10)])

            assert "Insufficient quantity" in str(exc_info.value)

            # Verify inventory wasn't changed
            unchanged = service.get_product(product.id)
            assert unchanged.quantity == 5

    def test_order_cancellation_workflow(self, uow):
        """Test order cancellation and inventory restoration."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create products
            product1 = service.create_product("Product1", 20, 50.00)
            product2 = service.create_product("Product2", 30, 75.00)

            # Create order
            order = service.create_order([
                (product1.id, 5),
                (product2.id, 10)
            ])

            # Verify inventory was reduced
            assert service.get_product(product1.id).quantity == 15
            assert service.get_product(product2.id).quantity == 20

            # Cancel order
            result = service.cancel_order(order.id)
            assert result is True

            # Verify inventory was restored
            assert service.get_product(product1.id).quantity == 20
            assert service.get_product(product2.id).quantity == 30

            # Verify order is deleted
            with pytest.raises(ValueError):
                service.get_order(order.id)

    def test_multiple_orders_same_product(self, uow):
        """Test multiple orders for the same product."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create product
            product = service.create_product("Popular Item", 100, 25.00)

            # Create multiple orders
            order1 = service.create_order([(product.id, 10)])
            order2 = service.create_order([(product.id, 20)])
            order3 = service.create_order([(product.id, 30)])

            # Verify all orders were created
            orders = service.list_orders()
            assert len(orders) == 3

            # Verify inventory was correctly updated
            updated_product = service.get_product(product.id)
            assert updated_product.quantity == 40  # 100 - 10 - 20 - 30

    def test_product_update_workflow(self, uow):
        """Test updating product quantity."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create product
            product = service.create_product("Test Item", 10, 50.00)

            # Update quantity
            updated = service.update_product_quantity(product.id, 50)
            assert updated.quantity == 50

            # Verify update persisted
            retrieved = service.get_product(product.id)
            assert retrieved.quantity == 50

    def test_transaction_rollback_on_error(self, uow):
        """Test that transactions are rolled back on error."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create initial product
            product = service.create_product("Test", 10, 100.00)
            uow.commit()

        # Start new transaction that will fail
        try:
            with uow:
                service = WarehouseService(uow.products, uow.orders)

                # This should work
                service.update_product_quantity(product.id, 20)

                # This should fail (product doesn't exist)
                service.get_product(999)
        except ProductNotFoundError:
            pass

        # Verify the update was rolled back
        with uow:
            service = WarehouseService(uow.products, uow.orders)
            unchanged = service.get_product(product.id)
            assert unchanged.quantity == 10  # Should still be original value

    def test_concurrent_orders_edge_case(self, uow):
        """Test edge case where concurrent orders might exceed inventory."""
        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create product with exact quantity for one order
            product = service.create_product("Edge Case Item", 10, 100.00)

            # First order succeeds
            order1 = service.create_order([(product.id, 10)])
            assert order1 is not None

            # Second order should fail (no inventory left)
            with pytest.raises(InsufficientQuantityError):
                service.create_order([(product.id, 1)])

            # Verify inventory is at zero
            updated = service.get_product(product.id)
            assert updated.quantity == 0