from pydantic import BaseModel
from typing import Dict, List, Union, Optional

from .datatypes import ByteSize, IntegerList, HexInt


class MemoryRegion(BaseModel):
    physical_start_addr: HexInt
    virtual_start_addr: HexInt
    size: ByteSize
    flags: List[str]  # FIXME: Use list of ENUM


class ShMemNetRegion(BaseModel):
    start_addr: HexInt
    device_id: int


class Board(BaseModel):
    name: str
    board: str
    memory_regions: Dict[str, MemoryRegion]


class HypervisorMemory(BaseModel):
    physical_start_addr: HexInt
    size: ByteSize


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
    address: int
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


PCIDevice = List[str]  # TODO: Implement PCI Device


class CellConfig(BaseModel):
    type: str
    name: str
    vpci_irq_base: int
    flags: List[str]  # FIXME: Use list of ENUM

    hypervisor_memory: HypervisorMemory
    debug_console: DebugConsole
    platform_info: PlatformInfo
    cpus: IntegerList
    memory_regions: Dict[str, Union[MemoryRegion, ShMemNetRegion]]
    irqchips: Dict[str, IRQChip]
    pci_devices: Dict[str, PCIDevice]


class CommunicationConfig(BaseModel):
    pass


class JailhouseConfig(BaseModel):
    cells: Dict[str, CellConfig]
    communication: Optional[Dict[str, CommunicationConfig]] = None


if __name__ == "__main__":
    import yaml
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.safe_load(yaml_file)
        pprint(yaml_dict, indent=2)

        board = Board(**yaml_dict)
        pprint(board, indent=2)
