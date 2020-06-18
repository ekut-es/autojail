import logging

import tabulate

from .passes import BasePass

from ..model import MemoryRegion


class PrepareMemoryRegionsPass(BasePass):
    """ Prepare memory regions by merging  regions from Extracted Board Info and Cell Configuration"""

    def __init__(self):
        self.config = None
        self.board = None

    def __call__(self, board, config):
        self.board = board
        self.config = config

        for name, cell in self.config.cells.items():
            self._prepare_memory_regions(cell)

        return self.board, self.config

    def _prepare_memory_regions(self, cell):
        if cell.type != "root":
            return

        for name, memory_region in self.board.memory_regions.items():

            p_start = memory_region.physical_start_addr
            v_start = memory_region.virtual_start_addr
            p_end = memory_region.physical_start_addr
            v_end = memory_region.virtual_start_addr

            skip = False
            for cell_name, cell_region in cell.memory_regions.items():
                if not isinstance(cell_region, MemoryRegion):
                    continue

                if cell_region.physical_start_addr is not None:
                    if (
                        p_start >= cell_region.physical_start_addr
                        and p_start
                        < cell_region.physical_start_addr + cell_region.size
                    ):
                        skip = True

                    if (
                        p_end >= cell_region.physical_start_addr
                        and p_end
                        < cell_region.physical_start_addr + cell_region.size
                    ):
                        skip = True

                if cell_region.virtual_start_addr is not None:
                    if (
                        v_start >= cell_region.virtual_start_addr
                        and v_start
                        < cell_region.virtual_start_addr + cell_region.size
                    ):
                        skip = True

                    if (
                        v_end >= cell_region.virtual_start_addr
                        and v_end
                        < cell_region.virtual_start_addr + cell_region.size
                    ):
                        skip = True

            if skip is True:
                continue

            cell.memory_regions[name] = memory_region


class FreeBlock:
    "Represents an unallocated chunk of memory"

    def __init__(self, start_addr, size):
        self.start_addr = start_addr
        self.size = size

    def __repr__(self):
        return f"FreeBlock(start_addr={hex(self.start_addr)},size={self.size})"


class AllocateMemoryPass(BasePass):
    def __init__(self):
        self.logger = logging.getLogger("autojail")
        self.config = None
        self.board = None
        self.root_cell = None
        self.freelist = []
        self.allocatable_regions = []

    def __call__(self, board, config):
        self.logger.info("Memory Allocator")

        self.board = board
        self.config = config
        self.root_cell = None

        for name, cell in self.config.cells.items():
            if cell.type == "root":
                self.root_cell = cell
                break

        self._build_freelist()
        self.logger.info("Free memory cells:")

        table = [
            [hex(b.start_addr), hex(b.start_addr + b.size), b.size]
            for b in self.freelist
        ]
        self.logger.info(
            tabulate.tabulate(table, headers=["Start", "End", "Size (Byte)"])
        )

        self._build_allocation_segments()
        self._reserve_preallocated_physical()
        self._allocate_physical()
        for name, cell in config.cells:
            self._preallocate_virtual(cell)
            self._allocate_virtual()

        return self.board, self.config

    def _build_freelist(self):
        temp_freelist = []
        for name, region in self.root_cell.memory_regions.items():
            if region.allocatable:
                new_block = FreeBlock(region.physical_start_addr, region.size)
                temp_freelist.append(new_block)
                self.allocatable_regions.append(region)

        temp_freelist.sort(key=lambda x: x.start_addr)

        last_segment = None
        for segment in temp_freelist:
            segments_fuseable = (
                last_segment is not None
                and last_segment.start_addr + last_segment.size
                == segment.start_addr
            )
            if segments_fuseable:
                last_segment.size += segment.size
            else:
                last_segment = segment
                self.freelist.append(segment)

    def _build_allocation_segments(self, key=lambda x: x.physical_start_addr):
        """ Group Memory Regions"""

        # Add hypervisor Memory
        self.logger.debug("building allocatable regions")

    def _allocate_memory(self):
        pass
