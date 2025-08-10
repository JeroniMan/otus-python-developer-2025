from sqlalchemy.orm import Session
from typing import List, Optional

from domain.models import Order, Product
from domain.repositories import ProductRepository, OrderRepository
from .orm import ProductORM, OrderORM, OrderProductORM


class SqlAlchemyProductRepository(ProductRepository):
    """SQLAlchemy implementation of ProductRepository."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, product: Product) -> Product:
        """Add a new product."""
        product_orm = ProductORM(
            name=product.name,
            quantity=product.quantity,
            price=product.price
        )
        self.session.add(product_orm)
        self.session.flush()
        product.id = product_orm.id
        return product

    def get(self, product_id: int) -> Optional[Product]:
        """Get a product by ID."""
        product_orm = self.session.query(ProductORM).filter_by(id=product_id).first()
        if not product_orm:
            return None
        return Product(
            id=product_orm.id,
            name=product_orm.name,
            quantity=product_orm.quantity,
            price=product_orm.price
        )

    def list(self) -> List[Product]:
        """List all products."""
        products_orm = self.session.query(ProductORM).all()
        return [
            Product(
                id=p.id,
                name=p.name,
                quantity=p.quantity,
                price=p.price
            ) for p in products_orm
        ]

    def update(self, product: Product) -> Product:
        """Update a product."""
        product_orm = self.session.query(ProductORM).filter_by(id=product.id).first()
        if product_orm:
            product_orm.name = product.name
            product_orm.quantity = product.quantity
            product_orm.price = product.price
            self.session.flush()
        return product

    def delete(self, product_id: int) -> bool:
        """Delete a product."""
        product_orm = self.session.query(ProductORM).filter_by(id=product_id).first()
        if product_orm:
            self.session.delete(product_orm)
            self.session.flush()
            return True
        return False


class SqlAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, order: Order) -> Order:
        """Add a new order."""
        order_orm = OrderORM()
        self.session.add(order_orm)
        self.session.flush()

        # Add order products
        for product in order.products:
            order_product = OrderProductORM(
                order_id=order_orm.id,
                product_id=product.id,
                quantity=product.quantity,
                price=product.price
            )
            self.session.add(order_product)

        self.session.flush()
        order.id = order_orm.id
        return order

    def get(self, order_id: int) -> Optional[Order]:
        """Get an order by ID."""
        order_orm = self.session.query(OrderORM).filter_by(id=order_id).first()
        if not order_orm:
            return None

        products = []
        for op in order_orm.products:
            product = Product(
                id=op.product_id,
                name=op.product.name if op.product else f"Product_{op.product_id}",
                quantity=op.quantity,
                price=op.price
            )
            products.append(product)

        return Order(id=order_orm.id, products=products)

    def list(self) -> List[Order]:
        """List all orders."""
        orders_orm = self.session.query(OrderORM).all()
        orders = []

        for order_orm in orders_orm:
            products = []
            for op in order_orm.products:
                product = Product(
                    id=op.product_id,
                    name=op.product.name if op.product else f"Product_{op.product_id}",
                    quantity=op.quantity,
                    price=op.price
                )
                products.append(product)

            orders.append(Order(id=order_orm.id, products=products))

        return orders

    def update(self, order: Order) -> Order:
        """Update an order."""
        order_orm = self.session.query(OrderORM).filter_by(id=order.id).first()
        if order_orm:
            # Clear existing products
            for op in order_orm.products:
                self.session.delete(op)

            # Add new products
            for product in order.products:
                order_product = OrderProductORM(
                    order_id=order_orm.id,
                    product_id=product.id,
                    quantity=product.quantity,
                    price=product.price
                )
                self.session.add(order_product)

            self.session.flush()
        return order

    def delete(self, order_id: int) -> bool:
        """Delete an order."""
        order_orm = self.session.query(OrderORM).filter_by(id=order_id).first()
        if order_orm:
            self.session.delete(order_orm)
            self.session.flush()
            return True
        return False