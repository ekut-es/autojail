import copy
import logging
from typing import Callable, List, Optional, Tuple, Union

import tabulate

from autojail.model.board import (
    Board,
    HypervisorMemoryRegion,
    MemoryRegion,
    ShMemNetRegion,
)

from ..model import (
    BaseMemoryRegion,
    ByteSize,
    CellConfig,
    HexInt,
    JailhouseConfig,
)
from ..utils import SortedCollection
from .passes import BasePass


class MemoryBlock:
    "Represents a chunk of memory in the allocator"

    def __init__(
        self, start_addr: Union[HexInt, int], size: Union[ByteSize, int]
    ) -> None:
        self.start_addr = start_addr
        self.size = size

    @property
    def end_addr(self) -> int:
        return self.start_addr + self.size

    def __repr__(self):
        return (
            f"MemoryBlock(start_addr={hex(self.start_addr)},size={self.size})"
        )

    def __lt__(self, other: "MemoryBlock") -> bool:
        if self.start_addr < other.start_addr:
            return True
        return False


class FreeList(SortedCollection):
    def __init__(self) -> None:
        super().__init__(key=lambda x: x.start_addr)

    def _overlap(self, block1: MemoryBlock, block2: MemoryBlock) -> bool:
        if block2 < block1:
            block1, block2 = block2, block1

        if block1.end_addr >= block2.start_addr:
            return True
        return False

    def _sub(self, current_block: MemoryBlock, sub_block: MemoryBlock) -> None:
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

    def insert(self, block: "MemoryBlock") -> None:
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

    def _reserve(self, block: MemoryBlock) -> None:
        # FIXME: use binary search to find start
        for local_block in self:
            if self._overlap(local_block, block):
                self._sub(local_block, block)

    def reserve(
        self, start_addr: Union[HexInt, int], size: Union[int, ByteSize]
    ) -> None:
        self._reserve(MemoryBlock(start_addr, size))


