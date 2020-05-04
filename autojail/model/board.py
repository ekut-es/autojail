from pydantic import BaseModel
from typing import Dict, List, Union, Optional

from .datatypes import ByteSize, ExpressionInt, IntegerList, HexInt


class MemoryRegion(BaseModel):
    physical_start_addr: Optional[HexInt] = None
    virtual_start_addr: Optional[HexInt] = None
    size: ByteSize
    flags: List[str]  # FIXME: Use list of ENUM
    allocatable: bool = False
    next_region: Optional[str] = None


class ShMemNetRegion(BaseModel):
    start_addr: HexInt
    device_id: int


class Board(BaseModel):
    name: str
    board: str
    pagesize: ByteSize
    memory_regions: Dict[str, MemoryRegion]


class HypervisorMemory(BaseModel):
    physical_start_addr: Optional[HexInt] = None
    size: ByteSize = "16 MB"


class DebugConsole(BaseModel):
    address: HexInt
    size: ByteSize
    type: str
    flags: List[str]  # FIXME: Use list of ENUM


class PlatformInfo(BaseModel):
    pci_mmconfig_base: HexInt
    pci_mmconfig_end_bus: HexInt
    pci_is_virtual: int
    pci_domain: int
    arm: List[str]


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

    hypervisor_memory: Optional[HypervisorMemory]
    debug_console: DebugConsole
    platform_info: Optional[PlatformInfo]
    cpus: IntegerList
    memory_regions: Optional[
        Dict[str, Union[MemoryRegion, ShMemNetRegion]]
    ] = {}
    irqchips: Optional[Dict[str, IRQChip]] = {}
    pci_devices: Optional[Dict[str, PCIDevice]] = {}


class ShmemConfig(BaseModel):
    protocol: str
    peers: List[str]
    common_output_region_size: Optional[ByteSize] = None
    per_device_region_size: Optional[ByteSize] = None


class JailhouseConfig(BaseModel):
    cells: Dict[str, CellConfig]
    shmem: Optional[Dict[str, ShmemConfig]] = None


if __name__ == "__main__":
    import yaml
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.safe_load(yaml_file)
        pprint(yaml_dict, indent=2)

        board = Board(**yaml_dict)
        pprint(board, indent=2)
