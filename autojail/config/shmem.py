# type: ignore

import copy
from typing import Optional, Tuple

from ..model import Board, JailhouseConfig, MemoryRegion, PCIDevice
from .passes import BasePass


class ConfigSHMemRegionsPass(BasePass):
    """Set flags for shmem regions according to global config"""

    def __init__(self) -> None:
        self.board: Optional[Board] = None
        self.config: Optional[JailhouseConfig] = None
        super().__init__()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self.board = board
        self.config = config

        self._regions_shmem_config()

        return self.board, self.config

    def _regions_shmem_config(self) -> None:
        """ set MEM_WRITE flags accordingly """
        assert self.config is not None
        assert self.board is not None

        if not self.config.shmem:
            return

        for name, shmem_config in self.config.shmem.items():
            for cell_name in shmem_config.peers:
                cell = self.config.cells[cell_name]
                assert cell.pci_devices is not None

                # offset 2, since mem_regions always
                # start with table_region and common_output_region
                dev_id = cell.pci_devices[name].shmem_dev_id
                assert dev_id is not None

                mem_region_name = f"{name}_{dev_id + 2}"

                assert cell.memory_regions is not None
                cell_output_region = cell.memory_regions[mem_region_name]

                def get_mem_region_index(cell, name):
                    ret = -1
                    index = 0

                    for region_name, _ in cell.memory_regions.items():
                        if region_name == name:
                            ret = index
                            break

                        index += 1

                    if ret == -1:
                        raise Exception(
                            f"Invalid cells.yaml, not a memory-region: {name}"
                        )

                    return ret

                first_mem_region_name = f"{name}_0"
                shmem_regions_start = get_mem_region_index(
                    cell, first_mem_region_name
                )
                cell.pci_devices[name].shmem_regions_start = shmem_regions_start

                new_cell_output_region = copy.copy(cell_output_region)
                new_cell_output_region.flags = copy.copy(
                    cell_output_region.flags
                )
                new_cell_output_region.flags.append("MEM_WRITE")

                cell.memory_regions[mem_region_name] = new_cell_output_region


