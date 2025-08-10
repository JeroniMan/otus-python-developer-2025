from sqlalchemy import Column, Integer, String, Float, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ProductORM(Base):
    """Product ORM model."""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)


class OrderORM(Base):
    """Order ORM model."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    products = relationship("OrderProductORM", back_populates="order", cascade="all, delete-orphan")


class OrderProductORM(Base):
    """Association table for Order-Product relationship."""
    __tablename__ = 'order_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("OrderORM", back_populates="products")
    product = relationship("ProductORM")