class AllocatorSegment:
    def __init__(
        self,
        name: str = "unnamed",
        memory_regions: Optional[
            List[Union[MemoryRegion, HypervisorMemoryRegion]]
        ] = None,
        alignment: int = 0,
        sharer_names: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.memory_regions: List[
            Union[MemoryRegion, HypervisorMemoryRegion]
        ] = (memory_regions if memory_regions is not None else [])
        self.sharer_names = sharer_names if sharer_names is not None else []
        self.size = sum(r.size for r in self.memory_regions)
        self.alignment = alignment

    @property
    def physical_start_addr(self):
        return self.memory_regions[0].physical_start_addr

    def set_physical_start_addr(self, addr: int) -> None:
        for region in self.memory_regions:
            region.physical_start_addr = HexInt.validate(addr)
            assert region.size is not None
            addr += region.size

    def set_virtual_start_addr(self, addr: int) -> None:
        for region in self.memory_regions:
            region.virtual_start_addr = HexInt.validate(addr)
            assert region.size is not None
            addr += region.size


class AllocateMemoryPass(BasePass):
    """Implements a simple MemoryAllocator for AutoJail"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("autojail")
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None
        self.root_cell: Optional[CellConfig] = None
        self.freelist = FreeList()
        self.allocatable_regions: List[MemoryRegion] = []

        self.unallocated_segments: List[AllocatorSegment] = []
        self.allocated_regions: List[MemoryRegion] = []

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
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

        self._lift_loadable()
        for name, cell in config.cells.items():
            freelist_virtual = FreeList()
            vmem_size = 2 ** 32
            if self.board.virtual_address_bits > 32:
                vmem_size = 2 ** (self.board.virtual_address_bits - 1)
            freelist_virtual.insert(MemoryBlock(0, vmem_size))
            self._log_freelist(
                freelist_virtual, f"Initial free vmem of cell {name}"
            )

            self._preallocate_vpci()
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

            self._remove_allocatable()

        return self.board, self.config

    def _lift_loadable(self):
        root_cell = self.root_cell
        for cell_name, cell in self.config.cells.items():
            if cell.type == "root":
                continue

            for name, region in cell.memory_regions.items():
                if region.flags and "MEM_LOADABLE" in region.flags:
                    print("Adding region:", name, "to root cell")
                    copy_region = copy.deepcopy(region)
                    copy_region.flags.remove("MEM_LOADABLE")
                    # FIXME: is it really true, that that MEM_LOADABLE must be the same at their respective memory region
                    copy_region.virtual_start_addr = (
                        copy_region.physical_start_addr
                    )
                    root_cell.memory_regions[
                        f"{name}@{cell_name}"
                    ] = copy_region

    def _log_freelist(self, freelist: FreeList, message: str = "") -> None:

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

    def _build_freelist(self) -> None:
        assert self.root_cell is not None
        assert self.root_cell.memory_regions is not None
        for region in self.root_cell.memory_regions.values():
            assert region is not None
            if isinstance(region, MemoryRegion) and region.allocatable:
                assert region.physical_start_addr is not None
                assert region.size is not None
                new_block = MemoryBlock(region.physical_start_addr, region.size)
                self.freelist.insert(new_block)
                self.allocatable_regions.append(region)

    def _build_unallocated_segments(
        self, key: Callable = lambda x: x.physical_start_addr
    ) -> List[AllocatorSegment]:
        """Group Memory Regions into Segments that are allocated continuously"""
        assert self.root_cell is not None
        assert self.config is not None

        unallocated = []

        # Add cell memories
        self.logger.debug("building allocatable regions")
        for cell_name, cell in self.config.cells.items():
            assert cell is not None
            assert cell.memory_regions is not None
            for region_name, region in cell.memory_regions.items():
                if not isinstance(region, MemoryRegion):
                    continue
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
        assert isinstance(hypervisor_memory, HypervisorMemoryRegion)
        if hypervisor_memory.physical_start_addr is None:
            unallocated.append(
                AllocatorSegment(
                    "hypervisor_memory",
                    [hypervisor_memory],
                    alignment=hypervisor_memory.size,  # FIXME: this is too much alignment
                    sharer_names=["hypervisor"],
                )
            )

        return unallocated

    def _build_unallocated_segments_virtual(
        self, cell: CellConfig
    ) -> List[AllocatorSegment]:
        unallocated = []
        assert cell.memory_regions is not None
        for name, region in cell.memory_regions.items():
            if isinstance(region, str):
                continue
            if isinstance(region, ShMemNetRegion):
                continue
            if region.virtual_start_addr is None:
                unallocated.append(AllocatorSegment(name, [region]))
        return unallocated

    def _preallocate_physical(self) -> None:
        assert self.config is not None
        for cell in self.config.cells.values():
            assert cell.memory_regions is not None
            for memory_region in cell.memory_regions.values():
                if isinstance(memory_region, str):
                    continue
                if isinstance(memory_region, ShMemNetRegion):
                    continue
                if memory_region.allocatable:
                    continue

                assert memory_region.size is not None
                if memory_region.physical_start_addr is not None:
                    self.freelist.reserve(
                        memory_region.physical_start_addr, memory_region.size
                    )

    def _preallocate_vpci(self):
        """Preallocate a virtual page on all devices"""
        assert self.config is not None

        if self.root_cell and self.root_cell.platform_info:
            if self.root_cell.platform_info.pci_mmconfig_base:
                # FIXME: preallocate pci
                pass
            else:
                self.root_cell.platform_info.pci_mmconfig_base = 0x800000000

    def _preallocate_virtual(
        self, freelist: FreeList, cell: CellConfig
    ) -> FreeList:
        if cell.memory_regions is None:
            return freelist

        for memory_region in cell.memory_regions.values():
            if isinstance(memory_region, str):
                continue
            if memory_region.allocatable:
                continue
            assert memory_region.size is not None
            if memory_region.virtual_start_addr is not None:
                freelist.reserve(
                    memory_region.virtual_start_addr, memory_region.size
                )

        return freelist

    def _find_next_fit(
        self,
        size: Union[int, ByteSize],
        alignment: Union[int, ByteSize] = 0,
        reverse: bool = True,
        freelist: Optional[FreeList] = None,
    ) -> int:
        if freelist is None:
            freelist = self.freelist

        if reverse:
            freelist = reversed(freelist)  # type: ignore

        for block in freelist:
            alignment_offset = block.start_addr % alignment
            if reverse:
                alignment_offset = (block.start_addr + block.size) % alignment

            if block.size >= size + alignment_offset:
                if reverse:
                    diff = block.size - size - alignment_offset
                    return block.start_addr + diff

                return block.start_addr + alignment_offset

        raise Exception(
            f"Could not find continuous Memory with size: {hex(size)}"
        )

    def _allocate_physical(self) -> None:
        assert self.board is not None
        for unallocated_region in self.unallocated_segments:
            assert unallocated_region.size is not None
            alignment = max(unallocated_region.alignment, self.board.pagesize)

            start_addr = self._find_next_fit(
                unallocated_region.size, alignment=alignment, reverse=True
            )
            self.freelist.reserve(start_addr, unallocated_region.size)
            unallocated_region.set_physical_start_addr(start_addr)

    def _allocate_virtual(
        self, freelist: FreeList, unallocated_segments: List[AllocatorSegment]
    ) -> None:
        assert self.board is not None
        for unallocated_region in unallocated_segments:
            assert unallocated_region.size is not None
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

    def _remove_allocatable(self):
        """Finally remove allocatable memory regions from cells"""
        assert self.config is not None

        for cell in self.config.cells.values():
            delete_list = []
            for name, region in cell.memory_regions.items():
                if isinstance(region, MemoryRegion):
                    if region.allocatable:
                        delete_list.append(name)

            for name in delete_list:
                del cell.memory_regions[name]


# FIXME: this pass might not be needed any more
class PrepareMemoryRegionsPass(BasePass):
    """ Prepare memory regions by merging  regions from Extracted Board Info and Cell Configuration"""

    def __init__(self) -> None:
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self.board = board
        self.config = config

        assert self.board is not None
        assert self.config is not None

        for cell in self.config.cells.values():
            assert cell.memory_regions is not None
            for region in cell.memory_regions.values():
                if isinstance(region, BaseMemoryRegion) and region.size is None:
                    region.size = self.board.pagesize

            if cell.type == "root":
                self._prepare_memory_regions_root(cell)

        return self.board, self.config

    def _prepare_memory_regions_root(self, cell: CellConfig) -> None:
        assert self.board is not None
        assert self.board.memory_regions is not None
        assert cell.memory_regions is not None

        for name, memory_region in self.board.memory_regions.items():
            if memory_region.physical_start_addr is None:
                continue
            if memory_region.virtual_start_addr is None:
                continue
            if memory_region.size is None:
                continue

            p_start = memory_region.physical_start_addr
            v_start = memory_region.virtual_start_addr
            p_end = memory_region.physical_start_addr + memory_region.size
            v_end = memory_region.virtual_start_addr + memory_region.size

            assert p_start is not None
            assert v_start is not None
            assert p_end is not None
            assert v_end is not None

            skip = False
            for cell_region in cell.memory_regions.values():

                if not isinstance(cell_region, BaseMemoryRegion):
                    continue

                assert cell_region.size is not None

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
