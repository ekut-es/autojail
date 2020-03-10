import re

from typing import Union

__all__ = ['ByteSize']

StrIntFloat = Union[str, int, float]

BYTE_SIZES = {
    'b': 1,
    'kb': 2 ** 10,
    'mb': 2 ** 20,
    'gb': 2 ** 30,
    'tb': 2 ** 40,
    'pb': 2 ** 50,
    'eb': 2 ** 60,
    'k': 2 ** 10,
    'm': 2 ** 20,
    'g': 2 ** 30,
    't': 2 ** 40,
    'p': 2 ** 50,
    'e': 2 ** 60,
    'kib': 2 ** 10,
    'mib': 2 ** 20,
    'gib': 2 ** 30,
    'tib': 2 ** 40,
    'pib': 2 ** 50,
    'eib': 2 ** 60,
}
BYTE_SIZES.update({k.lower()[0]: v for k, v in BYTE_SIZES.items() if 'i' not in k})
byte_string_re = re.compile(r'^\s*(\d*\.?\d+)\s*(\w+)?', re.IGNORECASE)


class ByteSize(int):
    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, v: StrIntFloat) -> 'ByteSize':

        try:
            return cls(int(v))
        except ValueError:
            pass

        str_match = byte_string_re.match(str(v))
        if str_match is None:
            raise errors.InvalidByteSize()

        scalar, unit = str_match.groups()
        if unit is None:
            unit = 'b'

        try:
            unit_mult = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise errors.InvalidByteSizeUnit(unit=unit)

        return cls(int(float(scalar) * unit_mult))

    def human_readable(self) -> str:

        divisor = 1024
        units = ['B', 'K', 'M', 'G', 'T', 'P']
        final_unit = 'E'

        num = float(self)
        for unit in units:
            if abs(num) < divisor:
                return f'{num:0.1f}{unit}'
            num /= divisor

        return f'{num:0.1f}{final_unit}'

    def to(self, unit: str) -> float:

        try:
            unit_div = BYTE_SIZES[unit.lower()]
        except KeyError:
            raise errors.InvalidByteSizeUnit(unit=unit)

        return self / unit_div
