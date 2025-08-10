"""Object and function wrappers for the byterun virtual machine."""

import inspect
import types
from typing import Any, Dict, List, Optional, Tuple
from collections import namedtuple

Block = namedtuple("Block", ["type", "handler", "stack_height"])


class Frame:
    """A single frame of execution."""

    def __init__(self, code: types.CodeType, global_names: Dict[str, Any],
                 local_names: Dict[str, Any], prev_frame: Optional['Frame']):
        self.code = code
        self.f_globals = global_names
        self.f_locals = local_names
        self.f_back = prev_frame
        self.stack: List[Any] = []
        self.block_stack: List[Block] = []
        self.f_lineno = code.co_firstlineno
        self.f_lasti = 0
        self.offset = 0

        # Built-in namespace
        self.f_builtins = global_names.get('__builtins__', {})
        if hasattr(self.f_builtins, '__dict__'):
            self.f_builtins = self.f_builtins.__dict__

        # Cells for closures
        self.cells = {}
        if code.co_cellvars or code.co_freevars:
            for var in code.co_cellvars:
                self.cells[var] = Cell()
            if prev_frame and prev_frame.cells:
                for var in code.co_freevars:
                    idx = prev_frame.code.co_cellvars.index(var) if var in prev_frame.code.co_cellvars else None
                    if idx is not None:
                        self.cells[var] = prev_frame.cells[var]

        # Generator support
        self.generator = None

    def push_block(self, b_type: str, handler: Optional[int] = None) -> None:
        """Push a block onto the block stack."""
        stack_height = len(self.stack)
        self.block_stack.append(Block(b_type, handler, stack_height))

    def pop_block(self) -> Block:
        """Pop a block from the block stack."""
        return self.block_stack.pop()

    def line_number(self) -> int:
        """Get the current line number."""
        # Simplified line number calculation
        return self.f_lineno


class Cell:
    """A cell for closures."""

    def __init__(self, value: Any = None):
        self.contents = value

    def get(self) -> Any:
        """Get the cell's value."""
        if self.contents is None:
            raise ValueError("Cell is empty")
        return self.contents

    def set(self, value: Any) -> None:
        """Set the cell's value."""
        self.contents = value


class Function:
    """A function wrapper that allows us to control execution."""

    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_dict', 'func_closure', '__name__', '__dict__',
        '_vm', '_func', '_doc'
    ]

    def __init__(self, name: str, code: types.CodeType, globs: Dict[str, Any],
                 defaults: Optional[Tuple] = None, closure: Optional[Tuple[Cell, ...]] = None,
                 vm=None):
        self._vm = vm
        self.func_code = code
        self.func_name = self.__name__ = name or code.co_name
        self.func_defaults = defaults
        self.func_globals = globs
        self.func_dict = {}
        self.func_closure = closure
        self.__dict__ = {}
        self._doc = code.co_consts[0] if code.co_consts and isinstance(code.co_consts[0], str) else None

        # For compatibility
        self._func = self

    @property
    def __doc__(self):
        """Get the docstring."""
        return self._doc

    def __call__(self, *args, **kwargs) -> Any:
        """Call the function."""
        if self._vm:
            # Create call arguments dictionary
            callargs = {}

            # Get parameter names from code object
            argcount = self.func_code.co_argcount
            argnames = self.func_code.co_varnames[:argcount]

            # Assign positional arguments
            for i, name in enumerate(argnames):
                if i < len(args):
                    callargs[name] = args[i]
                elif self.func_defaults and (argcount - i) <= len(self.func_defaults):
                    default_index = len(self.func_defaults) - (argcount - i)
                    callargs[name] = self.func_defaults[default_index]

            # Assign keyword arguments
            callargs.update(kwargs)

            # Create and run frame
            frame = self._vm.make_frame(self.func_code, callargs, self.func_globals, {})
            return self._vm.run_frame(frame)
        else:
            # Fallback - should not happen in normal use
            raise RuntimeError("Function called without VM")

    def __repr__(self) -> str:
        return f'<Function {self.func_name} at {id(self):#x}>'


class Method:
    """A method wrapper."""

    def __init__(self, obj: Any, _class: type, func: Function):
        self.im_self = obj
        self.im_class = _class
        self.im_func = func

    def __call__(self, *args, **kwargs) -> Any:
        """Call the method."""
        if self.im_self:
            return self.im_func(self.im_self, *args, **kwargs)
        else:
            return self.im_func(*args, **kwargs)

    def __repr__(self) -> str:
        name = f"{self.im_class.__name__}.{self.im_func.func_name}"
        if self.im_self:
            return f'<bound method {name} of {self.im_self!r}>'
        else:
            return f'<unbound method {name}>'


class Generator:
    """A generator wrapper."""

    def __init__(self, frame: Frame, vm):
        self.frame = frame
        self.vm = vm
        self.started = False
        self.finished = False

    def __iter__(self):
        """Return self as an iterator."""
        return self

    def __next__(self) -> Any:
        """Get the next value from the generator."""
        if self.finished:
            raise StopIteration

        if not self.started:
            self.started = True
            self.frame.generator = self

        val = self.vm.resume_frame(self.frame)

        if self.finished:
            raise StopIteration

        return val

    def send(self, value: Any) -> Any:
        """Send a value into the generator."""
        if not self.started:
            if value is not None:
                raise TypeError("can't send non-None value to a just-started generator")
            return self.__next__()

        self.frame.stack.append(value)
        return self.__next__()

    def close(self) -> None:
        """Close the generator."""
        self.finished = True