class LowerSHMemPass(BasePass):
    """Generates per cell shmem regions and devices from global configuration"""

    def __init__(self) -> None:
        self.board: Optional[Board] = None
        self.config: Optional[JailhouseConfig] = None
        super().__init__()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self.board = board
        self.config = config

        self._create_vpci_base()
        self._lower_shmem_config()

        return self.board, self.config

    def _lower_shmem_config(self) -> None:
        assert self.config is not None
        assert self.board is not None
        if not self.config.shmem:
            return

        root_cell = None
        for cell_config in self.config.cells.values():
            if cell_config.type == "root":
                root_cell = cell_config
                break

        if not root_cell:
            raise Exception("A configuration needs to provide a root cell")

        if len(self.config.shmem) > 4:
            self.logger.warning(
                "Configuring more than 4 will need an adoption of the default device trees"
            )

        current_bdf = 0
        pci_domain = root_cell.platform_info.pci_domain

        for name, shmem_config in self.config.shmem.items():
            if shmem_config.protocol == "SHMEM_PROTO_VETH":
                if len(shmem_config.peers) != 2:
                    raise Exception(
                        "shmem-net devices must have exactly 2 peers"
                    )

            # create mem regions
            common_output_region_size = shmem_config.common_output_region_size
            per_device_region_size = shmem_config.per_device_region_size

            if not common_output_region_size:
                common_output_region_size = 0

            if not per_device_region_size:
                per_device_region_size = 0

            mem_regions = list()
            mem_regions_index = 0

            if shmem_config.protocol == "SHMEM_PROTO_VETH":
                common_output_region_size = 0
                per_device_region_size = self.board.pagesize

            table_region = MemoryRegion(
                size=0x1000,
                allocatable=False,
                flags=["MEM_READ"],
                next_region=f"{name}_{mem_regions_index+1}",
                shared=True,
            )
            mem_regions.append((f"{name}_{mem_regions_index}", table_region))
            mem_regions_index += 1

            common_output_region = MemoryRegion(
                size=common_output_region_size,
                allocatable=False,
                flags=["MEM_READ", "MEM_WRITE"],
                next_region=f"{name}_{mem_regions_index+1}",
                shared=True,
            )
            mem_regions.append(
                (f"{name}_{mem_regions_index}", common_output_region)
            )
            mem_regions_index += 1

            for _cell_name in shmem_config.peers:
                mem_region = MemoryRegion(
                    size=per_device_region_size,
                    allocatable=False,
                    flags=["MEM_READ", "MEM_ROOTSHARED"],
                    next_region=f"{name}_{mem_regions_index+1}",
                    shared=True,
                )
                mem_regions.append((f"{name}_{mem_regions_index}", mem_region))
                mem_regions_index += 1

            mem_regions[-1][1].next_region = None

            # add PCI device to each affected cell
            root_added = False
            current_device_id = 0

            for cell_name in shmem_config.peers:
                cell = self.config.cells[cell_name]
                if cell.type == "root":
                    root_added = True

                pci_dev = PCIDevice(
                    type="PCI_TYPE_IVSHMEM",
                    domain=pci_domain,
                    bdf=current_bdf,
                    bar_mask="IVSHMEM_BAR_MASK_INTX",
                    shmem_regions_start=-1,
                    shmem_dev_id=current_device_id,
                    shmem_peers=len(shmem_config.peers),
                    shmem_protocol=shmem_config.protocol,
                )
                pci_dev.memory_regions = mem_regions

                cell.pci_devices[name] = pci_dev
                cell.memory_regions.update(copy.deepcopy(mem_regions))

                # set interrupt pins
                intx_pin = current_bdf & 0x3
                intx_pin += cell.vpci_irq_base

                # FIXME: what happens when irqchips are manually configured
                root_irq_chip = list(root_cell.irqchips.values())[0]
                irq_chip = list(cell.irqchips.values())[0]

                irq_chip.interrupts.append(intx_pin)
                irq_chip.interrupts.sort()

                root_irq_chip.interrupts.append(intx_pin)
                root_irq_chip.interrupts.sort()

                current_device_id += 1

            if not root_added:
                root_cell.mem_regions.update(copy.deepcopy(mem_regions))

            current_bdf += 1

    def _create_vpci_base(self) -> None:
        assert self.config is not None
        assert self.board is not None
        if self.config.shmem is None:
            return

        used_interrupts = set()

        for cell in self.config.cells.values():
            for irqchip in cell.irqchips.values():
                for irq in irqchip.interrupts:
                    used_interrupts.add(irq)

        num_interrupts = dict()
        for shmem_config in self.config.shmem.values():
            for cell_name in shmem_config.peers:
                cell_name = self.config.cells[cell_name].name

                if cell_name not in num_interrupts:
                    num_interrupts[cell_name] = 0

                num_interrupts[cell_name] += 1

        for cell in self.config.cells.values():
            if cell.vpci_irq_base:
                for i in range(
                    cell.vpci_irq_base,
                    cell.vpci_irq_base + num_interrupts[cell.name],
                ):
                    used_interrupts.add(i)

        for cell in self.config.cells.values():
            if cell.vpci_irq_base is None:
                for i in range(32, max(used_interrupts) + 2):
                    sentinel = set(range(i, i + num_interrupts[cell.name]))

                    if not (used_interrupts & sentinel):
                        used_interrupts |= sentinel
                        cell.vpci_irq_base = i
                        continue

        for cell in self.config.cells.values():
            if cell.type == "root":
                for irqchip in cell.irqchips.values():
                    for irq in used_interrupts:
                        if irq not in irqchip.interrupts:
                            irqchip.interrupts.append(irq)

        self.logger.info("Infered vpci root interupts")
        for name, cell in self.config.cells.items():
            self.logger.info("%s: %s", name, cell.vpci_irq_base)
