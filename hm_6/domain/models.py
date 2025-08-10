from dataclasses import dataclass, field
from typing import List

@dataclass
class Product:
    id: int
    name:str
    qunatity:int
    price:float

@dataclass
class Order:
    id: int
    products: List[Product] = filed(default_factory=list)

    def add_product(self, product: Product):
        self.products.append(product)