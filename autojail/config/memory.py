import copy
import logging
import math
import sys
from collections import defaultdict
from functools import reduce
from typing import (
    Any,
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
from ..model.parameters import GenerateConfig, GenerateParameters, ScalarChoice
from ..utils import get_overlap
from .passes import BasePass


class MemoryAllocationInfeasibleException(Exception):
    pass


class AllocatorSegment:
    def __init__(
        self,
        name: str = "unnamed",
        alignment: int = 2 ** 12,
        shared_regions: Optional[
            Dict[
                str,
                List[
                    Union[
                        MemoryRegion, DeviceMemoryRegion, HypervisorMemoryRegion
                    ]
                ],
            ]
        ] = None,
    ) -> None:
        self.name = name

        self.shared_regions: Optional[
            Dict[
                str,
                List[
                    Union[
                        MemoryRegion, DeviceMemoryRegion, HypervisorMemoryRegion
                    ]
                ],
            ]
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

    def __init__(
        self, size: int, virtual: bool, start_addr: int = None
    ) -> None:
        self.size = size
        self.virtual = virtual

        self.start_addr: Optional[int] = start_addr
        self.address_range: Optional[Tuple[int, int]] = None

        # Addresses must be aligned such that
        # addr % self.alignment == 0
        self.alignment: Optional[int] = None

        # Constraint for Memory regions where physical == virtual address
        # E.g. mem loadable in root cell
        self.equal_constraint: Optional["MemoryConstraint"] = None

        # Solver Interval Variable
        self.bound_vars: Optional[Tuple[Any, Any]] = None

        # Values for the allocated range after constraint solving
        self.allocated_range: Optional[Tuple[int, int]] = None

        # allow arbitrary actions upon resolving a constraint
        # this method is called iff, the solver found a valid
        # solution and assigned start_addr
        # Parameters:
        # - self: MemoryConstraint
        self.resolved: Optional[Callable[[MemoryConstraint], None]] = None

    def __str__(self):
        ret = ""
        if self.start_addr is not None:
            ret += f"addr: {hex(self.start_addr)} "
        if self.address_range:
            ret += f"range: {hex(self.address_range[0])}-{hex(self.address_range[1])} "
        if self.alignment:
            ret += f"alignment: {self.alignment} "
        if self.address_range:
            ret += f"allocated: {hex(self.address_range[0])}-{hex(self.adress_range[1])} "
        ret += f"size: {self.size} virtual: {self.virtual}"
        return ret

    # Returns a constraint that satisfies both
    # <self> and <other>, if possible
    # Fails otherwise
    def merge(self, other):
        assert (
            self.virtual == other.virtual
            and "Unable to merge constraints for physical and virtual addresses"
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
        physical_domain: cp_model.Domain,
        virtual_domain: cp_model.Domain,
    ):
        self.constraints = constraints
        self.model = cp_model.CpModel()

        self.physical_domain = physical_domain
        self.virtual_domain = virtual_domain

        self.ivars: Dict[cp_model.IntervalVar, MemoryConstraint] = dict()
        self.vars: Dict[
            cp_model.IntervalVar, Tuple[cp_model.IntVar, cp_model.IntVar]
        ] = dict()

        self._build_cp_constraints()

    def solve(self):
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True

        status = solver.Solve(self.model)

        if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
            for ivar, mc in self.ivars.items():
                lower, upper = self.vars[ivar]
                mc.allocated_range = solver.Value(lower), solver.Value(upper)
        else:
            print("Memory allocation infeasible")
            raise MemoryAllocationInfeasibleException()

    def _build_cp_constraints(self):
        equal_pairs = []
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
                print(lower, constr.size, upper)
                constr.bound_vars = (lower, upper)

                if constr.alignment:
                    self.model.AddModuloEquality(0, lower, constr.alignment)

                if constr.equal_constraint:

                    equal_pairs.append((constr, constr.equal_constraint))

                cp_no_overlap.append(ivar)

                self.ivars[ivar] = constr
                self.vars[ivar] = (lower, upper)

            self.model.AddNoOverlap(cp_no_overlap)

        for first, second in equal_pairs:
            self.model.Add(first.bound_vars[0] == second.bound_vars[0])
            self.model.Add(first.bound_vars[1] == second.bound_vars[1])


class AllocateMemoryPass(BasePass):
    """Implements a simple MemoryAllocator for AutoJail"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("autojail")
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None
        self.root_cell: Optional[CellConfig] = None
        self.root_cell_id: Optional[str] = None

        self.unallocated_segments: List[AllocatorSegment] = []
        self.allocated_regions: List[MemoryRegionData] = []
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
        constraint_tables = {}

        def f_no_overlap(
            cell_name: str, no_overlap: NoOverlapConstraint
        ) -> bool:
            constraint_tables[cell_name] = []
            return True

        def f_mc(cell_name: str, mc: MemoryConstraint) -> None:
            constraint_tables[cell_name].append(
                [
                    hex(mc.start_addr) if mc.start_addr is not None else "-",
                    hex(mc.address_range[0]) + "-" + hex(mc.address_range[1])
                    if mc.address_range
                    else "-",
                    str(mc.size) if mc.size is not None else "-",
                    str(mc.alignment) if mc.alignment else "-",
                    str(mc.virtual),
                    "yes" if mc.equal_constraint else "-",
                    str(mc.resolved) if mc.resolved else "-",
                ]
            )

        self._iter_constraints(f_no_overlap, f_mc)

        self.logger.info("")
        self.logger.info("Memory Constraints:")
        for cell_name, constraints in constraint_tables.items():
            self.logger.info("Cell: %s", cell_name)
            formatted = tabulate.tabulate(
                constraints,
                headers=[
                    "Start Address",
                    "Start Address Range",
                    "Size",
                    "Alignment",
                    "Virtual?",
                    "Equal?",
                    "Resolved callback",
                ],
            )
            self.logger.info(formatted)
            self.logger.info("")

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

                        if mc not in self.memory_constraints:
                            continue
                        seg = self.memory_constraints[mc]
                        print("Affected memory cells:")

                        for sharer in seg.shared_regions.keys():
                            print(f"\t{sharer}")

                full_regions.append(region)

            for mc in no_overlap.constraints:
                if mc.start_addr is not None:
                    region = (mc.start_addr, mc.start_addr + mc.size - 1)
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

        for id, cell in self.config.cells.items():
            if cell.type == "root":
                self.root_cell = cell
                self.root_cell_id = id
                break

        vmem_size = 2 ** 32
        if self.board.virtual_address_bits > 32:
            vmem_size = 2 ** (self.board.virtual_address_bits - 1)

        self.virtual_domain = cp_model.Domain(0, vmem_size)
        self._build_allocation_domain()

        self.logger.info(
            "Physical Memory Domain: %s",
            str(self.physical_domain.FlattenedIntervals()),
        )

        self.logger.info(
            "Virtual Memory domain: %s",
            str(self.virtual_domain.FlattenedIntervals()),
        )

        self.no_overlap_constraints["__global"] = self.global_no_overlap
        self.unallocated_segments = self._build_unallocated_segments()
        self._lift_loadable()
        self._preallocate_vpci()

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

        for seg in self.unallocated_segments:
            assert seg.size > 0
            assert seg.shared_regions

            mc_global = None
            for sharer, regions in seg.shared_regions.items():
                mc_seg = seg.constraint
                mc_local = MemoryConstraint(seg.size, True)

                if mc_seg and mc_seg.alignment:
                    mc_local.alignment = mc_seg.alignment
                else:
                    if regions[0].virtual_start_addr is None:
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

                if mc_seg and mc_seg.virtual:
                    mc_local.resolved = mc_seg.resolved

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

                    if mc_global.start_addr and mc_global.size:
                        print(
                            f"Adding global no-overlapp (shared): [0x{mc_global.start_addr:x}, 0x{mc_global.start_addr + mc_global.size:x}]"
                        )

                    self.global_no_overlap.add_memory_constraint(mc_global)
                    self.memory_constraints[mc_global] = seg

                # Add physical == virtual constraint for MEM_LOADABLEs in root cell
                if sharer == self.root_cell_id:
                    is_loadable = False
                    for shared_regions in seg.shared_regions.values():
                        for shared_region in shared_regions:
                            if isinstance(shared_region, MemoryRegionData):
                                for flag in shared_region.flags:
                                    if flag == "MEM_LOADABLE":
                                        is_loadable = True
                    if is_loadable:
                        mc_local.equal_constraint = mc_global

                self.no_overlap_constraints[sharer].add_memory_constraint(
                    mc_local
                )
                self.memory_constraints[mc_local] = seg

        # Add virtually reserved segments
        for cell_name, cell in self.config.cells.items():
            assert cell.memory_regions is not None

            for memory_region in cell.memory_regions.values():
                assert memory_region is not None
                if isinstance(memory_region, HypervisorMemoryRegion):
                    continue

                if isinstance(memory_region, ShMemNetRegion):
                    continue

                assert isinstance(memory_region, MemoryRegionData)

                if (
                    memory_region.virtual_start_addr is not None
                    and memory_region.physical_start_addr is not None
                ):
                    if memory_region.allocatable:
                        continue

                    assert memory_region.size is not None
                    memory_constraint = MemoryConstraint(
                        size=int(memory_region.size),
                        virtual=True,
                        start_addr=memory_region.virtual_start_addr,
                    )

                    self.no_overlap_constraints[
                        cell_name
                    ].add_memory_constraint(memory_constraint)

        self._add_gic_constraints()

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
            for constr in no_overlap_constr.constraints:
                if not constr.allocated_range:
                    print(constr, "has not been allocated")
                    continue

                (start, _) = constr.allocated_range

                if constr.resolved:
                    constr.resolved(constr)

                if constr not in self.memory_constraints:
                    continue

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

    def _add_gic_constraints(self):
        interrupt_ranges: List[Tuple[int, int]] = []
        for interrupt_controller in self.board.interrupt_controllers:
            if interrupt_controller.gic_version == 2:
                interrupt_ranges.append(
                    (interrupt_controller.gicd_base, 0x1000)
                )
                interrupt_ranges.append(
                    (interrupt_controller.gicc_base, 0x2000)
                )
                interrupt_ranges.append(
                    (interrupt_controller.gich_base, 0x2000)
                )
                interrupt_ranges.append(
                    (interrupt_controller.gicv_base, 0x2000)
                )
            elif interrupt_controller.gic_version == 3:
                interrupt_ranges.append(
                    (interrupt_controller.gicd_base, 0x10000)
                )
                interrupt_ranges.append(
                    (interrupt_controller.gicr_base, 0x20000)
                )

        for name, constraint in self.no_overlap_constraints.items():
            for interrupt_range in interrupt_ranges:
                mc = MemoryConstraint(
                    size=interrupt_range[1],
                    start_addr=interrupt_range[0],
                    virtual=False if name == "__global" else True,
                )
                constraint.add_memory_constraint(mc)

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
                    if "MEM_EXECUTE" in copy_region.flags:
                        copy_region.flags.remove("MEM_EXECUTE")
                    if "MEM_DMA" in copy_region.flags:
                        copy_region.flags.remove("MEM_DMA")

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
        assert self.board is not None

        start = None
        end = 0

        allocatable_regions = []
        for region in self.board.memory_regions.values():
            assert region is not None
            if isinstance(region, MemoryRegionData) and region.allocatable:
                assert region.physical_start_addr is not None
                assert region.size is not None

                allocatable_regions.append(region)

                tmp_start = region.physical_start_addr
                tmp_end = region.physical_start_addr + region.size

                if start is None:
                    start = tmp_start

                if tmp_start < start:
                    start = tmp_start

                if tmp_end > end:
                    end = tmp_end

        allocatable_regions.sort(
            key=lambda r: r.physical_start_addr
            if r.physical_start_addr is not None
            else 0
        )
        holes: List[List[int]] = []

        for i in range(0, len(allocatable_regions) - 1):
            r0 = allocatable_regions[i]
            r1 = allocatable_regions[i + 1]

            assert r0.physical_start_addr is not None and r0.size is not None
            assert r1.physical_start_addr is not None

            r0_end = r0.physical_start_addr + r0.size
            r1_start = r1.physical_start_addr

            if r0_end != r1_start:
                holes.append([r0_end, r1_start])

        # Physical domain spans the entire range from the first allocatable memory region
        # to the end of the last one. Any holes in that range are accomodated for using
        # constant interval constraints
        def remove_hole(start, end):
            try:
                holes.remove([start, end])
            except ValueError:
                pass

        self.physical_domain = cp_model.Domain.FromIntervals([[start, end]])

        # Make sure all pre-allocated regions part of a cell have a corresponding
        # constraint (technically, we only need constraints for those regions that
        # overlapp with the allocatable range/physical domain)
        non_alloc_ranges: List[List[int]] = []
        assert self.config

        for cell in self.config.cells.values():
            assert cell.memory_regions

            for r in cell.memory_regions.values():
                if not isinstance(r, ShMemNetRegion) and not isinstance(
                    r, MemoryRegion
                ):
                    continue

                if r.physical_start_addr is not None:
                    assert r.size is not None

                    end = r.physical_start_addr + r.size
                    non_alloc_range = [r.physical_start_addr, end]

                    if non_alloc_range in non_alloc_ranges:
                        continue

                    if not self.physical_domain.Contains(
                        non_alloc_range[0]
                    ) and not self.physical_domain.Contains(non_alloc_range[1]):
                        continue

                    non_alloc_ranges.append(non_alloc_range)
                    remove_hole(r.physical_start_addr, end)

                    mc = MemoryConstraint(r.size, False, r.physical_start_addr)

                    self.global_no_overlap.add_memory_constraint(mc)

        # fill remaining holes in between allocatable regions
        for hole in holes:
            s, e = hole
            size = e - s

            mc = MemoryConstraint(size, False, s)
            self.global_no_overlap.add_memory_constraint(mc)

    def _remove_allocatable(self):
        """Finally remove allocatable memory regions from cells"""
        assert self.config is not None

        for cell in self.config.cells.values():
            delete_list = []
            for name, region in cell.memory_regions.items():
                if isinstance(region, MemoryRegionData):
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
            # see hypvervisor/pci.c:850
            end_bus = self.root_cell.platform_info.pci_mmconfig_end_bus
            vpci_size = (end_bus + 2) * 256 * 4096

            if self.root_cell.platform_info.pci_mmconfig_base:
                for constraints in self.no_overlap_constraints.values():
                    mc = MemoryConstraint(
                        vpci_size,
                        True,
                        self.root_cell.platform_info.pci_mmconfig_base,
                    )
                    constraints.add_memory_constraint(mc)
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

                    self.logger.info(
                        "Print resolved pci_mmconfig %s",
                        hex(physical_start_addr),
                    )

                # Allocate vpci physically
                last_mc = MemoryConstraint(
                    vpci_size, True
                )  # This is a physical constraint, but it does not need to be backed by allocatable memory
                last_mc.resolved = callback
                last_mc.alignment = self.board.pagesize
                last_mc.address_range = (0x0, 2 ** 32 - 1)
                self.no_overlap_constraints["__global"].add_memory_constraint(
                    last_mc
                )

                for cell_name in self.config.cells.keys():
                    mc = MemoryConstraint(vpci_size, True)
                    mc.equal_constraint = last_mc
                    self.no_overlap_constraints[
                        cell_name
                    ].add_memory_constraint(mc)
                    mc.alignment = self.board.pagesize

                    last_mc = mc


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
            Tuple[int, int], Tuple[int, List[MemoryRegionData]]
        ] = defaultdict(lambda: (0, []))

        for cell in self.cells.values():
            for region in cell.memory_regions.values():
                if not isinstance(region, MemoryRegionData):
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
                if not isinstance(region, MemoryRegionData):
                    continue
                if region.allocatable:
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

                    if region.physical_start_addr is None:
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
    """ Merge IO regions in root cell that are at most n kB apart.
    n defaults to 64 kb
    """

    def __init__(
        self,
        set_params: Optional[GenerateConfig],
        gen_params: Optional[GenerateParameters],
    ) -> None:
        self.config: Optional[JailhouseConfig] = None
        self.board: Optional[Board] = None
        self.root_cell: Optional[CellConfig] = None
        self.logger = logging.getLogger("autojail")
        self.max_dist = 64 * 1024

        if set_params:
            self.max_dist = set_params.mem_io_merge_threshold

        if gen_params:
            threshold_choice = ScalarChoice()
            threshold_choice.lower = 1024
            threshold_choice.upper = 64 * 1024 * 1024
            threshold_choice.step = 1024
            threshold_choice.integer = True
            threshold_choice.log = True

            gen_params.mem_io_merge_threshold = threshold_choice

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
        ) -> List[Tuple[str, Union[DeviceMemoryRegion, MemoryRegion]]]:
            return list(
                [
                    (name, r)
                    for name, r in regions.items()
                    if isinstance(r, MemoryRegionData) and "MEM_IO" in r.flags
                ]
            )

        regions: Sequence[Tuple[str, MemoryRegionData]] = get_io_regions(
            self.root_cell.memory_regions
        )
        regions = sorted(
            regions,
            key=lambda t: t[1].physical_start_addr
            if t[1].physical_start_addr is not None
            else 0,
        )

        grouped_regions: List[List[Tuple[str, MemoryRegionData]]] = []
        current_group: List[Tuple[str, MemoryRegionData]] = []

        max_dist = self.max_dist

        vpci_start_addr = None
        vpci_end_addr = None

        if (
            self.root_cell.platform_info is not None
            and self.root_cell.platform_info.pci_mmconfig_base is not None
            and self.root_cell.platform_info.pci_mmconfig_base > 0
        ):
            vpci_start_addr = self.root_cell.platform_info.pci_mmconfig_base
            vpci_end_addr = (
                vpci_start_addr
                + (self.root_cell.platform_info.pci_mmconfig_end_bus + 1)
                * 256
                * 4096
            )

        for name, r in regions:
            assert r.physical_start_addr is not None
            assert r.size is not None

            if current_group:
                r1_end = r.physical_start_addr + r.size
                r1_start = r.physical_start_addr

                assert current_group[-1][1].physical_start_addr is not None
                assert current_group[-1][1].size is not None
                assert current_group[0][1].physical_start_addr is not None

                last_region_end = (
                    current_group[-1][1].physical_start_addr
                    + current_group[-1][1].size
                )

                # Do not merge regions if merged regions would
                # overlap with gic
                gic_overlap = False
                interrupt_ranges = []

                for interrupt_controller in board.interrupt_controllers:
                    if interrupt_controller.gic_version == 2:
                        interrupt_ranges.append(
                            (interrupt_controller.gicd_base, 0x1000)
                        )
                        interrupt_ranges.append(
                            (interrupt_controller.gicc_base, 0x2000)
                        )
                        interrupt_ranges.append(
                            (interrupt_controller.gich_base, 0x2000)
                        )
                        interrupt_ranges.append(
                            (interrupt_controller.gicv_base, 0x2000)
                        )
                    elif interrupt_controller.gic_version == 3:
                        interrupt_ranges.append(
                            (interrupt_controller.gicd_base, 0x10000)
                        )
                        interrupt_ranges.append(
                            (interrupt_controller.gicr_base, 0x20000)
                        )

                for interrupt_range in interrupt_ranges:
                    if (
                        current_group[0][1].physical_start_addr
                        < interrupt_range[0] + interrupt_range[1]
                    ):
                        if r1_end > interrupt_range[0]:
                            gic_overlap = True
                            break

                vpci_overlap = False
                if vpci_start_addr is not None and vpci_end_addr is not None:
                    if (
                        get_overlap(
                            (r1_start, r1_end), (vpci_start_addr, vpci_end_addr)
                        )
                        > 0
                    ):
                        vpci_overlap = True

                if (
                    r1_start - last_region_end > max_dist
                    or gic_overlap
                    or vpci_overlap
                ):
                    grouped_regions.append(current_group)

                    if not gic_overlap and not vpci_overlap:
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
            assert group[0][1].physical_start_addr is not None
            assert group[-1][1].physical_start_addr is not None
            assert group[-1][1].size is not None

            group_begin = group[0][1].physical_start_addr
            group_end = group[-1][1].physical_start_addr + group[-1][1].size

            self.logger.info(
                f"Group-Begin: (0x{group_begin:x} - 0x{group_end:x})"
            )
            for region in group:
                self.logger.info(f"\t{region}")

            self.logger.info("Group-End\n")

        for index, regions in enumerate(grouped_regions):
            r_start = regions[0][1]
            r_end = regions[-1][1]

            assert r_start.physical_start_addr is not None
            assert r_end.size is not None
            assert r_end.physical_start_addr is not None

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
                if isinstance(region, MemoryRegionData) and region.size is None:
                    region.size = self.board.pagesize

            if cell.type == "root":
                self._prepare_memory_regions_root(cell)

        return self.board, self.config

    def _prepare_memory_regions_root(self, cell: CellConfig) -> None:
        assert self.board is not None
        assert self.board.memory_regions is not None
        assert cell.memory_regions is not None

        allocatable_ranges = []
        for region in self.board.memory_regions.values():
            if region.allocatable:
                assert region.size is not None
                assert region.physical_start_addr is not None

                start = region.physical_start_addr
                end = start + region.size

                allocatable_ranges.append([start, end])

        allocatable_ranges.sort(key=lambda r: r[0])

        def overlaps_allocatable_region(start, end):
            for r in allocatable_ranges:
                if (
                    r[0] <= start
                    and start <= r[1]
                    or r[0] <= end
                    and end <= r[1]
                ):
                    return True

            return False

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

            if overlaps_allocatable_region(p_start, p_end):
                continue

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
