from pydantic import BaseModel
from typing import OrderedDict, List, Optional

from .datatypes import ByteSize, ExpressionInt, IntegerList, HexInt


class BaseMemoryRegion(BaseModel):
    """Base class for memory region definitions"""

    physical_start_addr: Optional[HexInt] = None
    virtual_start_addr: Optional[HexInt] = None
    size: Optional[ByteSize] = None
    flags: List[str] = []
    allocatable: bool = False
    shared: bool = False


class MemoryRegion(BaseMemoryRegion):
    next_region: Optional[str] = None
    path: Optional[str]
    compatible: Optional[str]
    interrupts: List[int] = []


class GroupedMemoryRegion(BaseMemoryRegion):
    "Represents a list of memory regions that are allocated at contiguous physical and virtual adresses"

    def __init__(self, regions: List[MemoryRegion]):
        self.regions = regions
        self.size = sum((r.size for r in regions))
        self.physical_start_addr = regions[0].physical_start_addr
        self.virtual_start_addr = regions[0].virtual_start_addr


class HypervisorMemoryRegion(BaseMemoryRegion):
    physical_start_addr: Optional[HexInt] = None
    size: ByteSize = "16 MB"


class ShMemNetRegion(BaseModel):
    start_addr: HexInt
    device_id: int
    allocatable: bool = False

    @property
    def virtual_start_addr(self):
        return self.start_addr

    @property
    def physical_start_addr(self):
        return self.start_addr

    @property
    def size(self):
        return 0x1000 + 2 * 0x7F000

    @property
    def flags(self):
        return []

    @property
    def allocatable(self):
        return False

    @property
    def next_region(self):
        return []


class GIC(BaseModel):
    maintenance_irq: ExpressionInt
    gic_version: ExpressionInt
    gicd_base: HexInt
    gicc_base: HexInt
    gich_base: HexInt
    gicv_base: HexInt
    gicr_base: HexInt
    interrupts: IntegerList


class Board(BaseModel):
    name: str
    board: str
    pagesize: ByteSize
    virtual_address_bits: int = 48  # FIXME: that seems correct for most ARM64 Boards
    memory_regions: OrderedDict[str, MemoryRegion]
    interrupt_controllers: List[GIC] = []
