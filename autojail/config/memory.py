import logging

import tabulate

from .passes import BasePass

from ..model import BaseMemoryRegion, ByteSize
from ..utils import SortedCollection


class MemoryBlock:
    "Represents a chunk of memory in the allocator"

    def __init__(self, start_addr, size):
        self.start_addr = start_addr
        self.size = size

    @property
    def end_addr(self):
        return self.start_addr + self.size

    def __repr__(self):
        return (
            f"MemoryBlock(start_addr={hex(self.start_addr)},size={self.size})"
        )

    def __lt__(self, other):
        if self.start_addr < other.start_addr:
            return True
        return False


class FreeList(SortedCollection):
    def __init__(self):
        super().__init__(key=lambda x: x.start_addr)

    def _overlap(self, block1, block2):
        if block2 < block1:
            block1, block2 = block2, block1

        if block1.end_addr >= block2.start_addr:
            return True
        return False

    def _sub(self, current_block, sub_block):
        """Remove overlapping parts of block at index"""

        if not self._overlap(current_block, sub_block):
            return

        if current_block in self:
            self.remove(current_block)

        if current_block.start_addr < sub_block.start_addr:
            new_size = sub_block.start_addr - current_block.start_addr
            if new_size > 0:
                self.insert(MemoryBlock(current_block.start_addr, new_size))

        if current_block.end_addr > sub_block.end_addr:
            new_size = current_block.end_addr - sub_block.end_addr
            if new_size > 0:
                self.insert(MemoryBlock(sub_block.end_addr, new_size))

    def insert(self, block: MemoryBlock):
        pred_block = self.find_le(block.start_addr)
        if pred_block and self._overlap(pred_block, block):
            self.remove(pred_block)
            diff = pred_block.end_addr - block.start_addr
            block.start_addr = pred_block.start_addr
            block.size = pred_block.size + block.size - diff

        succ_block = self.find_ge(block.start_addr)

        while succ_block and self._overlap(block, succ_block):
            self.remove(succ_block)
            diff = block.end_addr - succ_block.start
            block.size = block.size + succ_block.size - diff

            succ_block = self.find_ge(block.start_addr)

        super().insert(block)

    def _reserve(self, block):
        # FIXME: use binary search to find start
        for local_block in self:
            if self._overlap(local_block, block):
                self._sub(local_block, block)

    def reserve(self, start_addr, size):
        self._reserve(MemoryBlock(start_addr, size))


class AllocatorSegment:
    def __init__(self, name="unnaamed", memory_regions=None, sharer_names=None):
        self.name = name
        self.memory_regions = (
            memory_regions if memory_regions is not None else []
        )
        self.sharer_names = sharer_names if sharer_names is not None else []
        self.size = sum(r.size for r in self.memory_regions)

    @property
    def physical_start_addr(self):
        return self.memory_regions[0].physical_start_addr

    def set_physical_start_addr(self, addr):
        for region in self.memory_regions:
            region.physical_start_addr = addr
            addr += region.size

    def set_virtual_start_addr(self, addr):
        for region in self.memory_regions:
            region.virtual_start_addr = addr
            addr += region.size


