from __future__ import annotations

import logging
from typing import Any, Dict, Final, List, Optional, Tuple, Union, assert_type

# Challenge - any
logging.basicConfig(level=logging.INFO)
logging.info("Challenge - any ✅")


def foo_any(x: Any):
    pass


foo_any(1)
foo_any("10")
# foo_any(1, 2) # expect-type-error

# Challenge - dict
logging.info("Challenge - dict ✅")


def foo_dict(x: Dict[str, str]):
    pass


foo_dict({"foo": "bar"})
# foo_dict({"foo": 1}) # expect-type-error

# Challenge - final
logging.info("Challenge - final ✅")


my_list: Final = []
my_list.append(1)
# my_list = [] # expect-type-error
# my_list = "something" # expect-type-error

# Challenge - kwargs
logging.info("Challenge - kwargs ✅")


def foo_kwargs(**kwargs: Union[int, str]):
    pass


foo_kwargs(a=1, b="2")
# foo_kwargs(a=[1]) # expect-type-error

# Challenge - list
logging.info("Challenge - list ✅")


def foo_list(x: List[str]):
    pass


foo_list(["foo", "bar"])
# foo(["foo", 1]) # expect-type-error

# Challenge - optional
logging.info("Challenge - optional ✅")


def foo_optional1(x: Optional[Union[int, None]] = None):
    pass


foo_optional1(10)  # x is: 10
foo_optional1(None)  # x is: None
foo_optional1()  # x is: None


# foo_optional1("10")  # expect-type-error


def foo_optional2(x: int | None = None):
    pass


foo_optional2(10)  # x is: 10
foo_optional2(None)  # x is: None
foo_optional2()  # x is: None


# foo_optional2("10")  # expect-type-error

# Challenge - parameter
logging.info("Challenge - parameter ✅")


def foo_parameter(x: int):
    pass


foo_parameter(10)
# foo_parameter("10") # expect-type-error

# Challenge - return
logging.info("Challenge - return ✅")


def foo_return() -> int:
    return 1


assert_type(foo_return(), int)
# assert_type(foo_return(), str) # expect-type-error

# Challenge - tuple
logging.info("Challenge - tuple ✅")


def foo_tuple(x: Tuple[str, int]):
    pass


foo_tuple(("foo", 1))
# foo_tuple((1, 2)) # expect-type-error
# foo_tuple(("foo", "bar")) # expect-type-error
# foo_tuple((1, "foo")) # expect-type-error

# Challenge - typealias
logging.info("Challenge - typealias ✅")


Vector = List[float]


def foo_vector(v: Vector) -> float:
    return sum(x**2 for x in v) ** 0.5


foo_vector([1.1, 2])
# foo_vector([1]) # expect-type-error
# foo_vector(["1"]) # expect-type-error

# Challenge - union
logging.info("Challenge - union ✅")


def foo_union(x: Union[str, int]):
    pass


foo_union("foo")
foo_union(1)
# foo_union([]) # expect-type-error

# Challenge - variable
logging.info("Challenge - variable ✅")
a: int
a = 2
# a = "1" # expect-type-error
