# type: ignore
import json
import logging
from collections import OrderedDict
from pathlib import Path, PosixPath
from typing import Any, Dict, List, Tuple

from autojail.model.board import ParentClockInfo

from ..model import GIC, Board, Clock, MemoryRegion
from ..utils.draw_tree import draw_tree
from .device_tree import DeviceTreeExtractor


class BoardInfoExtractor:
    def __init__(self, name: str, board: str, data_root: str) -> None:
        self.name = name
        self.board = board
        self.data_root = Path(data_root)
        self.logger = logging.getLogger(__name__)

    def read_iomem(self, filename: PosixPath) -> Dict[str, MemoryRegion]:
        with open(filename, "r") as iomem_info:
            start_addr = 0
            end_addr = 0
            size_calculated = 0
            temp = 0
            compare_count = 2
            physical_start_addr = []

            size = []
            memory_regions: List[Any] = []
            res = 1
            res2 = 1
            mem_flags = "JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64"
            ram_flags = "JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_EXECUTE"
            for x in iomem_info:
                start_addr, temp, *rest = x.split("-", 1)
                temp = temp.strip()
                start_addr = start_addr.strip()
                physical_start_addr.append(start_addr)
                end_addr, temp = temp.split(":", 1)

                end_addr = end_addr.split(" ", 1)[0]
                size_calculated = int(end_addr, 16) - int(start_addr, 16) + 1
                size.append(size_calculated)
                temp = temp.strip()
                res = any(temp in sublist for sublist in memory_regions)
                compare_count = 1
                if res == 0:
                    memory_regions.append(temp)
                else:
                    while res != 0:
                        if res != 0:
                            compare_count += 1
                            if (
                                temp[-1].isdigit() == 1
                                or temp[-2].isdigit() == 1
                                and temp[-2] == "_"
                                or temp[-3] == "_"
                            ):
                                temp = temp.rsplit("_", 1)[0]
                                temp = temp.strip() + "_" + str(compare_count)
                            else:
                                temp = temp.strip() + "_" + str(compare_count)
                            res2 = any(
                                temp in sublist for sublist in memory_regions
                            )
                            if res2 == 0:
                                memory_regions.append(temp)

                                res = 0
                            else:
                                res = 1
        mem_regs = {}

        for i, name in enumerate(memory_regions):
            if (
                ("System RAM" in name)
                or ("Kernel Code" in name)
                or ("reserved" in name)
            ):
                flags = (ram_flags,)
            else:
                flags = (mem_flags,)

            allocatable = False
            if "System RAM" in name:
                allocatable = True

            memory_region = MemoryRegion(
                physical_start_addr=int(physical_start_addr[i], 16),
                virtual_start_addr=int(physical_start_addr[i], 16),
                size=size[i],
                flags=flags,
                allocatable=allocatable,
            )
            mem_regs[name] = memory_region

        # FIXME: it would be better to check if some regions are part of an outer region and merge accordingly
        to_delete = []
        for k in mem_regs:
            if k.startswith("reserved") or k.startswith("Kernel"):
                to_delete.append(k)

        for k in to_delete:
            del mem_regs[k]

        return mem_regs

    def read_getconf_out(self, getconf_path: Path) -> int:
        # Return values
        pagesize = 4096

        if getconf_path.exists():
            with getconf_path.open() as getconf_data:
                for line in getconf_data.readlines():
                    line = line.strip()
                    splitted_line = line.split()
                    if len(splitted_line) == 2:
                        name, value = splitted_line
                        if name == "PAGESIZE" or name == "PAGE_SIZE":
                            pagesize = int(value)
        return pagesize

    def extract_cpuinfo(self) -> List[Any]:
        path = self.data_root / "proc" / "cpuinfo"

        cpuinfo = []

        with path.open() as f:
            current_cpu: Dict[str, Any] = {}
            started = False
            for line in f:
                line = line.strip()

                if line == "":
                    if current_cpu:
                        cpuinfo.append(current_cpu)
                        current_cpu = {}
                        started = False

                if line.startswith("processor"):
                    started = True

                if started is False:
                    continue

                key, val = line.split(":")

                key = key.strip()
                val = val.strip()
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass

                current_cpu[key] = val

        if current_cpu:
            cpuinfo.append(current_cpu)

        return cpuinfo

    def extract_clock_mapping(self) -> Dict[str, ParentClockInfo]:
        clock_mapping_fname = (
            self.data_root / "sys" / "kernel" / "debug" / "autojail" / "clocks"
        )
        if not clock_mapping_fname.exists():
            self.logger.warning("Could not find %s", str(clock_mapping_fname))
            return {}

        with clock_mapping_fname.open() as f:
            clock_mapping_json = f.read()
            clock_mapping_data = json.loads(clock_mapping_json)

        clock_mapping_result = {}
        for k, v in clock_mapping_data.items():
            clock_mapping_result[k] = [ParentClockInfo(**item) for item in v]

        return clock_mapping_result

    def extract_clocks(self):
        clock_tree_fname = (
            self.data_root / "sys" / "kernel" / "debug" / "clk" / "clk_dump"
        )
        if not clock_tree_fname.exists():
            self.logger.warning("Could not find %s", str(clock_tree_fname))
            return {}

        clock_tree_data = {}
        with clock_tree_fname.open() as clock_tree_file:
            clock_tree_json = clock_tree_file.read()
            try:
                clock_tree_data = json.loads(clock_tree_json)
            except json.JSONDecodeError:
                self.logger.warning(
                    "Could not decode clk_dump trying to work arround json bug"
                )
                try:
                    clock_tree_json = clock_tree_json.replace(
                        r'"duty_cycle"', r',"duty_cycle"'
                    )
                    clock_tree_data = json.loads(clock_tree_json)
                except json.JSONDecodeError as e:
                    self.logger.critical(
                        "Could not parse clk_dump with json bug workaround"
                    )
                    self.logger.critical(str(e))

        worklist = [(k, v, None) for k, v in clock_tree_data.items()]
        clocks = {}
        while worklist:
            name, data, parent = worklist.pop()
            clock_data = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    worklist.append((key, value, name))
                else:
                    clock_data[key] = value

            clock = Clock(name=name, **clock_data, parent=parent)
            clocks[name] = clock
            if parent is not None:
                clocks[parent].derived_clocks[name] = clock

        return {k: v for k, v in clocks.items() if not v.parent}

    def extract_from_devicetree(
        self, memory_regions: Dict[str, MemoryRegion]
    ) -> Tuple[OrderedDict, List[GIC]]:
        extractor = DeviceTreeExtractor(
            self.data_root / "sys" / "firmware" / "devicetree" / "base"
        )
        extractor.run()

        return (
            extractor.memory_regions,
            extractor.interrupt_controllers,
            extractor.stdout_path,
            {x.name: x for x in extractor.cpus},
            extractor.devices,
        )

    def _merge_memory_regions(self, regions):
        return regions[0]

    def _merge_memory_cpuinfo(self, cpuinfos):
        lengths = [len(info) for info in cpuinfos]
        for length in lengths:
            if length != lengths[0]:
                self.logger.warning(
                    "Length of cpuinfos does not match: %s",
                    ", ".join([str(len) for len in lengths]),
                )

        return cpuinfos[0]

    def extract(self) -> Board:
        memory_regions = self.read_iomem(self.data_root / "proc" / "iomem")

        cpuinfo = self.extract_cpuinfo()

        pagesize = self.read_getconf_out(self.data_root / "getconf.out")

        (
            memory_regions_dt,
            interrupt_controllers,
            stdout_path,
            cpuinfo_dt,
            devices,
        ) = self.extract_from_devicetree(memory_regions)

        clocks = self.extract_clocks()
        self.logger.info(
            "Extracted Clock Tree:\n%s",
            draw_tree(
                clocks.values(),
                lambda x: list(x.derived_clocks.values()),
                lambda x: f"{x.name}: {x.rate} Hz",
            ),
        )

        clock_mapping = self.extract_clock_mapping()

        cpuinfo = self._merge_memory_cpuinfo([cpuinfo_dt, cpuinfo])
        memory_regions = self._merge_memory_regions(
            [memory_regions_dt, memory_regions]
        )

        board = Board(
            name=self.name,
            board=self.board,
            memory_regions=memory_regions,
            pagesize=pagesize,
            interrupt_controllers=interrupt_controllers,
            cpuinfo=cpuinfo,
            stdout_path=stdout_path,
            clock_tree=clocks,
            devices=devices,
            clock_mapping=clock_mapping,
        )

        return board
