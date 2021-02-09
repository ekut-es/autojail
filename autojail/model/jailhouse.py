# FIXME:  Dicts should be replaced by OrderedDict when 3.6 support is dropped
from typing import Dict, List, Optional, Union

from pydantic import BaseModel
from pydantic.networks import IPvAnyInterface, IPvAnyNetwork
from typing_extensions import Literal

from .board import (
    Board,
    DeviceMemoryRegion,
    HypervisorMemoryRegion,
    MemoryRegion,
    ShMemNetRegion,
)
from .datatypes import ByteSize, ExpressionInt, HexInt, IntegerList


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
    def pin_bitmap(self) -> List[str]:
        SIZE = 32  # noqa
        count = 0

        res = []

        update = None
        store = None
        init: Union[None, str, int] = None

        pin_base = self.pin_base

        if len(self.interrupts) > 5:

            def update(current_item, irq, count):
                # print("Update:", irq, pin_base, count)
                return current_item | 1 << (irq - (pin_base + count))

            def store(item):
                return "0x%x" % item

            init = 0
        else:

            def update(current_item, irq, count):
                res = (
                    current_item
                    + ("" if not current_item else " | ")
                    + f"1 << ({irq} - {pin_base + count})"
                )
                return res

            def store(x):
                return "0x0" if x == "" else x

            init = ""

        current_item = init
        for irq in self.interrupts:
            while irq - pin_base >= count + SIZE:
                res.append(store(current_item))
                current_item = init
                count += SIZE

            current_item = update(current_item, irq, count)

        if current_item:
            res.append(store(current_item))

        while len(res) < 4:
            res.append(store(init))

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
    memory_regions: List[DeviceMemoryRegion] = []

    @property
    def bus(self) -> int:
        return (int(self.bdf) >> 8) & 0xFF  # 8 Bits

    @property
    def device(self) -> int:
        return (int(self.bdf) >> 3) & 0x1F  # 5 Bits

    @property
    def function(self) -> int:
        return int(self.bdf) & 0x7  # 3 Bits


class CellConfig(BaseModel):
    type: str
    name: str
    vpci_irq_base: Optional[ExpressionInt]
    flags: List[str] = []

    hypervisor_memory: Optional[HypervisorMemoryRegion]
    debug_console: Union[str, DebugConsole]
    platform_info: Optional[PlatformInfo]
    cpus: Optional[IntegerList]
    memory_regions: Optional[
        Dict[str, Union[str, ShMemNetRegion, MemoryRegion, DeviceMemoryRegion]]
    ] = {}
    irqchips: Optional[Dict[str, IRQChip]] = {}
    pci_devices: Optional[Dict[str, PCIDevice]] = {}


class ShmemConfig(BaseModel):
    protocol: Literal[
        "SHMEM_PROTO_UNDEFINED", "SHMEM_VIRTIO_BACK", "SHMEM_PROTO_VETH"
    ]
    peers: List[str]
    common_output_region_size: Optional[ByteSize]
    per_device_region_size: Optional[ByteSize]


class InterfaceConfig(BaseModel):
    addresses: List[IPvAnyInterface]
    interface: Optional[str] = None


class ShmemConfigNet(ShmemConfig):
    protocol: Literal["SHMEM_PROTO_VETH"]
    renderer: Literal["interfaces"] = "interfaces"
    network: Union[List[IPvAnyNetwork], Dict[str, InterfaceConfig]] = {}


class JailhouseConfig(BaseModel):
    cells: Dict[str, CellConfig]
    shmem: Optional[Dict[str, Union[ShmemConfigNet, ShmemConfig]]] = None

    @property
    def root_cell(self) -> CellConfig:
        for cell in self.cells.values():
            if cell.type == "root":
                return cell

        raise Exception("No root cell found")


if __name__ == "__main__":
    import sys
    from pprint import pprint

    import yaml

    with open(sys.argv[1]) as yaml_file:
        yaml_dict = yaml.safe_load(yaml_file)
        pprint(yaml_dict, indent=2)  # noqa

        board = Board(**yaml_dict)
        pprint(board, indent=2)  # noqa
