"""Tests for Unit of Work pattern."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.models import Product, Order
from infrastructure.orm import Base
from infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from domain.services import WarehouseService


@pytest.fixture
def session_factory():
    """Create a test session factory."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


class TestSqlAlchemyUnitOfWork:
    """Test SQLAlchemy Unit of Work."""

    def test_uow_commit(self, session_factory):
        """Test that unit of work commits changes."""
        uow = SqlAlchemyUnitOfWork(session_factory)

        with uow:
            product = Product(id=None, name="Test", quantity=10, price=99.99)
            uow.products.add(product)
            uow.commit()

            assert product.id is not None

        # Verify in new session
        with uow:
            retrieved = uow.products.get(product.id)
            assert retrieved is not None
            assert retrieved.name == "Test"

    def test_uow_rollback_on_exception(self, session_factory):
        """Test that unit of work rolls back on exception."""
        uow = SqlAlchemyUnitOfWork(session_factory)

        try:
            with uow:
                product = Product(id=None, name="Test", quantity=10, price=99.99)
                uow.products.add(product)
                product_id = product.id
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify product was not persisted
        with uow:
            retrieved = uow.products.get(product_id)
            assert retrieved is None

    def test_uow_manual_rollback(self, session_factory):
        """Test manual rollback."""
        uow = SqlAlchemyUnitOfWork(session_factory)

        with uow:
            product = Product(id=None, name="Test", quantity=10, price=99.99)
            uow.products.add(product)
            product_id = product.id
            uow.rollback()

            # Should not be persisted after rollback
            retrieved = uow.products.get(product_id)
            assert retrieved is None

    def test_uow_with_service(self, session_factory):
        """Test unit of work with domain service."""
        uow = SqlAlchemyUnitOfWork(session_factory)

        with uow:
            service = WarehouseService(uow.products, uow.orders)

            # Create products
            product1 = service.create_product("Product1", 10, 100.0)
            product2 = service.create_product("Product2", 20, 50.0)

            # Create order
            order = service.create_order([
                (product1.id, 2),
                (product2.id, 3)
            ])

            assert order.id is not None
            assert len(order.products) == 2
            assert order.calculate_total() == 350.0  # 2*100 + 3*50

            # Check inventory was updated
            updated_product1 = service.get_product(product1.id)
            updated_product2 = service.get_product(product2.id)
            assert updated_product1.quantity == 8  # 10 - 2
            assert updated_product2.quantity == 17  # 20 - 3

    def test_uow_nested_transactions(self, session_factory):
        """Test handling of nested unit of work contexts."""
        uow1 = SqlAlchemyUnitOfWork(session_factory)
        uow2 = SqlAlchemyUnitOfWork(session_factory)

        with uow1:
            product1 = Product(id=None, name="Product1", quantity=10, price=100.0)
            uow1.products.add(product1)
            uow1.commit()

        with uow2:
            product2 = Product(id=None, name="Product2", quantity=20, price=50.0)
            uow2.products.add(product2)
            uow2.commit()

        # Both products should be persisted
        with uow1:
            products = uow1.products.list()
            assert len(products) == 2
            names = [p.name for p in products]
            assert "Product1" in names
            assert "Product2" in names