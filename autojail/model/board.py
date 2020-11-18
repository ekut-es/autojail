# FIXME:  Dicts should be replaced by OrderedDict when 3.6 support is dropped
from typing import Dict, List, Optional

from pydantic import BaseModel

from .datatypes import ByteSize, ExpressionInt, HexInt, IntegerList


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
    compatible: List[str] = []
    interrupts: List[int] = []
    aliases: List[str] = []
    clock_names: List[str] = []
    clocks: List[str] = []
    clock_output_names: List[str] = []


class GroupedMemoryRegion(MemoryRegion):
    "Represents a list of memory regions that are allocated at contiguous physical and virtual adresses"
    regions: List[MemoryRegion]

    def __init__(self, regions: List[MemoryRegion]) -> None:
        # Mypy was not satisfied with a one-line lambda doing the
        # same thing
        def byte_option_to_int(b: Optional[ByteSize]) -> int:
            if b:
                return int(b.to("b"))
            else:
                return 0

        int_region_sizes = map(lambda r: byte_option_to_int(r.size), regions)

        super().__init__(
            regions=regions,
            size=ByteSize.validate(sum(int_region_sizes)),
            physical_start_addr=regions[0].physical_start_addr,
            virtual_start_addr=regions[0].virtual_start_addr,
        )

    # FIXME
    def __setattr__(self, name, value):
        if name == "physical_start_addr":
            addr = value
            for region in self.regions:
                region.physical_start_addr = addr
                addr += region.size

        elif name == "virtual_start_addr":
            addr = value
            for region in self.regions:
                region.virtual_start_addr = addr
                addr += region.size
        elif name != "size":
            for region in self.regions:
                region.__setattr__(name, value)

        super().__setattr__(name, value)


class HypervisorMemoryRegion(BaseMemoryRegion):
    physical_start_addr: Optional[HexInt] = None
    size: ByteSize = ByteSize.validate("16 MB")


class ShMemNetRegion(BaseModel):
    start_addr: HexInt
    device_id: int

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


class Clock(BaseModel):
    """Clock definition from debugfs"""

    name: str
    enable_count: int
    prepare_count: int
    protect_count: int
    rate: int
    accuracy: int
    phase: int
    duty_cycle: int
    derived_clocks: Dict[str, "Clock"] = {}
    parent: Optional[str]

    def __str__(self) -> str:
        return f"{self.name}: {self.rate} Hz"


Clock.update_forward_refs()


class CPU(BaseModel):
    name: str
    num: int
    compatible: str
    enable_method: str
    next_level_cache: Optional[str]


class Cache(BaseModel):
    name: str
    next_level_cache: Optional[str]
    waysize: Optional[int]
    sets: Optional[int]
    linesize: Optional[int]


class SimpleBus(BaseModel):
    """Memory Mapped Bus from Device Tree"""

    name: str


class Board(BaseModel):
    name: str
    board: str
    pagesize: ByteSize
    stdout_path: str = ""
    virtual_address_bits: int = 48  # FIXME: that seems correct for most ARM64 Boards
    memory_regions: Dict[str, MemoryRegion]
    cpuinfo: Dict[str, CPU]
    interrupt_controllers: List[GIC] = []
    clock_tree: Dict[str, Clock] = {}
