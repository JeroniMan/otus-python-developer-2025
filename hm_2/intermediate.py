import asyncio
import functools
import logging
from asyncio import Queue
from typing import (
    Awaitable,
    Callable,
    ClassVar,
    Iterable,
    List,
    Literal,
    LiteralString,
    NotRequired,
    ParamSpec,
    Self,
    Tuple,
    TypedDict,
    TypeVar,
    Unpack,
    assert_type,
)

# Challenge - await
logging.basicConfig(level=logging.INFO)
logging.info("Challenge - await ✅")


# Make run_async async so it can be awaited
async def run_async(awaitable: Awaitable[int]):
    result = await awaitable
    return result


queue: Queue[int] = Queue()
queue2: Queue[str] = Queue()


async def async_function() -> int:
    return await queue.get()


async def async_function2() -> str:
    return await queue2.get()


async def main():
    await queue.put(42)
    await queue2.put("tests")
    await run_async(async_function())
    # await run_async(1) # expect-type-error
    # await run_async(async_function2()) # expect-type-error


asyncio.run(main())

# Challenge - callable
logging.info("Challenge - callable ✅")
SingleStringInput = Callable[[str], None]


def accept_single_string_input(func: SingleStringInput) -> None:
    pass


def string_name(name: str) -> None:
    pass


def string_value(value: str) -> None:
    pass


def int_value(value: int) -> None:
    pass


def new_name(name: str) -> str:
    return name


accept_single_string_input(string_name)
accept_single_string_input(string_value)
# accept_single_string_input(int_value) # expect-type-error
# accept_single_string_input(new_name # expect-type-error

# Challenge - class-var
logging.info("Challenge - class-var ✅")


class Foo_class_var:
    """Hint: No need to write __init__"""

    bar: ClassVar[int]


Foo_class_var.bar = 1
# Foo_class_var.bar = "1" # expect-type-error
# Foo_class_var().bar = "1" # expect-type-error

# Challenge - decorator
logging.info("Challenge - decorator ✅")
P = ParamSpec("P")  # типизация аргументов функции
R = TypeVar("R")  # тип возвращаемого значения


