import subprocess
from pathlib import Path
from typing import Any, List, Union
from tempfile import mktemp
from collections import OrderedDict

import fdt
import tabulate

from dataclasses import dataclass, field

from ..model import MemoryRegion, GIC
from ..model.datatypes import ByteSize
from ..utils.logging import getLogger


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

    def translate_addr(self, addr):
        """Translate address to global address"""
        for range in self.ranges:
            offset = addr - range.start
            if offset >= 0 and offset < range.size:
                return offset + range.global_start

        return addr

    def munge(self, range):
        res = 0
        for i, v in enumerate(reversed(range)):
            res += 2 ** (32 * i) * v
        return res

    def parse_range(self, range):
        start = self.munge(range[: self.address_cells])
        size = self.munge(
            range[self.address_cells : self.address_cells + self.size_cells]
        )

        return start, size, self.address_cells + self.size_cells


class DeviceTreeExtractor:
    def __init__(self, dt: Union[str, Path], pagesize=4096) -> None:
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
                print(temp_file)
                # Path(temp_file[1]).unlink()
        else:
            with dt_path.open("rb") as f:
                self.fdt = fdt.parse_dtb(f.read())

        self.aliases = OrderedDict()
        self.handles = OrderedDict()
        self.memory_regions = OrderedDict()
        self.interrupt_controllers = []

        self.logger = getLogger()

    def _extract_aliases(self):
        if self.fdt.exist_node("/aliases"):
            aliases_node = self.fdt.get_node("/aliases")
            for prop in aliases_node.props:
                self.aliases[prop.name] = prop.value

    def _is_simple_bus(self, node):
        compatible = node.get_property("compatible")
        if (compatible is not None) and ("simple-bus" in compatible.value):
            size_cells = node.get_property("#size-cells")
            # FIXME: this is a simple workaround for the
            #       target data
            if size_cells.value != 0:
                return True
        return False

    def _is_mmapped_bus(self, node):
        if self._is_simple_bus(node) or node.name == "/":
            return True
        return False

    def _current_cells(self, state, node):
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

    def _parse_cell(self, data):
        result = 0

        for num, val in enumerate(reversed(data)):
            result += 2 ** (32 * num) * val

        return result

    def _calc_ranges(self, current_state, node, address_cells, size_cells):
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

    def _add_memreserve(self, node):
        memreserve = node.get_property("memreserve")
        if memreserve is not None:
            region = MemoryRegion(
                virtual_start_addr=memreserve[0],
                physical_start_addr=memreserve[0],
                size=memreserve[1],
                flags=["MEM_READ", "MEM_WRITE", "MEM_EXECUTE"],
            )

            self._insert_named_region("memreserve", region)

    def _insert_named_region(self, orig_name, region):
        count = 0
        name = orig_name
        while name in self.memory_regions:
            name = orig_name + "." + str(count)
            count += 1

        self.memory_regions[name] = region

    def _extract_device(self, node, state):

        blacklist = ["vc_mem"]
        if node.name in blacklist:
            return

        compatible = node.get_property("compatible")
        reg = node.get_property("reg")

        if reg is None:
            return None

        device_type = node.get_property("device_type")
        interrupts = node.get_property("interrupts")

        if (compatible and compatible.value == "memory") or compatible is None:
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

        elif device_type and device_type.value == "cpu":
            # FIXME: Extract CPUs also from device tree
            return

        elif node.get_property("interrupt-controller"):
            print("Handling interrup controller", node.name)
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
                self.logger.warning(
                    "Could not find GIC version for %s", node.path
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

            if gic_version <= 2:
                try:
                    gicd_base = state.translate_addr(reg[0])
                    gicc_base = state.translate_addr(reg[2])
                    gich_base = state.translate_addr(reg[4])
                    gicv_base = state.translate_addr(reg[6])
                except IndexError:
                    self.logger.warning(
                        "GIC %s does not have virtualization extensions",
                        node.name,
                    )
            else:
                gicd_base = state.translate_addr(reg[0])
                gicr_base = state.translate_addr(reg[2])
                gicc_base = state.translate_addr(reg[4])
                gich_base = state.translate_addr(reg[6])
                gicv_base = state.translate_addr(reg[8])

            gic = GIC(
                gic_version=gic_version,
                maintenance_irq=maintenance_irq,
                gicd_base=gicd_base,
                gicc_base=gicc_base,
                gich_base=gich_base,
                gicv_base=gicv_base,
                gicr_base=gicr_base,
                interrupts=[],
            )
            self.interrupt_controllers.append(gic)

        else:
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

            extracted_interrupts = []
            if interrupts is not None:
                if len(interrupts) % 3 == 0:
                    for start in range(len(interrupts) // 3):
                        start = start * 3
                        int_type, int_num, int_meta = interrupts[
                            start : start + 3
                        ]
                        if int_type == 0:
                            extracted_interrupts.append(int_num)
            path = node.path + "/" + node.name
            for device_register in device_registers:
                device = MemoryRegion(
                    physical_start_addr=device_register.physical_start_addr,
                    virtual_start_addr=device_register.virtual_start_addr,
                    size=device_registers[0].size,
                    path=path,
                    compatible=compatible,
                    interrupts=extracted_interrupts,
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

            if len(device_registers) != 1:
                self.logger.warning(
                    "Standard device has more than one register %s", node.name
                )

    def _walk_tree(self):
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

            if self._is_mmapped_bus(node):
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

    def _add_interrupts(self):
        interrupts = set()
        for region in self.memory_regions.values():
            interrupts = interrupts.union(
                set(getattr(region, "interrupts", []))
            )

        interrupt_list = list(sorted(interrupts))

        for controller in self.interrupt_controllers:
            controller.interrupts = interrupt_list

    def _summarize(self):
        table = []
        for name, region in sorted(
            self.memory_regions.items(), key=lambda x: x[1].physical_start_addr
        ):
            table.append(
                (
                    name,
                    hex(region.physical_start_addr),
                    hex(region.physical_start_addr + region.size),
                    region.size.human_readable(),
                    ",".join(
                        (str(x) for x in getattr(region, "interrupts", []))
                    ),
                    getattr(region, "path", ""),
                )
            )

        self.logger.info("Memory Regions from Device Tree")
        self.logger.info(
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
            )
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
            )
        )

    def run(self):
        self._extract_aliases()
        self._walk_tree()
        self._add_interrupts()

        self._summarize()
