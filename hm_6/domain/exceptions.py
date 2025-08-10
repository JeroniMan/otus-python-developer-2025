"""Domain exceptions."""


class DomainException(Exception):
    """Base exception for domain errors."""
    pass


class ProductNotFoundError(DomainException):
    """Raised when a product is not found."""
    pass


class OrderNotFoundError(DomainException):
    """Raised when an order is not found."""
    pass


class InsufficientQuantityError(DomainException):
    """Raised when there is insufficient product quantity."""
    pass


class InvalidQuantityError(DomainException):
    """Raised when quantity is invalid."""
    pass