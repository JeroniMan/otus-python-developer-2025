# HM_6 - Warehouse Management System

A warehouse management system implemented using Domain-Driven Design (DDD) and Clean Architecture principles in Python.

## 📋 Description

This project demonstrates the implementation of DDD and Clean Architecture for a simple warehouse domain. The system manages products and orders with proper separation of concerns between domain logic and infrastructure.

## 🏗️ Architecture

The project follows Clean Architecture with the following layers:

### Domain Layer (`domain/`)
- **Models**: Core entities (Product, Order)
- **Repositories**: Abstract repository interfaces
- **Services**: Business logic (WarehouseService)
- **Exceptions**: Domain-specific exceptions
- **Unit of Work**: Abstract transaction management

### Infrastructure Layer (`infrastructure/`)
- **ORM**: SQLAlchemy models
- **Repositories**: Concrete repository implementations
- **Database**: Database configuration and initialization
- **Unit of Work**: SQLAlchemy-based transaction management

## 🚀 Quick Start

### Prerequisites

Install UV package manager:
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### Installation

```bash
# Install dependencies
make install

# Or using uv directly
uv sync --all-extras
```

### Running the Application

```bash
# Run the main application
make run

# Run demo script
make demo

# Or directly with uv
uv run python main.py
uv run python demo.py
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# View coverage report in browser
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint
```

## 📊 Business Logic

The warehouse system supports the following operations:

1. **Product Management**
   - Create products with name, quantity, and price
   - Update product quantities
   - List all available products
   - Track product inventory

2. **Order Management**
   - Create orders with multiple products
   - Validate product availability
   - Calculate order totals
   - Cancel orders and restore inventory

## 🧪 Testing

The project includes comprehensive tests for:

- **Domain Models**: Validation and business rules
- **Domain Services**: Business logic and workflows
- **Infrastructure**: Repository implementations and database operations

### Test Coverage

Run tests with coverage report:

```bash
uv run pytest tests/ --cov=domain --cov=infrastructure --cov-report=term
```

Current coverage target: >80% for domain layer

## 📝 Example Usage

```python
from domain.services import WarehouseService
from infrastructure.database import init_db, get_session_factory
from infrastructure.unit_of_work import SqlAlchemyUnitOfWork

# Initialize database
engine = init_db()
session_factory = get_session_factory(engine)

# Create unit of work
uow = SqlAlchemyUnitOfWork(session_factory)

with uow:
    warehouse = WarehouseService(uow.products, uow.orders)
    
    # Create products
    laptop = warehouse.create_product("Laptop", 10, 1500.00)
    mouse = warehouse.create_product("Mouse", 50, 25.00)
    
    # Create order
    order = warehouse.create_order([
        (laptop.id, 2),  # Order 2 laptops
        (mouse.id, 5),   # Order 5 mice
    ])
    
    print(f"Order total: ${order.calculate_total()}")
```

## 🛠️ Development

### Project Structure

```
hm_6/
├── domain/                 # Domain layer (business logic)
│   ├── models.py          # Domain entities
│   ├── repositories.py    # Repository interfaces
│   ├── services.py        # Domain services
│   ├── exceptions.py      # Domain exceptions
│   └── unit_of_work.py    # UoW interface
├── infrastructure/         # Infrastructure layer
│   ├── database.py        # Database configuration
│   ├── orm.py            # SQLAlchemy models
│   ├── repositories.py   # Repository implementations
│   └── unit_of_work.py   # UoW implementation
├── tests/                 # Test suite
│   ├── test_domain/      # Domain tests
│   └── test_infrastructure/ # Infrastructure tests
├── main.py               # Application entry point
├── demo.py               # Demo script
├── pyproject.toml        # Project configuration
├── .pylintrc            # Pylint configuration
├── Makefile             # Development commands
└── README.md            # This file
```

### Development with UV

UV is a fast Python package installer and resolver written in Rust. It's significantly faster than pip and poetry.

```bash
# Create virtual environment and install dependencies
uv sync --all-extras

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade

# Run commands in the virtual environment
uv run python script.py
uv run pytest
```

### Adding New Features

1. Define domain models in `domain/models.py`
2. Add repository interfaces in `domain/repositories.py`
3. Implement business logic in `domain/services.py`
4. Create infrastructure implementations in `infrastructure/`
5. Write tests in `tests/`

## 🔧 Configuration

The project uses SQLite as the default database. To change the database, modify the `DATABASE_URL` in `infrastructure/database.py`.

## 📄 License

MIT

## 👥 Contributors

- Your Name

## 📚 References

- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)