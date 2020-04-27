import ast
import operator
import re

from typing import Union, List, TYPE_CHECKING

import simpleeval

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator


StrIntFloat = Union[str, int, float]


class ExpressionInt(int):
    """An Integer that might be initialized from a string containing 
    a python expression evaluating to an integer

    Examples:
       1 << 3
       256 + 2
    """

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: StrIntFloat) -> "ExpressionInt":
        if isinstance(v, str):
            evaluator = simpleeval.SimpleEval()
            evaluator.operators[ast.And] = operator.and_
            evaluator.operators[ast.Or] = operator.or_
            evaluator.operators[ast.LShift] = operator.lshift
            evaluator.operators[ast.RShift] = operator.rshift
            v = evaluator.eval(v)
        cls(v)

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar("tag:yaml.org,2002:int", node)


class HexInt(int):
    """An integer that is represented by a hexadecimal value in JSON dumps"""

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: StrIntFloat) -> "ByteSize":
        return cls(int(v))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar("tag:yaml.org,2002:int", hex(node))


BYTE_SIZES = {
    "b": 1,
    "kb": 2 ** 10,
    "mb": 2 ** 20,
    "gb": 2 ** 30,
    "tb": 2 ** 40,
    "pb": 2 ** 50,
    "eb": 2 ** 60,
    "k": 2 ** 10,
    "m": 2 ** 20,
    "g": 2 ** 30,
    "t": 2 ** 40,
    "p": 2 ** 50,
    "e": 2 ** 60,
    "kib": 2 ** 10,
    "mib": 2 ** 20,
    "gib": 2 ** 30,
    "tib": 2 ** 40,
    "pib": 2 ** 50,
    "eib": 2 ** 60,
}
BYTE_SIZES.update(
    {k.lower()[0]: v for k, v in BYTE_SIZES.items() if "i" not in k}
)
byte_string_re = re.compile(r"^\s*(\d*\.?\d+)\s*(\w+)?", re.IGNORECASE)


class ByteSize(int):
    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: StrIntFloat) -> "ByteSize":

        try:
            return cls(int(v))
        except ValueError:
            pass

        str_match = byte_string_re.match(str(v))
        if str_match is None:
            raise ValueError(f"Invalid byte size in {v}")

        scalar, unit = str_match.groups()
        if unit is None:
            unit = "b"

        try:
            unit_mult = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise ValueError(f"Invalid unit for Bytesize {unit}")

        return cls(int(float(scalar) * unit_mult))

    def human_readable(self) -> str:

        divisor = 1024
        units = ["B", "K", "M", "G", "T", "P"]
        final_unit = "E"

        num = float(self)
        for unit in units:
            if abs(num) < divisor:
                return f"{num:0.1f}{unit}"
            num /= divisor

        return f"{num:0.1f}{final_unit}"

    def to(self, unit: str) -> float:

        try:
            unit_div = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise ValueError(f"Invalid unit for Bytesize {unit}")

        return self / unit_div

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar("tag:yaml.org,2002:int", hex(node))


class IntegerList(list):
    """Integer List that can be initialized with , separated values and ranges 0,2-4 representing [0,2,3,4]"""

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[str, List[int]]) -> "IntegerList":
        if isinstance(v, list):
            return cls(v)

        selection = set()
        # tokens are comma seperated values
        tokens = [x.strip() for x in v.split(",")]
        for i in tokens:
            try:
                # typically tokens are plain old integers
                selection.add(int(i))
            except Exception:
                # if not, then it might be a range
                try:
                    token = [int(k.strip()) for k in i.split("-")]
                    if len(token) > 1:
                        token.sort()
                        # we have items seperated by a dash
                        # try to build a valid range
                        first = token[0]
                        last = token[len(token) - 1]
                        for x in range(first, last + 1):
                            selection.add(x)
                    else:
                        raise ValueError(
                            "Could not read integer list item {}".format(str(i))
                        )
                except Exception:
                    raise ValueError(
                        "Could not read integer list item {}".format(str(i))
                    )

        return cls(sorted(selection))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(
            "tag:yaml.org,2002:str", ",".join(node)
        )
