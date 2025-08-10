"""Tests for infrastructure repositories."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.models import Product, Order
from infrastructure.orm import Base
from infrastructure.repositories import SqlAlchemyProductRepository, SqlAlchemyOrderRepository


@pytest.fixture
def session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestSqlAlchemyProductRepository:
    """Test SQLAlchemy Product Repository."""

    def test_add_product(self, session):
        """Test adding a product."""
        repo = SqlAlchemyProductRepository(session)
        product = Product(id=None, name="Test", quantity=10, price=99.99)

        result = repo.add(product)
        session.commit()

        assert result.id is not None
        assert result.name == "Test"
        assert result.quantity == 10
        assert result.price == 99.99

    def test_get_product(self, session):
        """Test getting a product."""
        repo = SqlAlchemyProductRepository(session)
        product = Product(id=None, name="Test", quantity=10, price=99.99)
        added = repo.add(product)
        session.commit()

        result = repo.get(added.id)

        assert result is not None
        assert result.id == added.id
        assert result.name == "Test"

    def test_get_nonexistent_product(self, session):
        """Test getting non-existent product."""
        repo = SqlAlchemyProductRepository(session)
        result = repo.get(999)
        assert result is None

    def test_list_products(self, session):
        """Test listing products."""
        repo = SqlAlchemyProductRepository(session)
        repo.add(Product(id=None, name="Product1", quantity=10, price=10.0))
        repo.add(Product(id=None, name="Product2", quantity=20, price=20.0))
        session.commit()

        products = repo.list()

        assert len(products) == 2
        assert products[0].name == "Product1"
        assert products[1].name == "Product2"

    def test_update_product(self, session):
        """Test updating a product."""
        repo = SqlAlchemyProductRepository(session)
        product = Product(id=None, name="Original", quantity=10, price=99.99)
        added = repo.add(product)
        session.commit()

        added.name = "Updated"
        added.quantity = 20
        repo.update(added)
        session.commit()

        result = repo.get(added.id)
        assert result.name == "Updated"
        assert result.quantity == 20

    def test_delete_product(self, session):
        """Test deleting a product."""
        repo = SqlAlchemyProductRepository(session)
        product = Product(id=None, name="Test", quantity=10, price=99.99)
        added = repo.add(product)
        session.commit()

        deleted = repo.delete(added.id)
        session.commit()

        assert deleted is True
        assert repo.get(added.id) is None


class TestSqlAlchemyOrderRepository:
    """Test SQLAlchemy Order Repository."""

    def test_add_order(self, session):
        """Test adding an order."""
        # Create products first
        product_repo = SqlAlchemyProductRepository(session)
        product1 = product_repo.add(Product(id=None, name="Product1", quantity=10, price=10.0))
        product2 = product_repo.add(Product(id=None, name="Product2", quantity=20, price=20.0))
        session.commit()

        # Create order
        order_repo = SqlAlchemyOrderRepository(session)
        order = Order(id=None)
        order.add_product(Product(id=product1.id, name="Product1", quantity=2, price=10.0))
        order.add_product(Product(id=product2.id, name="Product2", quantity=3, price=20.0))

        result = order_repo.add(order)
        session.commit()

        assert result.id is not None
        assert len(result.products) == 2

    def test_get_order(self, session):
        """Test getting an order."""
        # Create products
        product_repo = SqlAlchemyProductRepository(session)
        product = product_repo.add(Product(id=None, name="Product1", quantity=10, price=10.0))
        session.commit()

        # Create order
        order_repo = SqlAlchemyOrderRepository(session)
        order = Order(id=None)
        order.add_product(Product(id=product.id, name="Product1", quantity=2, price=10.0))
        added = order_repo.add(order)
        session.commit()

        result = order_repo.get(added.id)

        assert result is not None
        assert result.id == added.id
        assert len(result.products) == 1

    def test_list_orders(self, session):
        """Test listing orders."""
        # Create product
        product_repo = SqlAlchemyProductRepository(session)
        product = product_repo.add(Product(id=None, name="Product", quantity=100, price=10.0))
        session.commit()

        # Create orders
        order_repo = SqlAlchemyOrderRepository(session)
        for i in range(2):
            order = Order(id=None)
            order.add_product(Product(id=product.id, name="Product", quantity=1, price=10.0))
            order_repo.add(order)
        session.commit()

        orders = order_repo.list()
        assert len(orders) == 2

    def test_delete_order(self, session):
        """Test deleting an order."""
        # Create product
        product_repo = SqlAlchemyProductRepository(session)
        product = product_repo.add(Product(id=None, name="Product", quantity=10, price=10.0))
        session.commit()

        # Create order
        order_repo = SqlAlchemyOrderRepository(session)
        order = Order(id=None)
        order.add_product(Product(id=product.id, name="Product", quantity=2, price=10.0))
        added = order_repo.add(order)
        session.commit()

        deleted = order_repo.delete(added.id)
        session.commit()

        assert deleted is True
        assert order_repo.get(added.id) is None