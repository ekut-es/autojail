import os
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path
from tempfile import mktemp
from typing import Any, List, MutableMapping, Set, Tuple, Union

import fdt
import tabulate
from dataclasses import dataclass, field
from fdt.items import Node

from autojail.model.board import Interrupt

from ..model import (
    CPU,
    GIC,
    Device,
    DeviceData,
    DeviceMemoryRegion,
    MemoryRegion,
    MemoryRegionData,
)
from ..model.datatypes import ByteSize, IntegerList
from ..utils.logging import getLogger

SIZE_128K = 128 * 2 ** 10


@dataclass
class RangeEntry:
    start: int
    global_start: int
    size: int


@dataclass
class WalkerState:
    node: Any
    address_cells: int = 1
    size_cells: int = 1
    ranges: List[RangeEntry] = field(default_factory=list)
    memory_mapped: bool = True

    def translate_addr(self, addr: int) -> int:
        """Translate address to global address"""
        for range in self.ranges:
            offset = addr - range.start
            if offset >= 0 and offset < range.size:
                return offset + range.global_start

        return addr

    def munge(self, range: List[int]) -> int:
        res = 0
        for i, v in enumerate(reversed(range)):
            res += 2 ** (32 * i) * v
        return res

    def parse_range(self, range: List[int]) -> Tuple[int, int, int]:
        start = self.munge(range[: self.address_cells])
        size = self.munge(
            range[self.address_cells : self.address_cells + self.size_cells]
        )

        return start, size, self.address_cells + self.size_cells