def decorator(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = func(*args, **kwargs)
        return result

    return wrapper


@decorator
def foo(a: int, *, b: str) -> None:
    pass


@decorator
def bar(c: int, d: str) -> None:
    pass


foo(1, b="2")
bar(c=1, d="2")
# foo(1,"2") # expect-type-error
# foo(a=1, e="2") # expect-type-error
# decorator(1) # expect-type-error

# Challenge - empty-tuple
logging.info("Challenge - empty-tuple ✅")


def foo_empty_tuple(args: Tuple[()]):
    pass


foo_empty_tuple(())
# foo_empty_tuple((1,)) # expect-type-error

# Challenge - generic
logging.info("Challenge - generic ✅")
T = TypeVar("T")


def add(a: T, b: T) -> T:
    return a


assert_type(add(1, 2), int)
assert_type(add("1", "2"), str)
assert_type(add(["1"], ["2"]), List[str])
# assert_type(add(1,"2"),  int) # expect-type-error

# Challenge - generic2
logging.info("Challenge - generic2 ✅")
T2 = TypeVar("T2", int, str)


def add2(a: T2, b: T2) -> T2:
    return a


assert_type(add2(1, 2), int)
assert_type(add2("1", "2"), str)
# add2(["1"], ["2"]) # expect-type-error
# add2(1,"2") # expect-type-error

# Challenge - generic3
logging.info("Challenge - generic3 ✅")
T3 = TypeVar("T3", bound=int)


def add3(a: T3) -> T3:
    return a


class MyInt(int):
    pass


assert_type(add3(1), int)
assert_type(add3(MyInt(1)), MyInt)
# assert_type(add("1"), str) # expect-type-error
# add3(["1"], ["2"]) # expect-type-error
# add3(1,"2") # expect-type-error

# Challenge - instance-var
logging.info("Challenge - instance-var ✅")


class Foo_instance_var:
    bar: int


foo_e = Foo_instance_var()
foo_e.bar = 1
# foo_e.bar = "1"  # expect-type-error

# Challenge - literal
logging.info("Challenge - literal ✅")


def foo_literal(direction: Literal["left", "right"]) -> None:
    pass


foo_literal("left")
foo_literal("right")

a = "".join(["l", "e", "f", "t"])
# foo_literal(a)  # expect-type-error

# Challenge - literalstring
logging.info("Challenge - literalstring ✅")


def execute_query(sql: LiteralString, parameters: Iterable[str] = ...):
    pass


def query_user(user_id: str):
    query = f"SELECT * FROM data WHERE user_id = {user_id}"
    execute_query(query)  # expect-type-error


def query_data(user_id: str, limit: bool) -> None:
    query = """
        SELECT
            user.name,
            user.age
        FROM data
        WHERE user_id = ?
    """

    if limit:
        query += " LIMIT 1"

    execute_query(query, (user_id,))


# Challenge - self
logging.info("Challenge - self ✅")


class Foo:
    def return_self(self) -> Self:
        return self


class SubclassOfFoo(Foo):
    pass


f: Foo = Foo().return_self()
sf: SubclassOfFoo = SubclassOfFoo().return_self()
# sf: SubclassOfFoo = Foo().return_self()  # expect-type-error

# Challenge - typed-dict
logging.info("Challenge - typed-dict ✅")


class Student(TypedDict):
    name: str
    age: int
    school: str


tom: Student = {"name": "Tom", "age": 15, "school": "Hogwarts"}
# a: Student = {"name": 1, "age": 15, "school": "Hogwarts"}  # expect-type-error
# a: Student = {(1,): "Tom", "age": 2, "school": "Hogwarts"}  # expect-type-error
# a: Student = {"name": "Tom", "age": "2", "school": "Hogwarts"}  # expect-type-error
# a: Student = {"name": "Tom", "age": 2}  # expect-type-error
assert tom == dict(name="Tom", age=15, school="Hogwarts")

# Challenge - typed-dict2
logging.info("Challenge - typed-dict2 ✅")


class Student2(TypedDict, total=False):
    name: str
    age: int
    school: str


tom2: Student2 = {"name": "Tom", "age": 15}
assert tom2 == dict(name="Tom", age=15)
tom3: Student2 = {"name": "Tom", "age": 15, "school": "Hogwarts"}
assert tom3 == dict(name="Tom", age=15, school="Hogwarts")
# a: Student2 = {"name": 1, "age": 15, "school": "Hogwarts"}  # expect-type-error
# a: Student2 = {(1,): "Tom", "age": 2, "school": "Hogwarts"}  # expect-type-error
# a: Student2 = {"name": "Tom", "age": "2", "school": "Hogwarts"}  # expect-type-error
# a: Student2 = {"z": "Tom", "age": 2}  # expect-type-error

# Challenge - typed-dict3
logging.info("Challenge - typed-dict3 ✅")


class Person(TypedDict):
    name: str
    age: NotRequired[int]
    gender: NotRequired[str]
    address: NotRequired[str]
    email: NotRequired[str]


capy1: Person = {
    "name": "Capy",
    "age": 1,
    "gender": "Male",
    "address": "earth",
    "email": "capy@bara.com",
}
capy2: Person = {"name": "Capy"}
# capy3: Person = {"age": 1,
#                   "gender": "Male",
#                   "address": "",
#                   "email": ""} # expect-type-error

# Challenge - unpack
logging.info("Challenge - unpack ✅")


class per(TypedDict):
    name: str
    age: int


def foo_unpack(**kwargs: Unpack[per]):
    pass


life: per = {"name": "The Meaning of Life", "age": 1983}
foo_unpack(**life)
brian: per = {"name": "Brian", "age": 30}
foo_unpack(**brian)

# foo_unpack(**{"name": "Brian"})  # expect-type-error
# person2: dict[str, object] = {"name": "Brian", "age": 20}
# foo_unpack(**person2)  # expect-type-error
# foo_unpack(**{"name": "Brian", "age": "1979"})  # expect-type-error
