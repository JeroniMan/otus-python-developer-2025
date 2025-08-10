"""Main application entry point."""

from domain.services import WarehouseService
from infrastructure.database import init_db, get_session_factory
from infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def main():
    """Main function demonstrating warehouse operations."""
    # Initialize database
    engine = init_db()
    session_factory = get_session_factory(engine)

    # Create unit of work
    uow = SqlAlchemyUnitOfWork(session_factory)

    # Demonstrate warehouse operations
    with uow:
        warehouse_service = WarehouseService(uow.products, uow.orders)

        # Create products
        print("Creating products...")
        product1 = warehouse_service.create_product(
            name="Laptop",
            quantity=10,
            price=1500.00
        )
        print(f"Created product: {product1}")

        product2 = warehouse_service.create_product(
            name="Mouse",
            quantity=50,
            price=25.00
        )
        print(f"Created product: {product2}")

        product3 = warehouse_service.create_product(
            name="Keyboard",
            quantity=30,
            price=75.00
        )
        print(f"Created product: {product3}")

        # List products
        print("\nAvailable products:")
        products = warehouse_service.list_products()
        for p in products:
            print(f"  - {p.name}: {p.quantity} units @ ${p.price:.2f}")

        # Create an order
        print("\nCreating order...")
        order = warehouse_service.create_order([
            (product1.id, 2),  # 2 laptops
            (product2.id, 5),  # 5 mice
            (product3.id, 2),  # 2 keyboards
        ])
        print(f"Created order #{order.id}")
        print(f"Total: ${order.calculate_total():.2f}")

        # Check updated quantities
        print("\nUpdated product quantities:")
        products = warehouse_service.list_products()
        for p in products:
            print(f"  - {p.name}: {p.quantity} units")

        # List orders
        print("\nAll orders:")
        orders = warehouse_service.list_orders()
        for o in orders:
            print(f"  Order #{o.id}: {len(o.products)} items, Total: ${o.calculate_total():.2f}")


if __name__ == "__main__":
    main()