class DeviceTreeExtractor:
    def __init__(self, dt: Union[str, Path], pagesize: int = 4096) -> None:
        dt_path = Path(dt)
        if dt_path.is_dir():
            temp_file = mktemp(suffix=".dtb")
            try:
                subprocess.run(
                    f"dtc -I fs -O dtb -o {temp_file} {str(dt_path)}".split(),
                    stderr=subprocess.DEVNULL,
                )

                with open(temp_file, "rb") as f:
                    self.fdt = fdt.parse_dtb(f.read())
            finally:
                pass
        else:
            with dt_path.open("rb") as f:
                self.fdt = fdt.parse_dtb(f.read())

        self.aliases: MutableMapping[str, str] = OrderedDict()
        self.aliases_reversed: MutableMapping[str, List[str]] = defaultdict(
            list
        )  # type: ignore
        self.handles: MutableMapping[str, str] = OrderedDict()
        self.memory_regions: MutableMapping[
            str, MemoryRegionData
        ] = OrderedDict()
        self.devices: MutableMapping[str, DeviceData] = OrderedDict()
        self.interrupt_controllers: List[GIC] = []
        self.stdout_path: str = ""
        self.cpus: List[CPU] = []

        self.logger = getLogger()

    def _extract_stdout(self) -> None:
        if self.fdt.exist_property("stdout-path", "/chosen"):
            stdout_property = self.fdt.get_property("stdout-path", "/chosen")
            self.stdout_path = str(stdout_property.value)

    def _extract_aliases(self) -> None:
        if self.fdt.exist_node("/aliases"):
            aliases_node = self.fdt.get_node("/aliases")
            for prop in sorted(aliases_node.props, key=lambda x: x.name):
                self.aliases[prop.name] = prop.value
                self.aliases_reversed[prop.value].append(prop.name)

    def _is_simple_bus(self, node: Node) -> bool:
        compatible = node.get_property("compatible")
        if (compatible is not None) and ("simple-bus" in compatible.value):
            size_cells = node.get_property("#size-cells")
            # FIXME: this is a simple workaround for the
            #       target data
            if size_cells.value != 0:
                return True
        return False

    def _is_dwc_usb(self, node: Node) -> bool:
        compatible = node.get_property("compatible")
        if compatible is not None and "xlnx,zynqmp-dwc3" in compatible.value:
            return True

        return False

    def _is_mmapped_bus(self, node: Node) -> bool:
        if (
            self._is_simple_bus(node)
            or node.name == "/"
            or node.name == "reserved-memory"
            or self._is_dwc_usb(node)
        ):
            return True
        return False

    def _current_cells(self, state: WalkerState, node: Node) -> Tuple[int, int]:
        address_cells = node.get_property("#address-cells")
        if address_cells is None:
            address_cells = state.address_cells
        else:
            address_cells = address_cells.value

        size_cells = node.get_property("#size-cells")
        if size_cells is None:
            size_cells = state.size_cells
        else:
            size_cells = size_cells.value

        return address_cells, size_cells

    def _parse_cell(self, data: List[int]) -> int:
        result = 0

        for num, val in enumerate(reversed(data)):
            result += 2 ** (32 * num) * val

        return result

    def _calc_ranges(
        self,
        current_state: WalkerState,
        node: Node,
        address_cells: int,
        size_cells: int,
    ) -> List[RangeEntry]:
        ranges = node.get_property("ranges")
        if ranges is not None and getattr(ranges, "value", None) is not None:
            values = list(ranges)
            parent_cells = current_state.address_cells

            entry_size = address_cells + parent_cells + size_cells
            num_entries = len(values) // entry_size

            res = []

            for entry_num in range(num_entries):
                start = entry_num * entry_size
                end = start + address_cells
                current_addr = self._parse_cell(values[start:end])

                start = end
                end = start + parent_cells
                parent_addr = self._parse_cell(values[start:end])

                start = end
                end = start + size_cells
                size = self._parse_cell(values[start:end])

                parent_addr = current_state.translate_addr(parent_addr)

                self.logger.info(
                    f"{hex(parent_addr)} -- {node.name} --> {hex(current_addr)} {ByteSize(size).human_readable()}"
                )

                res.append(
                    RangeEntry(
                        start=current_addr, global_start=parent_addr, size=size
                    )
                )
            return res

        return list(current_state.ranges)

    def _insert_named_region(
        self, orig_name: str, region: MemoryRegionData
    ) -> None:
        count = 0
        name = orig_name
        region.name = orig_name
        while name in self.memory_regions:
            name = orig_name + "." + str(count)
            count += 1

        self.memory_regions[name] = region

    def _insert_named_device(self, orig_name: str, device: DeviceData):
        count = 0
        name = orig_name
        device.name = orig_name
        while name in self.devices:
            name = orig_name + "." + str(count)
            count += 1

        self.devices[name] = device

    def _add_memreserve(self, node: Node) -> None:
        memreserve = node.get_property("memreserve")
        if memreserve is not None:
            region = MemoryRegion(
                virtual_start_addr=memreserve[0],
                physical_start_addr=memreserve[0],
                size=memreserve[1],
                flags=["MEM_READ", "MEM_WRITE", "MEM_EXECUTE", "MEM_DMA"],
            )

            self._insert_named_region("mem_reserve", region)

    def _extract_interrupt_controller(
        self, node, state, compatible, reg, device_type, interrupts
    ):
        self.logger.info("Handling interrupt controller %s", node.name)
        # FIXME: some of the version two's are v1
        gic_versions = {
            "arm,arm11mp-gic": 2,
            "arm,cortex-a15-gic": 2,
            "arm,cortex-a7-gic": 2,
            "arm,cortex-a5-gic": 2,
            "arm,cortex-a9-gic": 2,
            "arm,eb11mp-gic": 2,
            "arm,gic-400": 2,
            "arm,pl390": 2,
            "arm,tc11mp-gic": 2,
            "nvidia,tegra210-agic": 2,
            "qcom,msm-8660-qgic": 2,
            "qcom,msm-qgic2": 2,
            "qcom,msm8996-gic-v3": 3,
            "arm,gic-v3": 3,
        }
        gic_version = None
        for compatible_item in compatible:
            if compatible_item in gic_versions:
                gic_version = gic_versions[compatible_item]

        if gic_version is None:
            self.logger.warning("Could not find GIC version for %s", node.path)
            self._extract_mmaped_device(
                node, state, compatible, reg, device_type, interrupts
            )
            return

        if interrupts is None:
            self.logger.warning(
                "Could not get maintenance interrupt for %s", node.path
            )
            return

        maintenance_irq = interrupts[1] + 16

        gicd_base, gicc_base, gich_base, gicv_base, gicr_base = (
            0,
            0,
            0,
            0,
            0,
        )

        next_pos = 0
        gic_addresses = []
        gic_sizes = []
        while next_pos < len(reg):
            start, size, offset = state.parse_range(reg[next_pos:])
            next_pos += offset
            start = state.translate_addr(start)
            gic_addresses.append(start)
            gic_sizes.append(size)

        if gic_version <= 2:
            try:
                gicd_base, gicc_base, gich_base, gicv_base = gic_addresses
                gicd_size, gicc_size, gich_size, gicv_size = gic_sizes

                # Have a look at drivers/irqchip/irq-gic.o:1359
                # This actually seems to be the logic
                if gicc_size == SIZE_128K:
                    gicc_base = gicc_base + 0xF000
                    gicv_base = gicv_base + 0xF000

            except Exception:
                self.logger.warning(
                    "GIC %s does not have virtualization extensions", node.name,
                )
        else:
            (
                gicd_base,
                gicr_base,
                gicc_base,
                gich_base,
                gicv_base,
            ) = gic_addresses

        gic = GIC(
            gic_version=gic_version,
            compatible=list(compatible),
            maintenance_irq=maintenance_irq,
            gicd_base=gicd_base,
            gicc_base=gicc_base,
            gich_base=gich_base,
            gicv_base=gicv_base,
            gicr_base=gicr_base,
            interrupts=[],
        )
        self.interrupt_controllers.append(gic)

    def _extract_interrupts(self, interrupts):
        extracted_interrupts = []
        if interrupts is not None:
            if len(interrupts) % 3 == 0:
                for start in range(len(interrupts) // 3):
                    start = start * 3
                    int_type, int_num, int_flags = interrupts[start : start + 3]
                    interrupt = Interrupt(
                        type=int_type, num=int_num, flags=int_flags
                    )
                    extracted_interrupts.append(interrupt)

        return extracted_interrupts

    def _extract_memory(
        self, node, state, compatible, reg, device_type, interrupts
    ) -> None:
        if not state.memory_mapped:
            return None
        if reg is None:
            return None

        next_pos = 0
        while next_pos < len(reg):
            start, size, offset = state.parse_range(reg[next_pos:])
            next_pos += offset
            start = state.translate_addr(start)
            region = MemoryRegion(
                physical_start_addr=start,
                virtual_start_addr=start,
                size=size,
                flags=["MEM_READ", "MEM_WRITE", "MEM_EXECUTE"],
            )

            if device_type and device_type.value == "memory":
                region.allocatable = True

            name = node.name
            self._insert_named_region(name, region)

    def _extract_mmaped_device(
        self, node, state, compatible, reg, device_type, interrupts
    ) -> None:
        self.logger.info("Extracting mmaped device %s", node.name)
        if reg is None:
            self._extract_unmapped_device(node, state)
            return

        clocks = node.get_property("clocks")
        clocks = list(clocks) if clocks else []

        clock_names = node.get_property("clock-names")
        clock_names = list(clock_names) if clock_names else []

        clock_output_names = node.get_property("clock-output-names")
        clock_output_names = (
            list(clock_output_names) if clock_output_names else []
        )

        clock_cells = node.get_property("#clock-cells")
        clock_cells = int(clock_cells[0]) if clock_cells else 0

        phandle = node.get_property("phandle")

        device_registers = []

        next_pos = 0
        while next_pos < len(reg):
            start, size, offset = state.parse_range(reg[next_pos:])
            next_pos += offset
            start = state.translate_addr(start)
            region = MemoryRegion(
                physical_start_addr=start,
                virtual_start_addr=start,
                size=size,
                flags=[
                    "MEM_READ",
                    "MEM_WRITE",
                    "MEM_IO",
                    "MEM_IO_8",
                    "MEM_IO_16",
                    "MEM_IO_32",
                    "MEM_IO_64",
                ],
            )
            device_registers.append(region)

        extracted_interrupts = self._extract_interrupts(interrupts)

        path = os.path.join(node.path, node.name)
        for device_register in device_registers:
            device = DeviceMemoryRegion(
                phandle=phandle[0] if phandle else None,
                physical_start_addr=device_register.physical_start_addr,
                virtual_start_addr=device_register.virtual_start_addr,
                size=device_registers[0].size,
                path=path,
                compatible=list(compatible),
                interrupts=extracted_interrupts,
                aliases=self.aliases_reversed[path],
                clock_names=clock_names,
                clock_cells=clock_cells,
                clock_output_names=clock_output_names,
                clocks=clocks,
                flags=[
                    "MEM_READ",
                    "MEM_WRITE",
                    "MEM_IO",
                    "MEM_IO_8",
                    "MEM_IO_16",
                    "MEM_IO_32",
                    "MEM_IO_64",
                ],
            )

            name = node.name
            self._insert_named_region(name, device)
            self._insert_named_device(name, device)

        if len(device_registers) != 1:
            self.logger.warning(
                "Standard device has more than one register %s", node.name
            )

    def _extract_unmapped_device(self, node: Node, state: WalkerState):

        self.logger.info("Extracting unmapped device %s", node.name)

        clocks = node.get_property("clocks")
        clocks = list(clocks) if clocks else []

        clock_names = node.get_property("clock-names")
        clock_names = list(clock_names) if clock_names else []

        clock_output_names = node.get_property("clock-output-names")
        clock_output_names = (
            list(clock_output_names) if clock_output_names else []
        )

        clock_cells = node.get_property("#clock-cells")
        clock_cells = int(clock_cells[0]) if clock_cells else 0

        phandle = node.get_property("phandle")

        compatible = node.get_property("compatible")
        compatible = list(compatible) if compatible else []

        extracted_interrupts = self._extract_interrupts(
            node.get_property("interrupts")
        )

        device = Device(
            clocks=clocks,
            clock_names=clock_names,
            clock_output_names=clock_output_names,
            clock_cells=clock_cells,
            phandle=phandle[0] if phandle else None,
            path=node.path + "/" + node.name,
            compatible=compatible,
            interrupts=extracted_interrupts,
        )
        self._insert_named_device(node.name, device)

    def _extract_device(self, node: Node, state: WalkerState) -> None:

        compatible = node.get_property("compatible")
        reg = node.get_property("reg")
        device_type = node.get_property("device_type")
        interrupts = node.get_property("interrupts")

        if (compatible and "memory" in compatible.data) or compatible is None:
            self._extract_memory(
                node, state, compatible, reg, device_type, interrupts
            )

        elif device_type and device_type.value == "cpu":
            self._extract_cpu(node)
            return

        elif node.get_property("interrupt-controller"):
            self._extract_interrupt_controller(
                node, state, compatible, reg, device_type, interrupts
            )

        else:
            if state.memory_mapped:
                self._extract_mmaped_device(
                    node, state, compatible, reg, device_type, interrupts
                )
            else:
                self._extract_unmapped_device(node, state)

    def _walk_tree(self) -> None:
        worklist = []

        worklist.append(WalkerState(self.fdt.root))

        while worklist:
            current_state = worklist.pop()

            node = current_state.node

            self._add_memreserve(node)
            self._extract_device(node, current_state)

            new_address_cells, new_size_cells = self._current_cells(
                current_state, node
            )

            if self._is_mmapped_bus(node) and current_state.memory_mapped:
                new_ranges = self._calc_ranges(
                    current_state, node, new_address_cells, new_size_cells
                )

                for child in node.nodes:
                    worklist.append(
                        WalkerState(
                            child,
                            address_cells=new_address_cells,
                            size_cells=new_size_cells,
                            ranges=new_ranges,
                        )
                    )
            else:
                # All entries that are not identifiable as memory mapped busses are handled as external
                for child in node.nodes:
                    worklist.append(
                        WalkerState(
                            child,
                            address_cells=new_address_cells,
                            size_cells=new_size_cells,
                            ranges=[],
                            memory_mapped=False,
                        )
                    )

    def _extract_cpu(self, node):
        name = node.name
        num = node.get_property("reg")[0]
        compatible = node.get_property("compatible").value
        enable_method = node.get_property("enable-method").value
        next_level_cache = None

        # node.get_property('next-level-cache')

        cpu = CPU(
            name=name,
            num=num,
            compatible=compatible,
            enable_method=enable_method,
            next_level_cache=next_level_cache,
        )
        self.cpus.append(cpu)

    def _add_interrupts(self) -> None:
        interrupts: Set[int] = set()
        for device in self.devices.values():
            interrupts = interrupts.union(
                set(
                    (
                        interrupt.to_jailhouse()
                        for interrupt in getattr(device, "interrupts", [])
                    )
                )
            )

        interrupt_list = list(sorted(interrupts))

        for controller in self.interrupt_controllers:
            controller.interrupts = IntegerList.validate(interrupt_list)

    def _summarize(self) -> None:
        table = []
        for name, region in sorted(
            self.memory_regions.items(), key=lambda x: x[1].physical_start_addr
        ):

            assert region.physical_start_addr is not None
            assert region.size is not None

            table.append(
                (
                    name,
                    hex(region.physical_start_addr),
                    hex(region.physical_start_addr + region.size),
                    region.size.human_readable(),
                    ",".join(
                        (
                            str(x.to_jailhouse())
                            for x in getattr(region, "interrupts", [])
                        )
                    ),
                    getattr(region, "path", ""),
                )
            )

        self.logger.info("Memory Regions from Device Tree")
        self.logger.info(
            "\n%s",
            tabulate.tabulate(
                table,
                headers=[
                    "Name",
                    "Start",
                    "End",
                    "Size",
                    "Interrupts (SPI)",
                    "Path",
                ],
            ),
        )

        interrupt_table = []
        for controller in self.interrupt_controllers:
            interrupt_table.append(
                (
                    controller.maintenance_irq,
                    hex(controller.gicd_base),
                    hex(controller.gicc_base),
                    hex(controller.gich_base),
                    hex(controller.gicv_base),
                    hex(controller.gicr_base),
                    str(min(controller.interrupts))
                    + "-"
                    + str(max(controller.interrupts)),
                )
            )

        self.logger.info("")
        self.logger.info("Extracted interrupt controller:")
        self.logger.info(
            "\n%s",
            tabulate.tabulate(
                interrupt_table,
                headers=[
                    "mIRQ",
                    "GICD",
                    "GICC",
                    "GICH",
                    "GICV",
                    "GICR",
                    "Interrupts",
                ],
            ),
        )

        cpu_table = []
        for cpu in self.cpus:
            cpu_table.append(
                [
                    cpu.num,
                    cpu.name,
                    cpu.compatible,
                    cpu.enable_method,
                    cpu.next_level_cache
                    if cpu.next_level_cache is not None
                    else "--",
                ]
            )
        self.logger.info("")
        self.logger.info("Extracted CPUs:")
        self.logger.info(
            "\n%s",
            tabulate.tabulate(
                cpu_table,
                headers=[
                    "Num",
                    "Name",
                    "Compatible",
                    "Enable Method",
                    "Next Level Cache",
                ],
            ),
        )

        self.logger.info("stdout-path: %s", self.stdout_path)

    def run(self) -> None:
        self._extract_stdout()
        self._extract_aliases()
        self._walk_tree()
        self._add_interrupts()

        self.memory_regions = OrderedDict(
            sorted(
                self.memory_regions.items(),
                key=lambda x: (x[1].physical_start_addr, x[0]),
            )
        )

        self.cpus.sort(key=lambda x: x.num)

        self._summarize()
