import copy
import logging
import math
import sys
from collections import defaultdict
from functools import reduce
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import tabulate
from ortools.sat.python import cp_model

from ..model import (
    Board,
    CellConfig,
    DeviceMemoryRegion,
    HypervisorMemoryRegion,
    JailhouseConfig,
    MemoryRegion,
    MemoryRegionData,
    ShMemNetRegion,
)
from ..model.datatypes import HexInt
from .passes import BasePass


class MemoryAllocationInfeasibleException(Exception):
    pass


class AllocatorSegment:
    def __init__(
        self,
        name: str = "unnamed",
        alignment: int = 2 ** 12,
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
        self.constraint: Optional[MemoryConstraint] = None

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

        # allow arbitrary actions upon resolving a constraint
        # this method is called iff, the solver found a valid
        # solution and assigned start_addr
        # Parameters:
        # - self: MemoryConstraint
        self.resolved: Optional[Callable[[MemoryConstraint], None]] = None

    def __str__(self):
        return str(self.__dict__)

    # Returns a constraint that satisfies both
    # <self> and <other>, if possible
    # Fails otherwise
    def merge(self, other):
        assert (
            self.virtual == other.virtual
            and "Unable to merge constraints for pyhsical and virtual addresses"
        )

        assert (
            self.size == other.size
            and "Unable to merge constraints with different size"
        )

        assert (
            self.start_addr == other.start_addr
            and "Unbable to merge constraints with different start addresses"
        )

        alignment = self.alignment
        if other.alignment:
            if alignment:
                alignment = (self.alignment * other.alignment) / math.gcd(
                    self.alignment, other.alignment
                )
            else:
                alignment = other.alignment

        resolved = self.resolved
        if other.resolved:
            if resolved:

                def callback(mc: MemoryConstraint):
                    assert self.resolved
                    assert other.resolved

                    self.resolved(mc)
                    other.resolved(mc)

                resolved = callback
            else:
                resolved = other.resolved

        mc = MemoryConstraint(self.size, self.virtual)
        mc.virtual = self.virtual

        mc.start_addr = self.start_addr
        mc.alignment = alignment

        mc.resolved = resolved


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
            raise MemoryAllocationInfeasibleException()

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
        self.per_region_constraints: Dict[str, MemoryConstraint] = dict()

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

    def _iter_constraints(self, f_no_overlap, f_mc):
        for cell_name, no_overlap in self.no_overlap_constraints.items():
            if not f_no_overlap(cell_name, no_overlap):
                continue

            for mc in no_overlap.constraints:
                f_mc(cell_name, mc)

    def _dump_constraints(self):
        def f_no_overlap(cell_name, no_overlap):
            self.logger.info(f"No-overlap Constraint for: {cell_name}")
            return True

        def f_mc(cell_name, mc):
            self.logger.info(mc)

        self._iter_constraints(f_no_overlap, f_mc)

    def _check_constraints(self):
        def f_no_overlap(cell_name, no_overlap):
            full_regions = []

            def insert_region(region):
                o_start, o_end = region
                for (start, end) in full_regions:
                    if (
                        (o_start <= start and start <= o_end)
                        or (o_start <= end and end <= o_end)
                        or (start <= o_start and o_start <= end)
                        or (start <= o_end and o_end <= end)
                    ):
                        print(
                            f"Regions overlap for {cell_name}: (0x{start:x}, 0x{end:x}) and (0x{o_start:x}, 0x{o_end:x})"
                        )

                        seg = self.memory_constraints[mc]
                        print("Affected memory cells:")

                        for sharer in seg.shared_regions.keys():
                            print(f"\t{sharer}")

                full_regions.append(region)

            for mc in no_overlap.constraints:
                if mc.start_addr is not None:
                    region = (mc.start_addr, mc.start_addr + mc.size)
                    insert_region(region)

            return False

        def f_mc(cell_name, mc):
            pass

        self._iter_constraints(f_no_overlap, f_mc)

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

        self._preallocate_vpci()

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

        for seg in self.unallocated_segments:
            assert seg.size > 0
            assert seg.shared_regions

            mc_global = None
            for sharer, regions in seg.shared_regions.items():
                mc_seg = seg.constraint
                mc_local = MemoryConstraint(seg.size - 1, True)

                if mc_seg and mc_seg.alignment:
                    mc_local.alignment = mc_seg.alignment
                else:
                    mc_local.alignment = seg.alignment

                fst_region = regions[0]
                if fst_region.virtual_start_addr is not None:
                    if mc_seg and mc_seg.start_addr and mc_seg.virtual:
                        assert (
                            mc_seg.start_addr == fst_region.virtual_start_addr
                            and "Invalid state detected: start addresses must be equal"
                        )

                    mc_local.start_addr = fst_region.virtual_start_addr
                elif mc_seg and mc_seg.start_addr and mc_seg.virtual:
                    mc_local.start_addr = mc_seg.start_addr

                self.no_overlap_constraints[sharer].add_memory_constraint(
                    mc_local
                )

                if mc_seg and mc_seg.virtual:
                    mc_local.resolved = mc_seg.resolved

                self.memory_constraints[mc_local] = seg

                if not mc_global:
                    mc_global = copy.deepcopy(mc_local)
                    mc_global.virtual = False
                    mc_global.start_addr = None

                    if fst_region.physical_start_addr is not None:
                        if mc_seg and mc_seg.start_addr and not mc_seg.virtual:
                            assert (
                                mc_seg.start_addr
                                == fst_region.virtual_start_addr
                                and "Invalid state detected: start addresses must be equal"
                            )

                        mc_global.start_addr = fst_region.physical_start_addr
                    elif mc_seg and mc_seg.start_addr and not mc_seg.virtual:
                        mc_global.start_addr = mc_seg.start_addr

                    if mc_seg and not mc_seg.virtual:
                        mc_global.resolved = mc_seg.resolved

                    self.global_no_overlap.add_memory_constraint(mc_global)
                    self.memory_constraints[mc_global] = seg

        self._dump_constraints()

        solver = CPMemorySolver(
            list(self.no_overlap_constraints.values()),
            self.physical_domain,
            self.virtual_domain,
        )
        try:
            solver.solve()
        except MemoryAllocationInfeasibleException:
            self._check_constraints()
            sys.exit(-1)

        for cell_name, no_overlap_constr in self.no_overlap_constraints.items():
            # for root make sure, all pairs (phys,virt) are equal (to phys!)
            if cell_name == "root":
                continue

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

                if constr.resolved:
                    constr.resolved(constr)

        # handle root separately
        for constr in self.no_overlap_constraints["root"].constraints:
            seg = self.memory_constraints[constr]

            assert seg.shared_regions
            for region in seg.shared_regions["root"]:
                if region.virtual_start_addr is None:
                    region.virtual_start_addr = region.physical_start_addr

            if constr.resolved:
                constr.resolved(constr)

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
        assert self.config
        assert self.config.cells

        ana = UnallocatedOrSharedSegmentsAnalysis(
            self.root_cell,
            self.config.cells,
            self.logger,
            self.per_region_constraints,
            self.physical_domain,
            key,
        )

        ana.run()
        unallocated = ana.unallocated

        assert unallocated
        return unallocated

    def _preallocate_vpci(self):
        """Preallocate a virtual page on all devices"""
        assert self.config is not None

        if self.root_cell and self.root_cell.platform_info:
            region = MemoryRegion()
            region_name = "pci_mmconfig_generated"

            region.flags = ["MEM_IO"]

            # see hypvervisor/pci.c:850
            end_bus = self.root_cell.platform_info.pci_mmconfig_end_bus
            region.size = (end_bus + 1) * 256 * 4096

            if self.root_cell.platform_info.pci_mmconfig_base:
                region.physical_start_addr = (
                    self.root_cell.platform_info.pci_mmconfig_base
                )
                region.virtual_start_addr = region.physical_start_addr

                assert (region.physical_start_addr + region.size) < 2 ** 32

                def callback(mc: MemoryConstraint):
                    assert self.root_cell
                    assert self.root_cell.memory_regions

                    del self.root_cell.memory_regions[region_name]

                mc = MemoryConstraint(region.size, False)
                mc.start_addr = region.physical_start_addr
                mc.resolved = callback

                self.root_cell.memory_regions[region_name] = region
                self.per_region_constraints[region_name] = mc
            else:

                def callback(mc: MemoryConstraint):
                    assert mc.allocated_range
                    assert self.root_cell
                    assert self.root_cell.platform_info
                    assert self.root_cell.memory_regions

                    physical_start_addr, _ = mc.allocated_range
                    self.root_cell.platform_info.pci_mmconfig_base = HexInt(
                        physical_start_addr
                    )

                    region = self.root_cell.memory_regions[region_name]
                    assert isinstance(region, MemoryRegion)

                    region.physical_start_addr = HexInt(physical_start_addr)
                    region.virtual_start_addr = HexInt(physical_start_addr)

                    del self.root_cell.memory_regions[region_name]

                mc = MemoryConstraint(region.size, False)
                mc.resolved = callback

                # this is MEM_IO but should still be allocated
                region.flags = []

                self.per_region_constraints[region_name] = mc
                self.root_cell.memory_regions[region_name] = region


class UnallocatedOrSharedSegmentsAnalysis(object):
    """ Group unallocated memory regions into segments
        that are allocated continuously.
        Detect (un-)allocated regions that are shared
        between cells
    """

    def __init__(
        self,
        root_cell,
        cells,
        logger,
        per_region_constraints,
        physical_domain,
        key=lambda x: x.physical_start_addr,
    ) -> None:
        self.root_cell: CellConfig = root_cell
        self.cells: Dict[str, CellConfig] = cells
        self.logger = logger
        self.key = key
        self.per_region_constraints = per_region_constraints
        self.physical_domain: Optional[cp_model.Domain] = physical_domain

        # result store
        self.unallocated: List[AllocatorSegment] = []
        self.shared: Dict[str, AllocatorSegment] = {}

    def _detect_shared_memio(self):
        shared: Dict[
            Tuple[int, int], Tuple[int, List[MemoryRegion]]
        ] = defaultdict(lambda: (0, []))

        for cell in self.cells.values():
            for region in cell.memory_regions.values():
                if not isinstance(region, MemoryRegion):
                    continue

                if not self.key(region) or "MEM_IO" not in region.flags:
                    continue

                start = region.physical_start_addr
                key = (start, region.size)

                count, regions = shared[key]
                regions.append(region)

                shared[key] = (count + 1, regions)

        for count, regions in shared.values():
            if count > 1:
                for region in regions:
                    region.shared = True

    def _log_shared_segments(self):
        self.logger.info("Shared segments:")
        for name, seg in self.shared.items():
            self.logger.info(f"Region: '{name}' shared by")

            for cell_name in seg.shared_regions:
                self.logger.info(f"\t{cell_name}")

            self.logger.info("\n")

    def run(self) -> None:
        assert self.root_cell is not None
        assert self.cells is not None

        self._detect_shared_memio()

        # Add cell memories
        self.logger.debug("building allocatable regions")
        for cell_name, cell in self.cells.items():
            assert cell is not None
            assert cell.memory_regions is not None

            for region_name, region in cell.memory_regions.items():
                if not isinstance(region, MemoryRegion):
                    continue
                if region.allocatable:
                    continue
                if self.key(region) is not None and region_name == "memreserve":
                    continue

                assert self.shared is not None
                if region.shared and region_name in self.shared:
                    current_segment = self.shared[region_name]

                    assert current_segment.shared_regions
                    current_segment.shared_regions[cell_name].append(region)

                    if region_name in self.per_region_constraints:
                        constraint = self.per_region_constraints[region_name]

                        if current_segment.constraint:
                            constraint = constraint.merge(
                                current_segment.constraint
                            )

                        current_segment.constraint = constraint
                else:
                    current_segment = AllocatorSegment(
                        region_name, shared_regions={cell_name: [region]},
                    )

                    if region_name in self.per_region_constraints:
                        current_segment.constraint = self.per_region_constraints[
                            region_name
                        ]

                    if region.physical_start_addr is not None:
                        if (
                            self.physical_domain
                            and self.physical_domain.Contains(
                                int(region.physical_start_addr)
                            )
                            or "MEM_IO" not in region.flags
                        ):
                            self.unallocated.append(current_segment)
                    else:
                        self.unallocated.append(current_segment)

                    # TODO are shared regions required to have
                    # the same name accross cells?
                    if region.shared:
                        self.shared[region_name] = current_segment

        # Add hypervisor memories
        hypervisor_memory = self.root_cell.hypervisor_memory
        assert isinstance(hypervisor_memory, HypervisorMemoryRegion)

        if hypervisor_memory.physical_start_addr is None:
            self.unallocated.append(
                AllocatorSegment(
                    "hypervisor_memory",
                    alignment=hypervisor_memory.size,  # FIXME: this is too much alignment
                    shared_regions={"hypervisor": [hypervisor_memory]},
                )
            )

        self._log_shared_segments()


class MergeIoRegionsPass(BasePass):
    """ Merge IO regions in root cell that are at most 64 kB apart """

    def __init__(self) -> None:
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None
        self.root_cell: Optional[CellConfig] = None
        self.logger = logging.getLogger("autojail")

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self.logger.info("Merge IO Regions")

        self.board = board
        self.config = config

        for cell in self.config.cells.values():
            if cell.type == "root":
                self.root_cell = cell

        assert self.root_cell
        assert self.root_cell.memory_regions

        shared_regions_ana = UnallocatedOrSharedSegmentsAnalysis(
            self.root_cell,
            self.config.cells,
            self.logger,
            dict(),
            None,
            key=lambda region: region.physical_start_addr,
        )
        shared_regions_ana.run()

        def get_io_regions(
            regions: Dict[
                str,
                Union[str, ShMemNetRegion, MemoryRegion, DeviceMemoryRegion],
            ]
        ) -> List[Tuple[str, DeviceMemoryRegion]]:
            return list(
                [
                    (name, r)
                    for name, r in regions.items()
                    if isinstance(r, DeviceMemoryRegion)
                ]
            )

        regions: Sequence[Tuple[str, MemoryRegionData]] = get_io_regions(
            self.root_cell.memory_regions
        )
        regions = sorted(regions, key=lambda t: t[1].physical_start_addr,)

        grouped_regions: List[List[Tuple[str, MemoryRegionData]]] = []
        current_group: List[Tuple[str, MemoryRegionData]] = []

        max_dist = 65536
        for name, r in regions:
            assert r.physical_start_addr
            assert r.size

            if current_group:
                r1_end = r.physical_start_addr + r.size

                assert current_group[-1][1].physical_start_addr
                if (
                    current_group[-1][1].physical_start_addr - r1_end > max_dist
                    or r.shared
                ):
                    grouped_regions.append(current_group)

                    if not r.shared:
                        current_group = [(name, r)]
                    else:
                        current_group = []
                else:
                    current_group.append((name, r))
            else:
                current_group.append((name, r))

        if current_group:
            grouped_regions.append(current_group)

        self.logger.info(f"Got {len(grouped_regions)} grouped region(s):")
        for group in grouped_regions:
            self.logger.info("Group-Begin:")
            for region in group:
                self.logger.info(f"\t{region}")

            self.logger.info("Group-End\n")

        for index, regions in enumerate(grouped_regions):
            r_start = regions[0][1]
            r_end = regions[-1][1]

            assert r_start.physical_start_addr
            assert r_end.size
            assert r_end.physical_start_addr
            new_size = (
                r_end.physical_start_addr + r_end.size
            ) - r_start.physical_start_addr

            def aux(
                acc: Iterable[str], t: Tuple[str, MemoryRegionData]
            ) -> Iterable[str]:
                _, r = t

                return set(acc) | set(r.flags)

            init: Iterable[str] = set()
            flags: List[str] = sorted(list(reduce(aux, regions, init)))

            physical_start_addr = r_start.physical_start_addr
            virtual_start_addr = r_start.virtual_start_addr

            new_region = MemoryRegion(
                size=new_size,
                physical_start_addr=physical_start_addr,
                virtual_start_addr=virtual_start_addr,
                flags=flags,
                allocatable=False,
                shared=False,
            )

            assert self.root_cell.memory_regions
            for name, _ in regions:
                del self.root_cell.memory_regions[name]

            self.root_cell.memory_regions[f"mmio_{index}"] = new_region

        return (self.board, self.config)


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
                if isinstance(region, MemoryRegion) and region.size is None:
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

                if not isinstance(cell_region, MemoryRegionData):
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
