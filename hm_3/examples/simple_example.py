#!/usr/bin/env python3
"""Simple examples demonstrating byterun usage."""

import dis
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from byterun.pyvm import VirtualMachine


def example_basic():
    """Basic arithmetic and variable assignment."""
    print("\n=== Basic Example ===")

    code = compile("""
x = 10
y = 20
z = x + y
print(f"Result: {z}")
""", "<example>", "exec")

    print("Bytecode:")
    dis.dis(code)

    print("\nExecution:")
    vm = VirtualMachine()
    vm.run_code(code)


def example_function():
    """Function definition and calling."""
    print("\n=== Function Example ===")

    code = compile("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(f"fib({i}) = {fibonacci(i)}")
""", "<example>", "exec")

    print("Execution:")
    vm = VirtualMachine()
    vm.run_code(code)


def example_closure():
    """Closure example."""
    print("\n=== Closure Example ===")

    code = compile("""
def make_multiplier(factor):
    def multiplier(x):
        return x * factor
    return multiplier

times_two = make_multiplier(2)
times_three = make_multiplier(3)

print(f"5 * 2 = {times_two(5)}")
print(f"5 * 3 = {times_three(5)}")
""", "<example>", "exec")

    vm = VirtualMachine()
    vm.run_code(code)


def example_generator():
    """Generator example."""
    print("\n=== Generator Example ===")

    code = compile("""
def countdown(n):
    while n > 0:
        yield n
        n -= 1

for num in countdown(5):
    print(f"Countdown: {num}")
""", "<example>", "exec")

    vm = VirtualMachine()
    vm.run_code(code)


def example_exception():
    """Exception handling example."""
    print("\n=== Exception Handling Example ===")

    code = compile("""
def divide(a, b):
    try:
        result = a / b
        print(f"{a} / {b} = {result}")
    except ZeroDivisionError:
        print(f"Cannot divide {a} by zero!")
    finally:
        print("Division operation completed")

divide(10, 2)
divide(10, 0)
""", "<example>", "exec")

    vm = VirtualMachine()
    vm.run_code(code)


def example_class():
    """Class definition example."""
    print("\n=== Class Example ===")

    code = compile("""
class Counter:
    def __init__(self, initial=0):
        self.value = initial

    def increment(self):
        self.value += 1
        return self.value

    def __str__(self):
        return f"Counter(value={self.value})"

counter = Counter(10)
print(counter)
counter.increment()
counter.increment()
print(counter)
""", "<example>", "exec")

    vm = VirtualMachine()
    vm.run_code(code)


def example_comprehensions():
    """List, dict, and set comprehensions."""
    print("\n=== Comprehensions Example ===")

    code = compile("""
# List comprehension
squares = [x**2 for x in range(10) if x % 2 == 0]
print(f"Squares of even numbers: {squares}")

# Dict comprehension
word_lengths = {word: len(word) for word in ["hello", "world", "python"]}
print(f"Word lengths: {word_lengths}")

# Set comprehension
unique_chars = {char for word in ["hello", "world"] for char in word}
print(f"Unique characters: {sorted(unique_chars)}")
""", "<example>", "exec")

    vm = VirtualMachine()
    vm.run_code(code)


def compare_with_cpython():
    """Compare byterun output with CPython."""
    print("\n=== Comparison with CPython ===")

    code_str = """
result = sum(i**2 for i in range(10))
print(f"Sum of squares: {result}")
"""

    code = compile(code_str, "<test>", "exec")

    print("CPython output:")
    exec(code)

    print("\nByterun output:")
    vm = VirtualMachine()
    vm.run_code(code)


def main():
    """Run all examples."""
    print("=" * 60)
    print("Byterun Examples - Python Interpreter in Python")
    print("=" * 60)

    example_basic()
    example_function()
    example_closure()
    example_generator()
    example_exception()
    example_class()
    example_comprehensions()
    compare_with_cpython()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()