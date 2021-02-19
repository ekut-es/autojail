from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .datatypes import ByteSize


class ChoiceList(BaseModel):
    choices: List[Any]
    min: int
    max: int


class ScalarChoice(BaseModel):
    # lower bound if any
    lower: Optional[float] = None

    # upper bound if any
    upper: Optional[float] = None

    # step size. defaults to 1
    # if bounded or 1/6 of the range
    # if completely bounded
    step: Optional[float] = None

    # cast to integer
    integer: bool = False

    # logarithmically distribute
    log: bool = False


class Partitions(BaseModel):
    """ Representation of a potentially ordered
    partition of choices into partitions elements
    """

    choices: List[Any]
    partitions: int
    ordered: bool


class GenerateParameters(BaseModel):
    cpu_allocation: Partitions
    mem_io_merge_threshold: ScalarChoice


class GenerateConfig(BaseModel):
    cpu_allocation: Dict[str, List[int]]
    mem_io_merge_threshold: ByteSize
