"""Custom exceptions for the byterun virtual machine."""


class VirtualMachineError(Exception):
    """Base exception for virtual machine errors."""
    pass


class BytecodeCorruption(VirtualMachineError):
    """Raised when bytecode is corrupted or invalid."""
    pass