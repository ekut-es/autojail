from pydantic import BaseModel, ByteSize
from typing import Dict, List, Union


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


class ShMemNet:
    start_addr: int
    device_id: int


class Board(BaseModel):
    name: str
    board: str
    memory_regions: Dict[str, Union[MemoryRegion, SHMemoryRegion]]
    # memory_regions: Dict[str, MemoryRegion]


class CellYML:
    base_infos: dict
    hypervisor_memory: dict
    debug_console: dict
    platform_info: dict
    cpus: List[int]
    additional_memory_regions: dict
    irqchips: dict
    pci_devices: dict
    sh_mem_net: dict


class BaseInfos:
    Type: str
    name: str
    vpci_irq_base: int
    flags: List[str]  # FIXME: Use list of ENUM


class HypervisorMemory:
    physical_start_addr: int
    size: ByteSize


class DebugConsole:
    adress: str
    size: int
    Type: str
    flags: List[str]  # FIXME: Use list of ENUM


class PlatformInfo:
    pci_mmconfig_base: int
    pci_mmconfig_end_bus: int
    pci_is_virtual: int
    pci_domain : int
    arm : List[str]


class IRQChips:
    adress: int
    pin_base: int
    interrupts : List[int]


class PCIDevices:
    demo: List[str]
    networking: List[str]


class SHMemoryRegionTest:
    physical_start_addr: int
    virtual_start_addr: int
    size: ByteSize
    flags: List[str]  # FIXME: Use list of ENUM

if __name__ == "__main__":
    import yaml
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.load(yaml_file)
        pprint(yaml_dict, indent=2)

        board = Board(**yaml_dict)
        pprint(board, indent=2)
