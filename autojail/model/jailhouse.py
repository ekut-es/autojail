from pydantic import BaseModel
from typing import OrderedDict, List, Union, Optional

from .datatypes import ByteSize, ExpressionInt, IntegerList, HexInt
from .board import MemoryRegion, HypervisorMemoryRegion, ShMemNetRegion, Board


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
    pci_mmconfig_end_bus: HexInt
    pci_is_virtual: bool
    pci_domain: int
    pci_mmconfig_base: Optional[HexInt]
    arch: Union[PlatformInfoArm, PlatformInfoX86, None] = None


class IRQChip(BaseModel):
    address: HexInt
    pin_base: int
    interrupts: IntegerList

    @property
    def pin_bitmap(self) -> List[int]:
        SIZE = 32  # noqa

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
    vpci_irq_base: Optional[ExpressionInt]
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
