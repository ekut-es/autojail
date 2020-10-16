import copy
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple, Union

import tabulate
from autojail.model.board import Board, HypervisorMemoryRegion, MemoryRegion
from ortools.sat.python import cp_model

from ..model import BaseMemoryRegion, CellConfig, JailhouseConfig
from ..model.datatypes import HexInt
from .passes import BasePass


class AllocatorSegment:
    def __init__(
        self,
        name: str = "unnamed",
        alignment: int = 0,
        shared_regions: Optional[
            Dict[str, List[Union[MemoryRegion, HypervisorMemoryRegion]]]
        ] = None,
    ) -> None:
        self.name = name

        self.shared_regions: Optional[
            Dict[str, List[Union[MemoryRegion, HypervisorMemoryRegion]]]
        ] = defaultdict(list)
        if shared_regions:
            self.shared_regions.update(shared_regions)

        self.alignment = alignment

    @property
    def physical_start_addr(self):
        key = self.shared_regions.keys()[0]
        return self.shared_regions[key][0].physical_start_addr

    @property
    def size(self):
        key = list(self.shared_regions)[0]
        return sum(map(lambda r: r.size, self.shared_regions[key]))


class MemoryConstraint(object):
    """Implements a generic constraint for AllocatorSegments"""

    def __init__(self, size: int, virtual: bool) -> None:
        self.size = size
        self.virtual = virtual

        self.address_range: Optional[Tuple[int, int]] = None
        self.start_addr: Optional[int] = None

        # Addresses must be aligned such that
        # addr % self.alignment == 0
        self.alignment: Optional[int] = None

        self.allocated_range: Optional[Tuple[int, int]] = None

    def __str__(self):
        return str(self.__dict__)


class NoOverlapConstraint(object):
    """Implements a generic no-overlap constraint"""

    def __init__(self) -> None:
        self.constraints: List[MemoryConstraint] = []

    def add_memory_constraint(self, mc: MemoryConstraint) -> None:
        self.constraints.append(mc)

    def __str__(self):
        return str(self.__dict__)


class CPMemorySolver(object):
    def __init__(
        self,
        constraints: List[NoOverlapConstraint],
        pyhsical_domain: cp_model.Domain,
        virtual_domain: cp_model.Domain,
    ):
        self.constraints = constraints
        self.model = cp_model.CpModel()

        self.physical_domain = pyhsical_domain
        self.virtual_domain = virtual_domain

        self.ivars: Dict[cp_model.IntervalVar, MemoryConstraint] = dict()
        self.vars: Dict[
            cp_model.IntervalVar, Tuple[cp_model.IntVar, cp_model.IntVar]
        ] = dict()

        self._build_cp_constraints()

    def solve(self):
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
            for ivar, mc in self.ivars.items():
                lower, upper = self.vars[ivar]
                mc.allocated_range = solver.Value(lower), solver.Value(upper)
        else:
            print("Memory allocation infeasible")
            raise AssertionError

    def _build_cp_constraints(self):
        for overlap_index, no_overlap in enumerate(self.constraints):
            cp_no_overlap = []

            for constr_index, constr in enumerate(no_overlap.constraints):
                lower = None
                upper = None

                constr_name = f"constr_{overlap_index}_{constr_index}"
                if constr.start_addr is not None:
                    lower = self.model.NewConstant(constr.start_addr)
                    upper = self.model.NewConstant(
                        constr.start_addr + constr.size
                    )
                else:
                    if constr.address_range:
                        l_addr, u_addr = constr.address_range
                        lower = self.model.NewIntVar(
                            l_addr, u_addr, f"{constr_name}_lower"
                        )
                    else:
                        domain = self.physical_domain
                        if constr.virtual:
                            domain = self.virtual_domain

                        lower = self.model.NewIntVarFromDomain(
                            domain, f"{constr_name}_lower"
                        )

                    if constr.address_range:
                        l_addr, u_addr = constr.address_range
                        upper = self.model.NewIntVar(
                            l_addr, u_addr, f"{constr_name}_upper"
                        )
                    else:
                        domain = self.physical_domain
                        if constr.virtual:
                            domain = self.virtual_domain

                        upper = self.model.NewIntVarFromDomain(
                            domain, f"{constr_name}_upper"
                        )

                ivar = self.model.NewIntervalVar(
                    lower, constr.size, upper, f"{constr_name}_ivar"
                )

                if constr.alignment:
                    self.model.AddModuloEquality(0, lower, constr.alignment)

                cp_no_overlap.append(ivar)

                self.ivars[ivar] = constr
                self.vars[ivar] = (lower, upper)

            self.model.AddNoOverlap(cp_no_overlap)


