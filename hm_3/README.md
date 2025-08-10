# Byterun - A Python Interpreter Written in Python

[![CI](https://github.com/yourusername/byterun/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/byterun/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)

A pure-Python implementation of a Python bytecode interpreter, modernized for Python 3.12.

Originally created by Ned Batchelder as an educational tool, this version has been updated to work with modern Python, removing Python 2 compatibility and the `six` module dependency.

## 📚 Educational Purpose

Byterun is designed to help understand how Python's interpreter works internally. It implements:

- **Stack-based virtual machine** - mirrors CPython's execution model
- **Frame management** - handles function calls and returns
- **Exception handling** - implements try/except/finally blocks
- **Closures and generators** - supports advanced Python features
- **Bytecode interpretation** - executes Python bytecode instructions

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/byterun.git
cd byterun/hm_3

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest black isort ruff mypy coverage
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test suites
make test-basic      # Basic Python operations
make test-functions  # Functions, closures, generators

# Run with coverage
make test-coverage
```

### Docker Support

```bash
# Build Docker image
make docker-build

# Run tests in Docker
make docker-test
```

## 🏗️ Architecture

### Core Components

1. **VirtualMachine** (`pyvm.py`)
   - Main interpreter loop
   - Bytecode dispatch
   - Stack manipulation

2. **Frame** (`pyobj.py`)
   - Execution context
   - Local/global namespaces
   - Block stack for control flow

3. **Function** (`pyobj.py`)
   - Wraps Python functions
   - Manages closures
   - Controls frame creation

4. **Block** (`pyobj.py`)
   - Handles loops and exceptions
   - Manages control flow

## 📖 How It Works

```python
from byterun.pyvm import VirtualMachine

# Create a virtual machine
vm = VirtualMachine()

# Compile Python code to bytecode
code = compile("""
def greet(name):
    return f"Hello, {name}!"

message = greet("World")
print(message)
""", "<example>", "exec")

# Run the bytecode
vm.run_code(code)
# Output: Hello, World!
```

## 🧪 Testing

The test suite validates that byterun produces the same results as CPython:

```python
class ByterunTests(unittest.TestCase):
    def assert_ok(self, code):
        """Run code in both byterun and CPython, compare results."""
        # Compile code
        code_obj = compile(code, "<test>", "exec")
        
        # Run in CPython
        python_result = exec(code_obj)
        
        # Run in byterun
        vm = VirtualMachine()
        byterun_result = vm.run_code(code_obj)
        
        # Compare results
        assert python_result == byterun_result
```

## 🔧 Development

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
mypy byterun
```

### Project Structure

```
hm_3/
├── byterun/
│   ├── __init__.py      # Package initialization
│   ├── pyvm.py          # Virtual machine implementation
│   ├── pyobj.py         # Object wrappers (Frame, Function, etc.)
│   └── exceptions.py    # Custom exceptions
├── tests/
│   ├── test_basic.py    # Basic operation tests
│   └── test_functions.py # Function-related tests
├── examples/
│   └── simple_example.py # Usage examples
├── pyproject.toml       # Project configuration
├── Makefile            # Development commands
├── Dockerfile          # Container configuration
└── README.md           # This file
```

## 🎯 Python 3.12 Compatibility

This version supports modern Python features:

- ✅ F-strings
- ✅ Type annotations
- ✅ Async/await (basic support)
- ✅ Dictionary comprehensions
- ✅ Set comprehensions
- ✅ Extended unpacking
- ✅ Nonlocal statement

### Bytecode Changes

Python 3.12 introduced significant bytecode changes:

- **Specialized adaptive interpreter** - handled as generic opcodes
- **New instructions** - `CALL`, `BINARY_OP`, `PUSH_NULL`, etc.
- **Exception handling** - updated to use exception tables
- **Jump calculations** - adapted for instruction offsets

## 📝 Limitations

This is an educational implementation with limitations:

- **Performance** - Much slower than CPython
- **Completeness** - Not all bytecode instructions implemented
- **C Extensions** - Cannot load C extension modules
- **Optimization** - No bytecode optimization or caching
- **Debugging** - Limited debugging capabilities

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Implement missing bytecode instructions
- Add support for more Python 3.12 features
- Improve error messages and debugging
- Add more comprehensive tests
- Performance optimizations

## 📚 References

- [Original Byterun](https://github.com/nedbat/byterun)
- [Architecture of Open Source Applications](https://aosabook.org/en/500L/a-python-interpreter-written-in-python.html)
- [Python 3.12 Documentation](https://docs.python.org/3.12/)
- [dis - Python bytecode disassembler](https://docs.python.org/3.12/library/dis.html)

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- **Ned Batchelder** - Original author of byterun
- **Allison Kaptur** - Contributors to the original project
- **Python Software Foundation** - For Python and its documentation

---

**Note**: This is an educational project for understanding Python internals. For production use, stick with CPython! 😊