from pydantic import BaseModel
from typing import Dict, List, Union

from .datatypes import ByteSize

class MemoryRegion(BaseModel):
    physical_start_addr: int
    virtual_start_addr: int
    size: ByteSize
    flags: List[str]  # FIXME: Use list of ENUM


class SHMemoryRegion(BaseModel):
    physical_start_addr: int
    virtual_start_addr: int
    size: ByteSize
    flags: List[str]  # FIXME: Use list of ENUM


class Board(BaseModel):
    name: str
    board: str
    memory_regions: Dict[str, Union[MemoryRegion, SHMemoryRegion]]


if __name__ == "__main__":
    import yaml
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.load(yaml_file)
        pprint(yaml_dict, indent=2)

        board = Board(**yaml_dict)
        pprint(board, indent=2)
