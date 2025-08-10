# byterun/__init__.py
"""Byterun - A Python interpreter written in Python."""

from .pyvm import VirtualMachine
from .pyobj import Frame, Function, Method, Generator

__version__ = "1.0.0"
__all__ = ["VirtualMachine", "Frame", "Function", "Method", "Generator"]


# byterun/exceptions.py
"""Custom exceptions for the byterun virtual machine."""


class VirtualMachineError(Exception):
    """Base exception for virtual machine errors."""
    pass


class BytecodeCorruption(VirtualMachineError):
    """Raised when bytecode is corrupted or invalid."""
    pass