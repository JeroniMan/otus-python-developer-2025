"""Basic tests for byterun."""

import dis
import sys
import textwrap
import unittest

from byterun.pyvm import VirtualMachine


class ByterunTests(unittest.TestCase):
    """Base class for byterun tests."""

    def assert_ok(self, code, raises=None):
        """Run code in both byterun and Python, and compare results."""
        code = textwrap.dedent(code)

        # Get the code object
        code_obj = compile(code, "<test>", "exec")

        # Run in real Python
        globs = {'__builtins__': __builtins__, '__name__': '__main__'}
        locs = {}

        py_exc = None
        try:
            exec(code_obj, globs, locs)
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
        self.assertEqual(vm.frame.f_locals if vm.frame else locs, locs)
        return vm_value


class TestBasic(ByterunTests):
    """Test basic Python operations."""

    def test_constant(self):
        """Test loading constants."""
        self.assert_ok("""
            x = 1
            y = 2.5
            z = 'hello'
        """)

    def test_arithmetic(self):
        """Test arithmetic operations."""
        self.assert_ok("""
            x = 1 + 2
            y = 3 * 4
            z = 5 - 1
            w = 10 / 2
        """)

    def test_comparison(self):
        """Test comparison operations."""
        self.assert_ok("""
            a = 1 < 2
            b = 3 > 2
            c = 4 == 4
            d = 5 != 6
            e = 7 <= 7
            f = 8 >= 7
        """)

    def test_boolean_operations(self):
        """Test boolean operations."""
        self.assert_ok("""
            x = True and False
            y = True or False
            z = not True
        """)

    def test_if_statement(self):
        """Test if statements."""
        self.assert_ok("""
            x = 1
            if x > 0:
                y = 'positive'
            else:
                y = 'negative'
        """)

    def test_while_loop(self):
        """Test while loops."""
        self.assert_ok("""
            x = 0
            y = 0
            while x < 5:
                y = y + x
                x = x + 1
        """)

    def test_for_loop(self):
        """Test for loops."""
        self.assert_ok("""
            total = 0
            for i in [1, 2, 3, 4, 5]:
                total = total + i
        """)

    def test_break(self):
        """Test break statement."""
        self.assert_ok("""
            x = 0
            for i in range(10):
                if i == 5:
                    break
                x = x + 1
        """)

    def test_continue(self):
        """Test continue statement."""
        self.assert_ok("""
            x = 0
            for i in range(10):
                if i % 2 == 0:
                    continue
                x = x + 1
        """)

    def test_list_operations(self):
        """Test list operations."""
        self.assert_ok("""
            x = [1, 2, 3]
            x.append(4)
            y = len(x)
            z = x[2]
        """)

    def test_dict_operations(self):
        """Test dictionary operations."""
        self.assert_ok("""
            d = {'a': 1, 'b': 2}
            d['c'] = 3
            x = d['a']
            y = len(d)
        """)

    def test_tuple(self):
        """Test tuple operations."""
        self.assert_ok("""
            t = (1, 2, 3)
            x = t[0]
            y = len(t)
        """)

    def test_set(self):
        """Test set operations."""
        self.assert_ok("""
            s = {1, 2, 3}
            s.add(4)
            x = len(s)
            y = 2 in s
        """)

    def test_list_comprehension(self):
        """Test list comprehensions."""
        self.assert_ok("""
            x = [i * 2 for i in range(5)]
        """)

    def test_dict_comprehension(self):
        """Test dictionary comprehensions."""
        self.assert_ok("""
            x = {i: i * 2 for i in range(3)}
        """)

    def test_set_comprehension(self):
        """Test set comprehensions."""
        self.assert_ok("""
            x = {i * 2 for i in range(5)}
        """)

    def test_multiple_assignment(self):
        """Test multiple assignment."""
        self.assert_ok("""
            a, b = 1, 2
            c, d, e = [3, 4, 5]
        """)

    def test_augmented_assignment(self):
        """Test augmented assignment."""
        self.assert_ok("""
            x = 5
            x += 3
            x -= 2
            x *= 2
            x //= 3
        """)

    def test_global_statement(self):
        """Test global statement."""
        self.assert_ok("""
            global_var = 1
            def change_global():
                global global_var
                global_var = 2

            change_global()
        """)

    def test_del_statement(self):
        """Test del statement."""
        self.assert_ok("""
            x = [1, 2, 3]
            del x[1]

            d = {'a': 1, 'b': 2}
            del d['a']
        """)

    def test_assert_statement(self):
        """Test assert statement."""
        self.assert_ok("""
            assert True
            x = 5
            assert x > 0
        """)

        # Test assert failure
        self.assert_ok("""
            assert False
        """, raises=AssertionError)

    def test_slice(self):
        """Test slicing."""
        self.assert_ok("""
            x = [1, 2, 3, 4, 5]
            a = x[1:3]
            b = x[::2]
            c = x[::-1]
        """)

    def test_with_statement(self):
        """Test with statement (basic)."""
        self.assert_ok("""
            class MyContext:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            with MyContext() as ctx:
                x = 1
        """)

    def test_string_formatting(self):
        """Test string formatting."""
        self.assert_ok("""
            x = "Hello, %s!" % "world"
            y = "Number: %d" % 42
        """)

    def test_f_strings(self):
        """Test f-strings (Python 3.6+)."""
        if sys.version_info >= (3, 6):
            self.assert_ok("""
                name = "world"
                x = f"Hello, {name}!"
                y = f"2 + 2 = {2 + 2}"
            """)

    def test_exception_handling(self):
        """Test exception handling."""
        self.assert_ok("""
            try:
                x = 1 / 0
            except ZeroDivisionError:
                x = 'caught'
        """)

    def test_nested_exception(self):
        """Test nested exception handling."""
        self.assert_ok("""
            try:
                try:
                    x = 1 / 0
                except KeyError:
                    y = 'wrong'
            except ZeroDivisionError:
                z = 'caught'
        """)

    def test_finally(self):
        """Test finally clause."""
        self.assert_ok("""
            x = 0
            try:
                x = 1
            finally:
                x = 2
        """)

    def test_raise(self):
        """Test raise statement."""
        self.assert_ok("""
            try:
                raise ValueError("test")
            except ValueError as e:
                x = str(e)
        """)


if __name__ == '__main__':
    unittest.main()