class AllocateMemoryPass(BasePass):
    """Implements a simple MemoryAllocator for AutoJail"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("autojail")
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None
        self.root_cell: Optional[CellConfig] = None

        self.unallocated_segments: List[AllocatorSegment] = []
        self.allocated_regions: List[MemoryRegion] = []

        # data structure for creating and handling generic
        # constraints
        self.physical_domain: cp_model.Domain = None
        self.virtual_domain: cp_model.Domain = None
        self.global_no_overlap = NoOverlapConstraint()

        self.no_overlap_constraints: Dict[
            str, NoOverlapConstraint
        ] = defaultdict(NoOverlapConstraint)
        self.memory_constraints: Dict[
            MemoryConstraint, AllocatorSegment
        ] = dict()

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

        vmem_size = 2 ** 32
        if self.board.virtual_address_bits > 32:
            vmem_size = 2 ** (self.board.virtual_address_bits - 1)

        self.virtual_domain = cp_model.Domain(0, vmem_size)
        self._build_allocation_domain()

        self.no_overlap_constraints["__global"] = self.global_no_overlap
        self.unallocated_segments = self._build_unallocated_segments()

        self.logger.info("")
        self.logger.info("Unallocated physical segments: ")
        table = [
            [
                s.name,
                s.size,
                len(s.shared_regions if s.shared_regions else []),
                ",".join(s.shared_regions.keys() if s.shared_regions else []),
            ]
            for s in self.unallocated_segments
        ]
        self.logger.info(
            tabulate.tabulate(
                table,
                headers=["Name", "Size (Byte)", "# Subregions", "Sharers"],
            )
        )

        self._lift_loadable()
        self._preallocate_vpci()

        for seg in self.unallocated_segments:
            assert seg.size > 0
            assert seg.shared_regions

            mc_global = None
            for sharer, regions in seg.shared_regions.items():
                mc_local = MemoryConstraint(seg.size, True)
                mc_local.alignment = seg.alignment

                fst_region = regions[0]
                if fst_region.virtual_start_addr is not None:
                    mc_local.start_addr = fst_region.virtual_start_addr

                self.no_overlap_constraints[sharer].add_memory_constraint(
                    mc_local
                )
                self.memory_constraints[mc_local] = seg

                if not mc_global:
                    mc_global = copy.deepcopy(mc_local)
                    mc_global.virtual = False
                    mc_global.start_addr = None

                    if fst_region.physical_start_addr is not None:
                        mc_global.start_addr = fst_region.physical_start_addr

                    self.global_no_overlap.add_memory_constraint(mc_global)
                    self.memory_constraints[mc_global] = seg

        solver = CPMemorySolver(
            list(self.no_overlap_constraints.values()),
            self.physical_domain,
            self.virtual_domain,
        )
        solver.solve()

        for cell_name, no_overlap_constr in self.no_overlap_constraints.items():
            for constr in no_overlap_constr.constraints:
                assert constr.allocated_range
                (start, _) = constr.allocated_range

                seg = self.memory_constraints[constr]
                if cell_name == "__global":
                    assert seg.shared_regions

                    for _, regions in seg.shared_regions.items():
                        for region in regions:
                            if region.physical_start_addr is None:
                                region.physical_start_addr = HexInt(start)
                else:
                    assert seg.shared_regions
                    assert constr.virtual

                    for region in seg.shared_regions[cell_name]:
                        if region.virtual_start_addr is None:
                            region.virtual_start_addr = HexInt(start)

        self._remove_allocatable()

        return self.board, self.config

    def _lift_loadable(self):
        root_cell = self.root_cell
        for cell_name, cell in self.config.cells.items():
            if cell.type == "root":
                continue

            for name, region in cell.memory_regions.items():
                if region.flags and "MEM_LOADABLE" in region.flags:
                    root_region_name = f"{name}@{cell_name}"
                    print("Adding region:", root_region_name, "to root cell")

                    copy_region = copy.deepcopy(region)
                    copy_region.flags.remove("MEM_LOADABLE")
                    # FIXME: is it really true, that that MEM_LOADABLE must be the same at their respective memory region
                    copy_region.virtual_start_addr = (
                        copy_region.physical_start_addr
                    )
                    root_cell.memory_regions[root_region_name] = copy_region

                    for seg in self.unallocated_segments:
                        if cell_name not in seg.shared_regions:
                            continue

                        if region not in seg.shared_regions[cell_name]:
                            continue

                        seg.shared_regions["root"].append(copy_region)

    def _build_allocation_domain(self) -> None:
        assert self.root_cell is not None
        assert self.root_cell.memory_regions is not None

        intervals = []

        for region in self.root_cell.memory_regions.values():
            assert region is not None
            if isinstance(region, MemoryRegion) and region.allocatable:
                assert region.physical_start_addr is not None
                assert region.size is not None
                intervals.append(
                    [
                        region.physical_start_addr,
                        region.physical_start_addr + region.size,
                    ]
                )

        self.physical_domain = cp_model.Domain.FromIntervals(intervals)

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

    def _build_unallocated_segments(
        self, key: Callable = lambda x: x.physical_start_addr
    ) -> List[AllocatorSegment]:
        """Group Memory Regions into Segments that are allocated continuously"""
        assert self.root_cell is not None
        assert self.config is not None

        unallocated = []
        shared_segments: Dict[str, AllocatorSegment] = {}

        # Add cell memories
        self.logger.debug("building allocatable regions")
        for cell_name, cell in self.config.cells.items():
            assert cell is not None
            assert cell.memory_regions is not None

            # FIXME add constraints for already allocated regions
            # -> skipped due to line 390
            # -> make sure IO regions that are shared are either
            #   - marked shared
            #   - only added once

            for region_name, region in cell.memory_regions.items():
                if not isinstance(region, MemoryRegion):
                    continue
                if region.allocatable:
                    continue
                if key(region) is not None and (
                    "MEM_IO" in region.flags or region_name == "memreserve"
                ):
                    continue
                if key(region):
                    print(region)

                assert shared_segments is not None
                if region.shared and region_name in shared_segments:
                    current_segment = shared_segments[region_name]

                    assert current_segment.shared_regions
                    current_segment.shared_regions[cell_name].append(region)
                else:
                    current_segment = AllocatorSegment(
                        region_name,
                        alignment=8,
                        shared_regions={cell_name: [region]},
                    )
                    unallocated.append(current_segment)
                    if region.shared:
                        shared_segments[region_name] = current_segment

        # Add hypervisor memories
        hypervisor_memory = self.root_cell.hypervisor_memory
        assert isinstance(hypervisor_memory, HypervisorMemoryRegion)

        if hypervisor_memory.physical_start_addr is None:
            unallocated.append(
                AllocatorSegment(
                    "hypervisor_memory",
                    alignment=hypervisor_memory.size,  # FIXME: this is too much alignment
                    shared_regions={"hypervisor": [hypervisor_memory]},
                )
            )

        return unallocated

    def _preallocate_vpci(self):
        """Preallocate a virtual page on all devices"""
        assert self.config is not None

        if self.root_cell and self.root_cell.platform_info:
            if self.root_cell.platform_info.pci_mmconfig_base:
                # FIXME: preallocate pci
                pass
            else:
                self.root_cell.platform_info.pci_mmconfig_base = 0xE0000000


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
