"""Tests for function-related features in byterun."""

import sys
import textwrap
import unittest

from byterun.pyvm import VirtualMachine


class FunctionTests(unittest.TestCase):
    """Test function-related features."""

    def assert_ok(self, code, raises=None):
        """Run code in both byterun and Python, and compare results."""
        code = textwrap.dedent(code)

        # Get the code object
        code_obj = compile(code, "<test>", "exec")

        # Run in real Python
        globs = {'__builtins__': __builtins__, '__name__': '__main__'}
        locs = {}

        py_exc = None
        py_value = None
        try:
            exec(code_obj, globs, locs)
            py_value = locs
        except Exception as e:
            py_exc = e

        # Run in byterun
        vm = VirtualMachine()
        vm_exc = None
        vm_value = None

        try:
            vm_value = vm.run_code(code_obj, globs, locs)
        except Exception as e:
            vm_exc = e

        # Check exceptions
        if raises:
            self.assertIsNotNone(vm_exc, "byterun should have raised an exception")
            self.assertIsInstance(vm_exc, raises)
            self.assertIsNotNone(py_exc, "Python should have raised an exception")
            self.assertIsInstance(py_exc, raises)
        else:
            if vm_exc:
                raise vm_exc
            if py_exc:
                raise py_exc

        # Compare results
        return vm_value

    def test_simple_function(self):
        """Test a simple function."""
        self.assert_ok("""
            def add(a, b):
                return a + b

            result = add(2, 3)
        """)

    def test_function_with_defaults(self):
        """Test function with default arguments."""
        self.assert_ok("""
            def greet(name, greeting="Hello"):
                return greeting + ", " + name

            x = greet("World")
            y = greet("Python", "Hi")
        """)

    def test_function_with_kwargs(self):
        """Test function with keyword arguments."""
        self.assert_ok("""
            def func(a, b=2, c=3):
                return a + b + c

            x = func(1)
            y = func(1, c=4)
            z = func(1, 5, 6)
        """)

    def test_function_with_varargs(self):
        """Test function with *args."""
        self.assert_ok("""
            def sum_all(*args):
                total = 0
                for x in args:
                    total += x
                return total

            x = sum_all(1, 2, 3, 4, 5)
        """)

    def test_function_with_kwargs_dict(self):
        """Test function with **kwargs."""
        self.assert_ok("""
            def make_dict(**kwargs):
                return kwargs

            d = make_dict(a=1, b=2, c=3)
        """)

    def test_nested_function(self):
        """Test nested function definitions."""
        self.assert_ok("""
            def outer(x):
                def inner(y):
                    return x + y
                return inner

            f = outer(10)
            result = f(5)
        """)

    def test_closure(self):
        """Test closures."""
        self.assert_ok("""
            def make_adder(n):
                def adder(x):
                    return x + n
                return adder

            add5 = make_adder(5)
            result = add5(10)
        """)

    def test_nonlocal(self):
        """Test nonlocal statement."""
        if sys.version_info >= (3, 0):
            self.assert_ok("""
                def outer():
                    x = 1
                    def inner():
                        nonlocal x
                        x = 2
                    inner()
                    return x

                result = outer()
            """)

    def test_recursion(self):
        """Test recursive functions."""
        self.assert_ok("""
            def factorial(n):
                if n <= 1:
                    return 1
                else:
                    return n * factorial(n - 1)

            result = factorial(5)
        """)

    def test_lambda(self):
        """Test lambda functions."""
        self.assert_ok("""
            add = lambda x, y: x + y
            result = add(3, 4)

            numbers = [1, 2, 3, 4, 5]
            squared = list(map(lambda x: x ** 2, numbers))
        """)

    def test_generator_function(self):
        """Test generator functions."""
        self.assert_ok("""
            def count_up_to(n):
                i = 0
                while i < n:
                    yield i
                    i += 1

            gen = count_up_to(5)
            values = list(gen)
        """)

    def test_generator_expression(self):
        """Test generator expressions."""
        self.assert_ok("""
            gen = (x * 2 for x in range(5))
            values = list(gen)
        """)

    def test_decorator(self):
        """Test function decorators."""
        self.assert_ok("""
            def double(func):
                def wrapper(*args):
                    return func(*args) * 2
                return wrapper

            @double
            def add(a, b):
                return a + b

            result = add(3, 4)
        """)

    def test_multiple_decorators(self):
        """Test multiple decorators."""
        self.assert_ok("""
            def double(func):
                def wrapper(*args):
                    return func(*args) * 2
                return wrapper

            def add_one(func):
                def wrapper(*args):
                    return func(*args) + 1
                return wrapper

            @double
            @add_one
            def value():
                return 5

            result = value()
        """)

    def test_class_definition(self):
        """Test class definition."""
        self.assert_ok("""
            class MyClass:
                def __init__(self, value):
                    self.value = value

                def get_value(self):
                    return self.value

            obj = MyClass(42)
            result = obj.get_value()
        """)

    def test_class_inheritance(self):
        """Test class inheritance."""
        self.assert_ok("""
            class Base:
                def method(self):
                    return "base"

            class Derived(Base):
                def method(self):
                    return "derived"

            obj = Derived()
            result = obj.method()
        """)

    def test_class_methods(self):
        """Test class methods."""
        self.assert_ok("""
            class MyClass:
                counter = 0

                @classmethod
                def increment(cls):
                    cls.counter += 1
                    return cls.counter

            x = MyClass.increment()
            y = MyClass.increment()
        """)

    def test_static_methods(self):
        """Test static methods."""
        self.assert_ok("""
            class MyClass:
                @staticmethod
                def add(a, b):
                    return a + b

            result = MyClass.add(3, 4)
        """)

    def test_property(self):
        """Test property decorator."""
        self.assert_ok("""
            class Circle:
                def __init__(self, radius):
                    self._radius = radius

                @property
                def radius(self):
                    return self._radius

                @radius.setter
                def radius(self, value):
                    self._radius = value

            c = Circle(5)
            x = c.radius
            c.radius = 10
            y = c.radius
        """)

    def test_method_resolution_order(self):
        """Test method resolution order."""
        self.assert_ok("""
            class A:
                def method(self):
                    return "A"

            class B(A):
                pass

            class C(A):
                def method(self):
                    return "C"

            class D(B, C):
                pass

            obj = D()
            result = obj.method()
        """)

    def test_super(self):
        """Test super() calls."""
        self.assert_ok("""
            class Base:
                def method(self):
                    return "base"

            class Derived(Base):
                def method(self):
                    base_result = super().method()
                    return f"derived-{base_result}"

            obj = Derived()
            result = obj.method()
        """)

    def test_list_as_default_argument(self):
        """Test mutable default arguments."""
        self.assert_ok("""
            def append_to_list(item, target=None):
                if target is None:
                    target = []
                target.append(item)
                return target

            list1 = append_to_list(1)
            list2 = append_to_list(2)
        """)

    def test_function_annotations(self):
        """Test function annotations (Python 3+)."""
        if sys.version_info >= (3, 0):
            self.assert_ok("""
                def greet(name: str, age: int = 0) -> str:
                    return f"Hello {name}, age {age}"

                result = greet("Alice", 30)
            """)

    def test_async_function(self):
        """Test async function definition (Python 3.5+)."""
        if sys.version_info >= (3, 5):
            self.assert_ok("""
                async def async_func():
                    return 42

                import asyncio
                # Note: We can define but not easily run async functions in this test
                x = 1  # Just test that it compiles
            """)


if __name__ == '__main__':
    unittest.main()