class AllocateMemoryPass(BasePass):
    """Implements a simple MemoryAllocator for AutoJail"""

    def __init__(self):
        self.logger = logging.getLogger("autojail")
        self.config = None
        self.board = None
        self.root_cell = None
        self.freelist = FreeList()
        self.allocatable_regions = []

        self.unallocated_segments = []
        self.allocated_regions = []

    def __call__(self, board, config):
        self.logger.info("Memory Allocator")

        self.board = board
        self.config = config
        self.root_cell = None

        for cell in self.config.cells.values():
            if cell.type == "root":
                self.root_cell = cell
                break

        self._build_freelist()
        self._log_freelist(self.freelist, "Free memory cells:")

        self.unallocated_segments = self._build_unallocated_segments()

        self.logger.info("")
        self.logger.info("Unallocated physical segments: ")
        table = [
            [s.name, s.size, len(s.memory_regions), ",".join(s.sharer_names)]
            for s in self.unallocated_segments
        ]
        self.logger.info(
            tabulate.tabulate(
                table,
                headers=["Name", "Size (Byte)", "# Subregions", "Sharers"],
            )
        )

        self._preallocate_physical()
        self._log_freelist(
            self.freelist, "Free memory cells (after preallocation):"
        )

        self._allocate_physical()
        self._log_freelist(self.freelist, "Free Memory (after allocation)")

        for name, cell in config.cells.items():
            freelist_virtual = FreeList()
            vmem_size = 2 ** 32
            if self.board.virtual_address_bits > 32:
                vmem_size = 2 ** (self.board.virtual_address_bits - 1)
            freelist_virtual.insert(MemoryBlock(0, vmem_size))
            self._log_freelist(
                freelist_virtual, f"Initial free vmem of cell {name}"
            )

            freelist_virtual = self._preallocate_virtual(freelist_virtual, cell)
            self._log_freelist(
                freelist_virtual,
                f"Free vmem of cell {name} after preallocation",
            )

            unallocated_virtual = self._build_unallocated_segments_virtual(cell)
            self._allocate_virtual(freelist_virtual, unallocated_virtual)

            self._log_freelist(
                freelist_virtual, f"Free vmem of cell {name} after allocation",
            )

        return self.board, self.config

    def _log_freelist(self, freelist, message=""):

        self.logger.info("")
        if message:
            self.logger.info(message)

        table = [
            [
                hex(b.start_addr),
                hex(b.start_addr + b.size),
                ByteSize(b.size).human_readable(),
            ]
            for b in freelist
        ]
        self.logger.info(
            tabulate.tabulate(table, headers=["Start", "End", "Size (Byte)"])
        )

    def _build_freelist(self):
        for region in self.root_cell.memory_regions.values():
            if region.allocatable:
                new_block = MemoryBlock(region.physical_start_addr, region.size)
                self.freelist.insert(new_block)
                self.allocatable_regions.append(region)

    def _build_unallocated_segments(self, key=lambda x: x.physical_start_addr):
        """Group Memory Regions into Segments that are allocated continuously"""

        unallocated = []

        # Add cell memories
        self.logger.debug("building allocatable regions")
        for cell_name, cell in self.config.cells.items():
            for region_name, region in cell.memory_regions.items():
                if region.allocatable:
                    continue
                if key(region) is not None:
                    continue

                unallocated.append(
                    AllocatorSegment(
                        region_name, [region], sharer_names=[cell_name]
                    )
                )

        # Add hypervisor memories
        hypervisor_memory = self.root_cell.hypervisor_memory
        if hypervisor_memory.physical_start_addr is None:
            unallocated.append(
                AllocatorSegment(
                    "hypervisor_memory", [hypervisor_memory], ["hypervisor"]
                )
            )

        return unallocated

    def _build_unallocated_segments_virtual(self, cell):
        unallocated = []
        for name, region in cell.memory_regions.items():
            if region.virtual_start_addr is None:
                unallocated.append(AllocatorSegment(name, [region]))
        return unallocated

    def _preallocate_physical(self):
        for cell in self.config.cells.values():
            for memory_region in cell.memory_regions.values():
                if memory_region.allocatable:
                    continue
                if memory_region.physical_start_addr is not None:
                    self.freelist.reserve(
                        memory_region.physical_start_addr, memory_region.size
                    )

    def _preallocate_virtual(self, freelist, cell):
        for memory_region in cell.memory_regions.values():
            if memory_region.allocatable:
                continue
            if memory_region.virtual_start_addr is not None:
                freelist.reserve(
                    memory_region.virtual_start_addr, memory_region.size
                )

        return freelist

    def _find_next_fit(self, size, alignment=0, reverse=True, freelist=None):
        if freelist is None:
            freelist = self.freelist

        if reverse:
            freelist = reversed(freelist)

        for block in freelist:
            if block.size >= size:
                if reverse:
                    diff = block.size - size
                    return block.start_addr + diff
                return block.start_addr

        raise Exception(f"Could not find continuous Memory with size: {size}")

    def _allocate_physical(self):
        for unallocated_region in self.unallocated_segments:
            alignment = 0
            if unallocated_region.size % self.board.pagesize == 0:
                alignment = self.board.pagesize

            start_addr = self._find_next_fit(
                unallocated_region.size, alignment=alignment, reverse=True
            )
            self.freelist.reserve(start_addr, unallocated_region.size)
            unallocated_region.set_physical_start_addr(start_addr)

    def _allocate_virtual(self, freelist, unallocated_segments):
        for unallocated_region in unallocated_segments:
            alignment = 0
            if unallocated_region.size % self.board.pagesize == 0:
                alignment = self.board.pagesize

            start_addr = self._find_next_fit(
                unallocated_region.size,
                alignment=alignment,
                reverse=False,
                freelist=freelist,
            )
            freelist.reserve(start_addr, unallocated_region.size)
            unallocated_region.set_virtual_start_addr(start_addr)


# FIXME: this pass might not be needed any more
class PrepareMemoryRegionsPass(BasePass):
    """ Prepare memory regions by merging  regions from Extracted Board Info and Cell Configuration"""

    def __init__(self):
        self.config = None
        self.board = None

    def __call__(self, board, config):
        self.board = board
        self.config = config

        for cell in self.config.cells.values():
            for region in cell.memory_regions.values():
                if hasattr(region, "size") and region.size is None:
                    region.size = self.board.pagesize

            if cell.type == "root":
                self._prepare_memory_regions_root(cell)

        return self.board, self.config

    def _prepare_memory_regions_root(self, cell):

        for name, memory_region in self.board.memory_regions.items():

            p_start = memory_region.physical_start_addr
            v_start = memory_region.virtual_start_addr
            p_end = memory_region.physical_start_addr
            v_end = memory_region.virtual_start_addr

            skip = False
            for cell_region in cell.memory_regions.values():
                if not isinstance(cell_region, BaseMemoryRegion):
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
