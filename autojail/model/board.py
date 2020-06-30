from pydantic import BaseModel
from typing import OrderedDict, List, Union, Optional

from .datatypes import ByteSize, ExpressionInt, IntegerList, HexInt

# FIXME: Split and Rename this file


class BaseMemoryRegion(BaseModel):
    """Base class for memory region definitions"""

    physical_start_addr: Optional[HexInt] = None
    virtual_start_addr: Optional[HexInt] = None
    size: Optional[ByteSize] = None
    flags: List[str] = []
    allocatable: bool = False


class MemoryRegion(BaseMemoryRegion):
    next_region: Optional[str] = None


class DeviceMemoryRegion(BaseMemoryRegion):
    """Adds a path to the corresponding device tree node"""

    path: str
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


class Board(BaseModel):
    name: str
    board: str
    pagesize: ByteSize
    virtual_address_bits: int = 48  # FIXME: that seems correct for most ARM64 Boards
    memory_regions: OrderedDict[str, MemoryRegion]


class DebugConsole(BaseModel):
    address: HexInt
    size: ByteSize
    type: str
    flags: List[str]  # FIXME: Use list of ENUM


class AMDIOMMUConfig(BaseModel):
    bdf: Optional[ExpressionInt]
    base_cap: Optional[HexInt]
    msi_cap: Optional[HexInt]
    features: Optional[ExpressionInt]


class TIPVUIOMMUConfig(BaseModel):
    tlb_base: Optional[ExpressionInt]
    tlb_size: Optional[ByteSize]


class IOMMUConfig(BaseModel):
    type: Optional[str]
    base: Optional[HexInt]
    size: Optional[ByteSize]
    arch: Union[AMDIOMMUConfig, TIPVUIOMMUConfig, None] = None


class PlatformInfoArm(BaseModel):
    maintenance_irq: Optional[ExpressionInt]
    gic_version: Optional[ExpressionInt]
    gicd_base: Optional[HexInt]
    gicc_base: Optional[HexInt]
    gich_base: Optional[HexInt]
    gicv_base: Optional[HexInt]
    gicr_base: Optional[HexInt]

    iommu_units: List[IOMMUConfig] = []


class PlatformInfoX86(BaseModel):
    pm_timer_address: Optional[HexInt]
    vtd_interrupt_limit: Optional[ExpressionInt]
    apic_mode: Optional[HexInt]
    tsc_khz: Optional[ExpressionInt]
    apic_khz: Optional[ExpressionInt]

    iommu_units: List[IOMMUConfig] = []


class PlatformInfo(BaseModel):
    pci_mmconfig_base: Optional[HexInt]
    pci_mmconfig_end_bus: HexInt
    pci_is_virtual: int
    pci_domain: int
    arch: Union[PlatformInfoArm, PlatformInfoX86]


class IRQChip(BaseModel):
    address: HexInt
    pin_base: int
    interrupts: IntegerList

    @property
    def pin_bitmap(self) -> List[int]:
        SIZE = 32

        count = 0
        res = []
        current_item = 0

        for irq in self.interrupts:
            if irq >= count + SIZE:
                res.append(current_item)
                current_item = 0
                count += SIZE
            current_item |= 1 << irq - count

        if current_item > 0:
            res.append(current_item)

        return res


class PCIDevice(BaseModel):
    type: str
    domain: int
    bdf: ExpressionInt
    bar_mask: str
    shmem_regions_start: Optional[int]
    shmem_dev_id: Optional[int]
    shmem_peers: Optional[int]
    shmem_protocol: Optional[str]

    # List of corresponding memory regions
    memory_regions: List[MemoryRegion] = []


class CellConfig(BaseModel):
    type: str
    name: str
    vpci_irq_base: ExpressionInt
    flags: List[str]  # FIXME: Use list of ENUM

    hypervisor_memory: Optional[HypervisorMemoryRegion]
    debug_console: DebugConsole
    platform_info: Optional[PlatformInfo]
    cpus: IntegerList
    memory_regions: Optional[
        OrderedDict[str, Union[MemoryRegion, ShMemNetRegion]]
    ] = {}
    irqchips: Optional[OrderedDict[str, IRQChip]] = {}
    pci_devices: Optional[OrderedDict[str, PCIDevice]] = {}


class ShmemConfig(BaseModel):
    protocol: str
    peers: List[str]
    common_output_region_size: Optional[ByteSize]
    per_device_region_size: Optional[ByteSize]


class JailhouseConfig(BaseModel):
    cells: OrderedDict[str, CellConfig]
    shmem: Optional[OrderedDict[str, ShmemConfig]]


if __name__ == "__main__":
    import yaml
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.safe_load(yaml_file)
        pprint(yaml_dict, indent=2)

        board = Board(**yaml_dict)
        pprint(board, indent=2)
