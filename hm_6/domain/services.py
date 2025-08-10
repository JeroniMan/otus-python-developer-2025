from .model import Product, Order
from .repositories import ProductRepository, OrderRepository

class WarehouseService:
    def __init__(self, product_repo: ProductRepository, order_repo: OrderRepository):
        self.product_repo=product_repo
        self.order_repo=order_repo

    def create_product(self, name: str, quantity: int, price: float) -> Product:
        product=Product(id=None, name=name, quantity=quantity,price=price)
        self.product_repo.add(product)
        return product

    def create_order(self, products: List[Product]) -> Order:
        order=Order(id=None, products=products)
        self.order_repo.add(order)
        return order
