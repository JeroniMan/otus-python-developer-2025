"""A Python interpreter written in Python for Python 3.12."""

import dis
import inspect
import linecache
import logging
import operator
import sys
import types
from typing import Any, Dict, List, Optional, Tuple, Union

from .pyobj import Block, Cell, Frame, Function, Generator, Method
from .exceptions import VirtualMachineError

log = logging.getLogger(__name__)


class VirtualMachine:
    """The main virtual machine for executing Python bytecode."""

    def __init__(self):
        self.frames: List[Frame] = []  # The call stack of frames
        self.frame: Optional[Frame] = None  # The current frame
        self.return_value = None
        self.last_exception: Optional[Tuple[type, Any, Any]] = None

    def top(self) -> Any:
        """Return the value at the top of the stack."""
        return self.frame.stack[-1]

    def pop(self, n: int = 1) -> Any:
        """Pop a value from the stack."""
        if not self.frame or not self.frame.stack:
            return None

        if n == 1:
            if self.frame.stack:
                return self.frame.stack.pop()
            return None
        else:
            result = []
            for _ in range(n):
                if self.frame.stack:
                    result.append(self.frame.stack.pop())
                else:
                    result.append(None)
            return result[::-1]

    def push(self, *vals: Any) -> None:
        """Push values onto the stack."""
        self.frame.stack.extend(vals)

    def popn(self, n: int) -> List[Any]:
        """Pop n values from the stack."""
        if n:
            ret = self.frame.stack[-n:]
            self.frame.stack[-n:] = []
            return ret
        else:
            return []

    def peek(self, n: int) -> Any:
        """Peek at the nth value from the top of the stack."""
        return self.frame.stack[-n]

    def jump(self, offset: int) -> None:
        """Jump to the given offset in the bytecode."""
        self.frame.offset = offset

    # Frame management
    def make_frame(self, code: types.CodeType, callargs: Dict[str, Any] = None,
                   global_names: Dict[str, Any] = None, local_names: Dict[str, Any] = None) -> Frame:
        """Create a new frame for code execution."""
        if global_names is None:
            global_names = {}
        if local_names is None:
            local_names = {}

        # Handle argument passing
        if callargs:
            local_names.update(callargs)

        frame = Frame(code, global_names, local_names, self.frame)
        return frame

    def push_frame(self, frame: Frame) -> None:
        """Push a frame onto the call stack."""
        self.frames.append(frame)
        self.frame = frame

    def pop_frame(self) -> Frame:
        """Pop a frame from the call stack."""
        self.frames.pop()
        if self.frames:
            self.frame = self.frames[-1]
        else:
            self.frame = None
        return self.frame

    def print_frames(self):
        """Print the call stack for debugging."""
        for f in self.frames:
            filename = f.code.co_filename
            lineno = f.line_number()
            function = f.code.co_name
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            print(f'  File "{filename}", line {lineno}, in {function}')
            if line:
                print(f'    {line.strip()}')

    def resume_frame(self, frame: Frame) -> Any:
        """Resume execution of the given frame."""
        frame.f_back = self.frame
        val = self.run_frame(frame)
        frame.f_back = None
        return val

    def run_code(self, code: types.CodeType, global_names: Dict[str, Any] = None,
                 local_names: Dict[str, Any] = None) -> Any:
        """Run the given code object."""
        frame = self.make_frame(code, global_names=global_names, local_names=local_names)
        return self.run_frame(frame)

    def unwind_block(self, frame: Frame, block: Block) -> None:
        """Unwind the values on the stack when leaving a block."""
        if block.type == 'except-handler':
            offset = 3
        else:
            offset = 0

        while len(frame.stack) > block.stack_height + offset:
            self.pop()

        if block.type == 'except-handler':
            tb, value, exctype = self.popn(3)
            self.last_exception = (exctype, value, tb)

    def parse_byte_and_args(self) -> Tuple[str, Optional[int]]:
        """Parse the current bytecode instruction."""
        frame = self.frame
        offset = frame.offset

        # Get bytecode
        bytecode = frame.code.co_code

        # Check if we're at the end
        if offset >= len(bytecode):
            return 'RETURN_VALUE', None

        # Python 3.12 uses 2-byte instructions
        byte = bytecode[offset]
        arg = bytecode[offset + 1] if offset + 1 < len(bytecode) else 0

        # Update offset for next instruction
        frame.offset += 2

        # Get opname
        if byte < len(dis.opname):
            byte_name = dis.opname[byte]
        else:
            byte_name = f'<{byte}>'

        # Handle extended args for larger constants
        if byte == dis.EXTENDED_ARG:
            arg = arg << 8
            if frame.offset < len(bytecode):
                next_byte = bytecode[frame.offset]
                next_arg = bytecode[frame.offset + 1]
                frame.offset += 2
                arg |= next_arg
                byte_name = dis.opname[next_byte] if next_byte < len(dis.opname) else f'<{next_byte}>'

        return byte_name, arg

    def dispatch(self, byte_name: str, argument: Optional[int]) -> Optional[str]:
        """Dispatch the bytecode instruction to the appropriate handler."""
        why = None

        try:
            bytecode_fn = getattr(self, f'byte_{byte_name}', None)
            if bytecode_fn is None:
                if byte_name.startswith('UNARY_'):
                    self.unaryOperator(byte_name[6:])
                elif byte_name.startswith('BINARY_'):
                    self.binaryOperator(byte_name[7:])
                else:
                    raise VirtualMachineError(f'Unknown bytecode type: {byte_name}')
            else:
                why = bytecode_fn(argument)
        except Exception:
            self.last_exception = sys.exc_info()
            why = 'exception'

        return why

    def run_frame(self, frame: Frame) -> Any:
        """Run the given frame until it returns or raises an exception."""
        self.push_frame(frame)
        max_iterations = 100000  # Safety limit to prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            try:
                byte_name, argument = self.parse_byte_and_args()

                if log.isEnabledFor(logging.DEBUG):
                    log.debug(f'{frame.offset}: {byte_name} {argument}')

                why = self.dispatch(byte_name, argument)

                # Deal with any block management
                while why and frame.block_stack:
                    why = self.manage_block_stack(frame, why)

                if why:
                    break

            except Exception as e:
                # Handle exceptions during execution
                self.last_exception = sys.exc_info()
                why = 'exception'

                # Try to handle with exception blocks
                handled = False
                while frame.block_stack:
                    block = frame.block_stack[-1]
                    if block.type in ('setup-except', 'except'):
                        why = self.manage_block_stack(frame, why)
                        handled = True
                        break
                    else:
                        frame.block_stack.pop()

                if not handled and why == 'exception':
                    break

        if iteration >= max_iterations:
            raise VirtualMachineError(f"Infinite loop detected after {max_iterations} iterations")

        self.pop_frame()

        if why == 'exception':
            if self.last_exception:
                exc, val, tb = self.last_exception
                if val:
                    raise val
                else:
                    raise
            else:
                raise RuntimeError("Unknown exception")

        return self.return_value

    def manage_block_stack(self, frame: Frame, why: str) -> Optional[str]:
        """Manage the block stack when breaking out of a block."""
        block = frame.block_stack[-1]

        if block.type == 'loop' and why == 'continue':
            self.jump(self.return_value)
            why = None
            return why

        frame.block_stack.pop()
        self.unwind_block(frame, block)

        if block.type == 'loop' and why == 'break':
            why = None
            self.jump(block.handler)
            return why

        if why == 'exception' and block.type in ('setup-except', 'setup-finally', 'except', 'finally'):
            if block.type == 'setup-except':
                exctype, value, tb = self.last_exception
                self.push(tb, value, exctype)
                # Push marker for exception handler
                self.push(tb, value, exctype)
                why = None
                self.jump(block.handler)
                return why
            elif block.type == 'setup-finally':
                if why == 'return' or why == 'continue':
                    self.push(self.return_value)
                self.push(why)
                why = None
                self.jump(block.handler)
                return why

        return why

    # Stack manipulation
    def byte_LOAD_CONST(self, const: int) -> None:
        """Load a constant onto the stack."""
        self.push(self.frame.code.co_consts[const])

    def byte_POP_TOP(self, arg: Optional[int]) -> None:
        """Pop the top value from the stack."""
        self.pop()

    def byte_DUP_TOP(self, arg: Optional[int]) -> None:
        """Duplicate the top value on the stack."""
        self.push(self.top())

    def byte_DUP_TOP_TWO(self, arg: Optional[int]) -> None:
        """Duplicate the top two values on the stack."""
        a, b = self.popn(2)
        self.push(a, b, a, b)

    def byte_ROT_TWO(self, arg: Optional[int]) -> None:
        """Swap the top two values on the stack."""
        a, b = self.popn(2)
        self.push(b, a)

    def byte_ROT_THREE(self, arg: Optional[int]) -> None:
        """Rotate the top three values on the stack."""
        a, b, c = self.popn(3)
        self.push(c, a, b)

    def byte_ROT_FOUR(self, arg: Optional[int]) -> None:
        """Rotate the top four values on the stack."""
        a, b, c, d = self.popn(4)
        self.push(d, a, b, c)

    # Names
    def byte_LOAD_NAME(self, name: int) -> None:
        """Load a name from locals or globals."""
        frame = self.frame
        name_str = frame.code.co_names[name]

        if name_str in frame.f_locals:
            val = frame.f_locals[name_str]
        elif name_str in frame.f_globals:
            val = frame.f_globals[name_str]
        elif name_str in frame.f_builtins:
            val = frame.f_builtins[name_str]
        else:
            raise NameError(f"name '{name_str}' is not defined")

        self.push(val)

    def byte_STORE_NAME(self, name: int) -> None:
        """Store a value in locals."""
        name_str = self.frame.code.co_names[name]
        self.frame.f_locals[name_str] = self.pop()

    def byte_DELETE_NAME(self, name: int) -> None:
        """Delete a name from locals."""
        name_str = self.frame.code.co_names[name]
        del self.frame.f_locals[name_str]

    def byte_LOAD_FAST(self, name: int) -> None:
        """Load a local variable."""
        name_str = self.frame.code.co_varnames[name]
        if name_str in self.frame.f_locals:
            val = self.frame.f_locals[name_str]
        else:
            raise UnboundLocalError(f"local variable '{name_str}' referenced before assignment")
        self.push(val)

    def byte_STORE_FAST(self, name: int) -> None:
        """Store a value in a local variable."""
        name_str = self.frame.code.co_varnames[name]
        self.frame.f_locals[name_str] = self.pop()

    def byte_DELETE_FAST(self, name: int) -> None:
        """Delete a local variable."""
        name_str = self.frame.code.co_varnames[name]
        del self.frame.f_locals[name_str]

    def byte_LOAD_GLOBAL(self, name: int) -> None:
        """Load a global variable."""
        name_str = self.frame.code.co_names[name]

        if name_str in self.frame.f_globals:
            val = self.frame.f_globals[name_str]
        elif name_str in self.frame.f_builtins:
            val = self.frame.f_builtins[name_str]
        else:
            raise NameError(f"name '{name_str}' is not defined")

        self.push(val)

    def byte_STORE_GLOBAL(self, name: int) -> None:
        """Store a value in globals."""
        name_str = self.frame.code.co_names[name]
        self.frame.f_globals[name_str] = self.pop()

    def byte_LOAD_DEREF(self, name: int) -> None:
        """Load a value from a cell."""
        self.push(self.frame.cells[name].get())

    def byte_STORE_DEREF(self, name: int) -> None:
        """Store a value in a cell."""
        self.frame.cells[name].set(self.pop())

    def byte_LOAD_CLOSURE(self, name: int) -> None:
        """Load a cell onto the stack."""
        self.push(self.frame.cells[name])

    # Operators
    def unaryOperator(self, op: str) -> None:
        """Handle unary operators."""
        x = self.pop()
        operations = {
            'NOT': lambda x: not x,
            'POSITIVE': operator.pos,
            'NEGATIVE': operator.neg,
            'INVERT': operator.invert,
        }
        self.push(operations[op](x))

    def byte_BINARY_SUBSCR(self, arg: Optional[int]) -> None:
        """Binary subscript operator obj[key]."""
        key = self.pop()
        obj = self.pop()

        # Handle slice operations
        if isinstance(key, slice):
            result = obj[key]
        elif key == 'SLICE':
            # Handle SLICE for slicing operations
            stop = self.pop()
            start = self.pop()
            result = obj[start:stop]
        else:
            result = obj[key]

        self.push(result)

    def binaryOperator(self, op: str) -> None:
        """Handle binary operators."""
        x, y = self.popn(2)
        operations = {
            'POWER': operator.pow,
            'MULTIPLY': operator.mul,
            'MATRIX_MULTIPLY': operator.matmul,  # Python 3.5+
            'FLOOR_DIVIDE': operator.floordiv,
            'TRUE_DIVIDE': operator.truediv,
            'MODULO': operator.mod,
            'ADD': operator.add,
            'SUBTRACT': operator.sub,
            'SUBSCR': operator.getitem,
            'LSHIFT': operator.lshift,
            'RSHIFT': operator.rshift,
            'AND': operator.and_,
            'XOR': operator.xor,
            'OR': operator.or_,
        }

        if op in operations:
            self.push(operations[op](x, y))
        else:
            raise VirtualMachineError(f"Unknown binary operator: {op}")

    def byte_COMPARE_OP(self, opnum: int) -> None:
        """Handle comparison operators."""
        x, y = self.popn(2)

        # Python 3.12 uses different comparison op indices
        # The opnum might be shifted by 1 bit in some cases
        op_index = opnum >> 1 if opnum > 10 else opnum

        operations = [
            operator.lt,  # 0: <
            operator.le,  # 1: <=
            operator.eq,  # 2: ==
            operator.ne,  # 3: !=
            operator.gt,  # 4: >
            operator.ge,  # 5: >=
            lambda x, y: x in y,  # 6: in
            lambda x, y: x not in y,  # 7: not in
            operator.is_,  # 8: is
            operator.is_not,  # 9: is not
            lambda x, y: issubclass(x, Exception) and issubclass(x, y),  # 10: exception match
        ]

        if op_index < len(operations):
            self.push(operations[op_index](x, y))
        else:
            # Fallback for unknown comparison
            self.push(x == y)

    # Attributes
    def byte_LOAD_ATTR(self, name: int) -> None:
        """Load an attribute from an object."""
        # In Python 3.12, the name index might be shifted
        if name >= len(self.frame.code.co_names):
            # Try to adjust the index
            name = name >> 1
        name_str = self.frame.code.co_names[name]
        obj = self.pop()
        val = getattr(obj, name_str)
        self.push(val)

    def byte_STORE_ATTR(self, name: int) -> None:
        """Store an attribute on an object."""
        name_str = self.frame.code.co_names[name]
        val, obj = self.popn(2)
        setattr(obj, name_str, val)

    def byte_DELETE_ATTR(self, name: int) -> None:
        """Delete an attribute from an object."""
        name_str = self.frame.code.co_names[name]
        obj = self.pop()
        delattr(obj, name_str)

    # Building data structures
    def byte_BUILD_TUPLE(self, count: int) -> None:
        """Build a tuple from the top count stack items."""
        elts = self.popn(count)
        self.push(tuple(elts))

    def byte_BUILD_LIST(self, count: int) -> None:
        """Build a list from the top count stack items."""
        elts = self.popn(count)
        self.push(elts)

    def byte_BUILD_SET(self, count: int) -> None:
        """Build a set from the top count stack items."""
        elts = self.popn(count)
        self.push(set(elts))

    def byte_BUILD_MAP(self, count: int) -> None:
        """Build a dictionary from the stack items."""
        items = self.popn(2 * count)
        # Items are key1, value1, key2, value2, ...
        self.push(dict(zip(items[::2], items[1::2])))

    def byte_STORE_SUBSCR(self, arg: Optional[int]) -> None:
        """Store a subscript (obj[key] = val)."""
        val, obj, subscr = self.popn(3)
        obj[subscr] = val

    def byte_DELETE_SUBSCR(self, arg: Optional[int]) -> None:
        """Delete a subscript (del obj[key])."""
        obj, subscr = self.popn(2)
        del obj[subscr]

    # Jumps
    def byte_POP_JUMP_IF_FALSE(self, target: int) -> None:
        """Pop and jump if false."""
        val = self.pop()
        if not val:
            # In Python 3.12, target is already in bytes
            self.jump(target)

    def byte_POP_JUMP_IF_TRUE(self, target: int) -> None:
        """Pop and jump if true."""
        val = self.pop()
        if val:
            # In Python 3.12, target is already in bytes
            self.jump(target)

    def byte_POP_JUMP_FORWARD_IF_FALSE(self, target: int) -> None:
        """Pop and jump forward if false (Python 3.12)."""
        val = self.pop()
        if not val:
            self.jump(self.frame.offset + target)

    def byte_POP_JUMP_FORWARD_IF_TRUE(self, target: int) -> None:
        """Pop and jump forward if true (Python 3.12)."""
        val = self.pop()
        if val:
            self.jump(self.frame.offset + target)

    def byte_POP_JUMP_BACKWARD_IF_FALSE(self, target: int) -> None:
        """Pop and jump backward if false (Python 3.12)."""
        val = self.pop()
        if not val:
            self.jump(self.frame.offset - target)

    def byte_POP_JUMP_BACKWARD_IF_TRUE(self, target: int) -> None:
        """Pop and jump backward if true (Python 3.12)."""
        val = self.pop()
        if val:
            self.jump(self.frame.offset - target)

    def byte_JUMP_FORWARD(self, delta: int) -> None:
        """Jump forward by delta bytes."""
        # delta is in instructions, convert to bytes
        self.jump(self.frame.offset + delta * 2)

    def byte_JUMP_ABSOLUTE(self, target: int) -> None:
        """Jump to an absolute position."""
        # target is in instructions, convert to bytes
        self.jump(target * 2)

    def byte_JUMP_IF_TRUE_OR_POP(self, target: int) -> None:
        """Jump if true, or pop if false."""
        val = self.top()
        if val:
            self.jump(target)
        else:
            self.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, target: int) -> None:
        """Jump if false, or pop if true."""
        val = self.top()
        if not val:
            self.jump(target)
        else:
            self.pop()

    # Blocks
    def byte_SETUP_LOOP(self, dest: int) -> None:
        """Setup a loop block."""
        self.frame.push_block('loop', dest)

    def byte_GET_ITER(self, arg: Optional[int]) -> None:
        """Get an iterator for an object."""
        self.push(iter(self.pop()))

    def byte_FOR_ITER(self, delta: int) -> None:
        """Get the next item from an iterator."""
        # Check if stack is empty
        if not self.frame.stack:
            return

        iterobj = self.top()
        try:
            v = next(iterobj)
            self.push(v)
        except StopIteration:
            self.pop()  # Remove the iterator
            # Jump forward to exit the loop
            self.jump(self.frame.offset + delta)

    def byte_BREAK_LOOP(self, arg: Optional[int]) -> str:
        """Break out of a loop."""
        return 'break'

    def byte_CONTINUE_LOOP(self, dest: int) -> str:
        """Continue a loop."""
        self.return_value = dest
        return 'continue'

    def byte_SETUP_EXCEPT(self, dest: int) -> None:
        """Setup an exception handler."""
        self.frame.push_block('setup-except', self.frame.offset + dest * 2)

    def byte_SETUP_FINALLY(self, dest: int) -> None:
        """Setup a finally handler."""
        self.frame.push_block('setup-finally', self.frame.offset + dest * 2)

    def byte_POP_BLOCK(self, arg: Optional[int]) -> None:
        """Pop a block from the block stack."""
        self.frame.pop_block()

    def byte_LOAD_ASSERTION_ERROR(self, arg: Optional[int]) -> None:
        """Load AssertionError for assertion statements."""
        self.push(AssertionError)

    def byte_RAISE_VARARGS(self, argc: int) -> str:
        """Raise an exception."""
        if argc == 0:
            # Re-raise
            if self.last_exception:
                exc, val, tb = self.last_exception
                raise val
            else:
                raise RuntimeError("No active exception to reraise")
        elif argc == 1:
            exc = self.pop()
            if isinstance(exc, type) and issubclass(exc, BaseException):
                exc = exc()
            raise exc
        elif argc == 2:
            cause = self.pop()
            exc = self.pop()
            if isinstance(exc, type) and issubclass(exc, BaseException):
                exc = exc()
            exc.__cause__ = cause
            raise exc
        return 'exception'

    def byte_POP_EXCEPT(self, arg: Optional[int]) -> None:
        """Pop an exception from the stack."""
        block = self.frame.pop_block()
        if block.type != 'except-handler':
            raise Exception("popped block is not an except handler")
        self.unwind_block(self.frame, block)

    def byte_END_FINALLY(self, arg: Optional[int]) -> Optional[str]:
        """End a finally block."""
        v = self.pop()
        if isinstance(v, str):
            why = v
            if why in ('return', 'continue'):
                self.return_value = self.pop()
            if why == 'exception':
                exc_type, val, tb = self.popn(3)
                self.last_exception = (exc_type, val, tb)
        elif v is None:
            why = None
        elif isinstance(v, BaseException):
            raise v
        else:
            raise VirtualMachineError(f"Confused END_FINALLY: {v}")
        return why

    # Function calling
    def byte_MAKE_FUNCTION(self, argc: int) -> None:
        """Make a function from a code object."""
        name = self.pop()
        code = self.pop()

        # Handle Python 3.6+ changes
        if sys.version_info >= (3, 6):
            # In Python 3.6+, qualified name comes before code
            name, code = code, name

        defaults = self.popn(argc & 0xFF)

        # Create our Function wrapper
        fn = Function(name, code, self.frame.f_globals, defaults, None, self)
        self.push(fn)

    def byte_MAKE_CLOSURE(self, argc: int) -> None:
        """Make a closure from a code object."""
        name = self.pop()
        closure = self.pop()
        code = self.pop()

        # Handle Python 3.6+ changes
        if sys.version_info >= (3, 6):
            name, code = code, name

        defaults = self.popn(argc & 0xFF)

        # Create our Function wrapper with closure
        fn = Function(name, code, self.frame.f_globals, defaults, closure, self)
        self.push(fn)

    def byte_CALL_FUNCTION(self, arg: int) -> None:
        """Call a function with positional and keyword arguments."""
        # Get all arguments
        args = self.popn(arg)
        func = self.pop()

        # Handle None func (comprehension, etc)
        if func is None:
            self.push(None)
            return

        # Call the function
        if hasattr(func, 'im_func'):
            # Method call
            if func.im_self:
                args = [func.im_self] + list(args)
            func = func.im_func

        if callable(func):
            retval = func(*args)
            self.push(retval)
        else:
            self.push(None)

    def byte_RETURN_VALUE(self, arg: Optional[int]) -> str:
        """Return from a function."""
        self.return_value = self.pop()
        if self.frame.generator:
            self.frame.generator.finished = True
        return 'return'

    # Imports
    def byte_IMPORT_NAME(self, name: int) -> None:
        """Import a module."""
        level, fromlist = self.popn(2)
        name_str = self.frame.code.co_names[name]
        mod = __import__(name_str, self.frame.f_globals, self.frame.f_locals, fromlist, level)
        self.push(mod)

    def byte_IMPORT_FROM(self, name: int) -> None:
        """Import a name from a module."""
        name_str = self.frame.code.co_names[name]
        mod = self.top()
        attr = getattr(mod, name_str)
        self.push(attr)

    def byte_IMPORT_STAR(self, arg: Optional[int]) -> None:
        """Import * from a module."""
        mod = self.pop()
        for name in dir(mod):
            if not name.startswith('_'):
                self.frame.f_locals[name] = getattr(mod, name)

    # Miscellaneous
    def byte_PRINT_EXPR(self, arg: Optional[int]) -> None:
        """Print the top of stack."""
        print(self.pop())

    def byte_LOAD_BUILD_CLASS(self, arg: Optional[int]) -> None:
        """Load the __build_class__ function."""
        self.push(__build_class__)

    def byte_YIELD_VALUE(self, arg: Optional[int]) -> Any:
        """Yield a value from a generator."""
        self.return_value = self.pop()
        return 'yield'

    def byte_UNPACK_SEQUENCE(self, count: int) -> None:
        """Unpack a sequence onto the stack."""
        seq = self.pop()
        for x in reversed(seq):
            self.push(x)

    def byte_BUILD_SLICE(self, count: int) -> None:
        """Build a slice object."""
        if count == 2:
            start, stop = self.popn(2)
            self.push(slice(start, stop))
        elif count == 3:
            start, stop, step = self.popn(3)
            self.push(slice(start, stop, step))
        else:
            raise VirtualMachineError(f"Invalid slice count: {count}")

    def byte_LIST_APPEND(self, count: int) -> None:
        """Append to a list (used in list comprehensions)."""
        val = self.pop()
        the_list = self.peek(count)
        the_list.append(val)

    def byte_SET_ADD(self, count: int) -> None:
        """Add to a set (used in set comprehensions)."""
        val = self.pop()
        the_set = self.peek(count)
        the_set.add(val)

    def byte_MAP_ADD(self, count: int) -> None:
        """Add to a map (used in dict comprehensions)."""
        val, key = self.popn(2)
        the_map = self.peek(count)
        the_map[key] = val

    # Python 3.12 specific opcodes
    def byte_PUSH_NULL(self, arg: Optional[int]) -> None:
        """Push a NULL value (used before CALL)."""
        self.push(None)

    def byte_CALL(self, arg: int) -> None:
        """Call a callable with arguments (Python 3.11+)."""
        # In Python 3.12, arg is the number of arguments (not including the callable)
        args = self.popn(arg)

        # Pop the NULL/self marker if present
        null_or_self = self.pop()

        # Pop the callable
        func = self.pop()

        # If null_or_self is actually a callable (method case), handle it
        if callable(null_or_self) and func is None:
            func = null_or_self
            null_or_self = None

        # Filter out NULL markers
        if null_or_self is not None and null_or_self != func:
            args = [null_or_self] + list(args)

        # Make the call
        if func is None:
            self.push(None)
            return

        if hasattr(func, 'im_func'):
            # Method call
            if func.im_self:
                args = [func.im_self] + list(args)
            func = func.im_func

        if callable(func):
            try:
                result = func(*args)
                self.push(result)
            except Exception as e:
                # Let exception propagate
                raise
        else:
            # Not callable - push None
            self.push(None)

    def byte_BINARY_OP(self, op: int) -> None:
        """Binary operation (Python 3.11+)."""
        # Check if we have enough values on stack
        if len(self.frame.stack) < 2:
            return

        x, y = self.popn(2)
        ops = {
            0: operator.add,
            1: operator.and_,
            2: operator.floordiv,
            3: operator.lshift,
            4: operator.matmul,
            5: operator.mul,
            6: operator.mod,
            7: operator.or_,
            8: operator.pow,
            9: operator.rshift,
            10: operator.sub,
            11: operator.truediv,
            12: operator.xor,
            13: operator.add,  # inplace
            14: operator.and_,  # inplace
            15: operator.floordiv,  # inplace
            16: operator.lshift,  # inplace
            17: operator.matmul,  # inplace
            18: operator.mul,  # inplace
            19: operator.mod,  # inplace
            20: operator.or_,  # inplace
            21: operator.pow,  # inplace
            22: operator.rshift,  # inplace
            23: operator.sub,  # inplace
            24: operator.truediv,  # inplace
            25: operator.xor,  # inplace
        }
        if op in ops:
            self.push(ops[op](x, y))
        else:
            raise VirtualMachineError(f"Unknown binary op: {op}")

    def byte_CACHE(self, arg: Optional[int]) -> None:
        """Cache instruction (no-op in our implementation)."""
        pass

    def byte_RESUME(self, arg: Optional[int]) -> None:
        """Resume instruction (no-op in our implementation)."""
        pass

    def byte_PRECALL(self, arg: Optional[int]) -> None:
        """Precall instruction (removed in 3.12 but may appear in older bytecode)."""
        pass

    def byte_RETURN_CONST(self, const: int) -> str:
        """Return a constant value (Python 3.12+)."""
        self.return_value = self.frame.code.co_consts[const]
        if self.frame.generator:
            self.frame.generator.finished = True
        return 'return'

    def byte_NOP(self, arg: Optional[int]) -> None:
        """No operation."""
        pass

    def byte_JUMP_BACKWARD(self, delta: int) -> None:
        """Jump backward by delta bytes."""
        # In Python 3.12, delta is the number of bytes to jump back
        self.jump(self.frame.offset - delta)

    def byte_JUMP_BACKWARD_NO_INTERRUPT(self, delta: int) -> None:
        """Jump backward without interrupt check (Python 3.12)."""
        self.jump(self.frame.offset - delta)

    def byte_LIST_EXTEND(self, count: int) -> None:
        """Extend list with items from iterable."""
        iterable = self.pop()
        list_obj = self.peek(count)
        list_obj.extend(iterable)

    def byte_SET_UPDATE(self, count: int) -> None:
        """Update set with items from iterable."""
        iterable = self.pop()
        set_obj = self.peek(count)
        set_obj.update(iterable)

    def byte_BUILD_CONST_KEY_MAP(self, count: int) -> None:
        """Build a dictionary from keys tuple and values."""
        keys = self.pop()
        values = self.popn(count)
        self.push(dict(zip(keys, values)))

    def byte_FORMAT_VALUE(self, flags: int) -> None:
        """Format a value for f-strings."""
        # flags determine conversion (str, repr, ascii) and format spec
        value = self.pop()

        # Check if there's a format spec
        fmt_spec = ''
        if flags & 0x04:
            fmt_spec = self.pop()

        # Apply conversion
        conversion = flags & 0x03
        if conversion == 1:  # str
            value = str(value)
        elif conversion == 2:  # repr
            value = repr(value)
        elif conversion == 3:  # ascii
            value = ascii(value)

        # Apply format spec
        if fmt_spec:
            value = format(value, fmt_spec)
        else:
            value = str(value)

        self.push(value)

    def byte_BUILD_STRING(self, count: int) -> None:
        """Build a string from count items."""
        items = self.popn(count)
        self.push(''.join(str(item) for item in items))

    def byte_RESERVED(self, arg: Optional[int]) -> None:
        """Reserved opcode."""
        pass

    def byte_CONTAINS_OP(self, invert: int) -> None:
        """Contains operation (in/not in)."""
        right, left = self.popn(2)
        if invert:
            self.push(left not in right)
        else:
            self.push(left in right)

    def byte_CHECK_EXC_MATCH(self, arg: Optional[int]) -> None:
        """Check if exception matches."""
        exc_type = self.pop()
        exc_value = self.top()

        # Check if exception matches the type
        if exc_value is None:
            self.push(False)
        elif isinstance(exc_type, type) and isinstance(exc_value, BaseException):
            self.push(isinstance(exc_value, exc_type))
        else:
            self.push(False)

    def byte_COPY(self, i: int) -> None:
        """Copy the i-th item to the top of stack."""
        self.push(self.peek(i))

    def byte_SWAP(self, i: int) -> None:
        """Swap TOS with the i-th item."""
        tos = self.pop()
        item = self.peek(i-1)
        self.frame.stack[-i] = tos
        self.push(item)

    def byte_IS_OP(self, invert: int) -> None:
        """Identity comparison (is/is not)."""
        right, left = self.popn(2)
        if invert:
            self.push(left is not right)
        else:
            self.push(left is right)

    def byte_LOAD_METHOD(self, name: int) -> None:
        """Load a method for calling."""
        name_str = self.frame.code.co_names[name]
        obj = self.pop()
        method = getattr(obj, name_str)
        self.push(method)
        self.push(obj)  # Push self for method call

    def byte_CALL_METHOD(self, arg: int) -> None:
        """Call a method."""
        args = self.popn(arg)
        self_arg = self.pop()
        method = self.pop()

        # Check if it's a bound method
        if hasattr(method, '__self__'):
            result = method(*args)
        else:
            result = method(self_arg, *args)
        self.push(result)

    def byte_KW_NAMES(self, consti: int) -> None:
        """Load keyword names for CALL."""
        # This is handled with CALL in Python 3.11+
        pass

    def byte_PUSH_EXC_INFO(self, arg: Optional[int]) -> None:
        """Push exception info."""
        # Used in exception handling - push current exception onto stack
        if self.last_exception:
            exc_type, exc_value, exc_tb = self.last_exception
            self.push(exc_tb)
            self.push(exc_value)
            self.push(exc_type)
        else:
            self.push(None)
            self.push(None)
            self.push(None)

    def byte_SETUP_WITH(self, delta: int) -> None:
        """Setup for with statement."""
        # In Python 3.12, with statements are handled differently
        self.frame.push_block('setup-with', self.frame.offset + delta)

    def byte_WITH_EXCEPT_START(self, arg: Optional[int]) -> None:
        """Handle exception in with statement."""
        # Pop exception info and context manager exit method
        exc_type, exc_value, exc_tb = self.popn(3)
        exit_func = self.pop()

        # Call exit with exception info
        should_suppress = exit_func(exc_type, exc_value, exc_tb)
        self.push(should_suppress)

    def byte_LOAD_FAST_AND_CLEAR(self, var: int) -> None:
        """Load a local variable and clear it (used in comprehensions)."""
        name = self.frame.code.co_varnames[var]
        val = self.frame.f_locals.get(name)
        self.frame.f_locals[name] = None
        self.push(val)

    def byte_BEFORE_WITH(self, arg: Optional[int]) -> None:
        """Prepare for with statement."""
        ctx_mgr = self.top()
        exit_method = getattr(ctx_mgr, '__exit__')
        enter_method = getattr(ctx_mgr, '__enter__')
        self.push(exit_method)
        # Call __enter__
        result = enter_method()
        self.push(result)

    def byte_STORE_FAST_STORE_FAST(self, arg: int) -> None:
        """Store two values in locals (Python 3.12)."""
        # Used in unpacking
        value2 = self.pop()
        value1 = self.pop()
        var1 = arg & 0xFF
        var2 = (arg >> 8) & 0xFF
        self.frame.f_locals[self.frame.code.co_varnames[var1]] = value1
        self.frame.f_locals[self.frame.code.co_varnames[var2]] = value2