"""Demo script showcasing the warehouse system functionality."""

import os
from domain.services import WarehouseService
from infrastructure.database import init_db, get_session_factory
from infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from domain.exceptions import InsufficientQuantityError


def print_separator():
    """Print a separator line."""
    print("-" * 60)


def demo_warehouse_system():
    """Demonstrate the warehouse management system."""
    # Clean up any existing database
    if os.path.exists("warehouse.db"):
        os.remove("warehouse.db")

    # Initialize database
    print("🚀 Initializing Warehouse Management System")
    print_separator()

    engine = init_db()
    session_factory = get_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with uow:
        service = WarehouseService(uow.products, uow.orders)

        # Create products
        print("📦 Creating products in warehouse:")
        print_separator()

        products_data = [
            ("MacBook Pro 14", 15, 2499.00),
            ("iPad Air", 25, 599.00),
            ("AirPods Pro", 50, 249.00),
            ("Magic Mouse", 100, 79.00),
            ("Magic Keyboard", 75, 99.00),
            ("USB-C Cable", 200, 19.00),
        ]

        created_products = []
        for name, quantity, price in products_data:
            product = service.create_product(name, quantity, price)
            created_products.append(product)
            print(f"✅ {name}: {quantity} units @ ${price:.2f}")

        print()
        print("📊 Current Inventory:")
        print_separator()
        all_products = service.list_products()
        total_value = sum(p.quantity * p.price for p in all_products)
        for p in all_products:
            value = p.quantity * p.price
            print(f"   {p.name:<20} | Qty: {p.quantity:>3} | Price: ${p.price:>7.2f} | Value: ${value:>9.2f}")
        print_separator()
        print(f"   Total Inventory Value: ${total_value:,.2f}")

        # Create first order
        print()
        print("🛒 Creating Order #1:")
        print_separator()

        order1_items = [
            (created_products[0].id, 2),  # 2 MacBooks
            (created_products[1].id, 3),  # 3 iPads
            (created_products[2].id, 4),  # 4 AirPods
        ]

        order1 = service.create_order(order1_items)
        print(f"✅ Order #{order1.id} created successfully!")
        print("   Items:")
        for item in order1.products:
            subtotal = item.quantity * item.price
            print(f"   - {item.quantity}x {item.name} @ ${item.price:.2f} = ${subtotal:.2f}")
        print(f"   Order Total: ${order1.calculate_total():,.2f}")

        # Create second order
        print()
        print("🛒 Creating Order #2:")
        print_separator()

        order2_items = [
            (created_products[3].id, 5),  # 5 Magic Mice
            (created_products[4].id, 5),  # 5 Magic Keyboards
            (created_products[5].id, 10),  # 10 USB-C Cables
        ]

        order2 = service.create_order(order2_items)
        print(f"✅ Order #{order2.id} created successfully!")
        print("   Items:")
        for item in order2.products:
            subtotal = item.quantity * item.price
            print(f"   - {item.quantity}x {item.name} @ ${item.price:.2f} = ${subtotal:.2f}")
        print(f"   Order Total: ${order2.calculate_total():,.2f}")

        # Show updated inventory
        print()
        print("📊 Updated Inventory After Orders:")
        print_separator()
        all_products = service.list_products()
        for p in all_products:
            value = p.quantity * p.price
            print(f"   {p.name:<20} | Qty: {p.quantity:>3} | Price: ${p.price:>7.2f} | Value: ${value:>9.2f}")

        # Try to create an order with insufficient inventory
        print()
        print("⚠️  Attempting to order more than available:")
        print_separator()

        try:
            # Try to order 20 MacBooks when we only have 13 left
            service.create_order([(created_products[0].id, 20)])
        except InsufficientQuantityError as e:
            print(f"❌ Order failed: {e}")

        # Show all orders
        print()
        print("📋 All Orders Summary:")
        print_separator()
        all_orders = service.list_orders()
        total_revenue = 0
        for order in all_orders:
            order_total = order.calculate_total()
            total_revenue += order_total
            print(f"   Order #{order.id}: {len(order.products)} items, Total: ${order_total:,.2f}")
        print_separator()
        print(f"   Total Revenue: ${total_revenue:,.2f}")

        # Cancel an order
        print()
        print("🔄 Canceling Order #2:")
        print_separator()

        if service.cancel_order(order2.id):
            print(f"✅ Order #{order2.id} cancelled successfully!")
            print("   Inventory has been restored.")

        # Show final inventory
        print()
        print("📊 Final Inventory:")
        print_separator()
        all_products = service.list_products()
        for p in all_products:
            value = p.quantity * p.price
            print(f"   {p.name:<20} | Qty: {p.quantity:>3} | Price: ${p.price:>7.2f} | Value: ${value:>9.2f}")

        print()
        print("✨ Demo completed successfully!")


if __name__ == "__main__":
    try:
        demo_warehouse_system()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise