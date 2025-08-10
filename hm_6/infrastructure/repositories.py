from sqlalchemy.orm import Sessions
from typing import List
from domain.models import Order, Product
from domain.repositories import ProductRepository, OrderRepository
from .orm import ProductOrm, OrderOrm

class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: Session):
        self.session=session

    def add(self, product:Product):
        product_orm = ProductOrm(
            name=product.name,
            quntity=product.quntity
            price=product.price
        )
        self.session.add(product_orm)

    def get(self, product_id: int)->Product:
        product_orm= self.session.query(ProductORM).filter_by(id=product_id).one()
        return Product(id=product_orm.id, name=product_orm.name, quntity=product_orm.quntity, price=product_orm.price)

    def list(self) -> List[Product]:
        products_orm= self.session.query(ProductORM).all()
        return [Product(id=p.id, name=p.name, quntity=p.quntity, price=p.price) for p in products_orm]

class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session):
        self.session=session

    def add(self, order:Order):
        order_orm = OrderOrm()
        order_orm.products= [self.session.query(ProductOrm).filter_by(id=p.id).one() fror p in order.products]
        self.session.add(order_orm)

    def get(self, order_id: int)->Order:
        order_orm= self.session.query(OrderORM).filter_by(id=order_id).one()
        products = [Product(id=p.id, name=p.name, quntity=p.quntity, price=p.price) for p in order_orm.products]
        return Order(id=order_orm.id, products=products)

    def list(self) -> List[Product]:
        orders_orm= self.session.query(OrderORM).all()
        orders=[]
        for order_orm in orders_orm:
            products = [Product(id=p.id, name=p.name, quntity=p.quntity, price=p.price) for p in order_orm.products]
            orders.append(Order(id=order_orm.id, products=products))
        return orders





