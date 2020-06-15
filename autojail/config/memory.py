import bisect
import copy

from collections import defaultdict

from .passes import BasePass

from ..model import MemoryRegion


class PrepareMemoryRegionsPass(BasePass):
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


class AllocateMemoryPass(BasePass):
    def __init__(self):
        self.config = None
        self.board = None

    def __call__(self, board, config):
        self.board = board
        self.config = config

        self._allocate_memory()

        return self.board, self.config

    def _allocate_memory(self):
        root = self.config.cells["root"]

        # virtual_alloc_ranges: map from cell name to
        # sorted list of pairs: (virtual_start_address, virtual_end_address)
        virtual_alloc_ranges = defaultdict(list)

        allocatable_memory = sorted(
            map(
                lambda x: x[1],
                filter(lambda x: x[1].allocatable, root.memory_regions.items()),
            ),
            key=lambda x: x.physical_start_addr + x.size,
            reverse=True,
        )

        if not len(allocatable_memory):
            raise Exception(
                "Invalid cells.yaml: No allocatable memory specified"
            )

        def get_virtual_mem(start, size, cell_name):
            ranges = virtual_alloc_ranges[cell_name]

            if not ranges:
                return start

            range_req = (start, start + size)

            def ranges_overlap(r1, r2):
                start1, end1 = r1
                start2, end2 = r2

                if (
                    (start1 <= start2 and start2 < end1)
                    or (start1 < end2 and end2 < end1)
                    or (start2 <= start1 and start1 < end2)
                    or (start2 < end1 and end1 < end2)
                ):
                    print(
                        f"Ranges overlap: (0x{r1[0]:x}, 0x{r1[1]:x}) and (0x{r2[0]:x}, 0x{r2[1]:x})"
                    )
                    return True

                return False

            for ref_start, ref_end in ranges:
                if ranges_overlap(range_req, (ref_start, ref_end)):
                    range_req = (ref_end, size)

            return range_req[0]

        def get_physical_mem(size):
            mem = None
            for i in range(len(allocatable_memory)):
                if allocatable_memory[i].size >= size:
                    mem = i
                    break

            if mem is None:
                raise Exception(
                    "Invalid cells.yml: Not enough allocatable memory available"
                )

            allocatable_region = allocatable_memory[mem]
            start_addr, total_size = (
                allocatable_region.physical_start_addr,
                allocatable_region.size,
            )
            ret_addr = start_addr + total_size - size

            total_size -= size

            allocatable_memory[mem].size = total_size
            if total_size <= 0:
                del allocatable_memory[mem]

            return ret_addr

        # get allocated virtual regions and unallocated
        # physical regions
        # maps region name to a list of pairs: (region, cell name)

        # FIXME: allocating the same physical address across cells
        # for same-named memory regions breaks RAM regions
        unallocated_regions = defaultdict(list)
        for cell_name, cell in self.config.cells.items():
            for region_name, region in cell.memory_regions.items():
                if (
                    region.virtual_start_addr is not None
                    and region.size is not None
                    and not region.allocatable
                ):
                    mem_range = (
                        region.virtual_start_addr,
                        region.virtual_start_addr + region.size,
                    )
                    bisect.insort(virtual_alloc_ranges[cell_name], mem_range)

                if region.physical_start_addr is None:
                    unallocated_regions[region_name].append((region, cell_name))

        # sort regions such that those, that are not
        # referenced via 'next_region' come first
        def is_a_next_region(name):
            for _, lst in unallocated_regions.items():
                region = lst[0][0]

                if name == region.next_region:
                    return True

            return False

        # allocate unallocated regions
        keys_in_order = sorted(
            unallocated_regions.keys(),
            key=lambda x: 1 if is_a_next_region(x) else -1,
        )

        # TODO add all unallocated regions that are not
        # part of the root cell, to the root cell
        # Do cross-cell region identification name-based
        for region_name, lst in unallocated_regions.items():
            if region_name not in root.memory_regions:
                new_root_regions = list()
                for region, cell_name in lst:
                    new_region = copy.deepcopy(region)

                    root.memory_regions[
                        f"{cell_name}_{region_name}"
                    ] = new_region
                    new_root_regions.append((new_region, root.name))

                lst += new_root_regions

        regions = None
        while unallocated_regions:
            if not regions:
                name = keys_in_order.pop(0)
                regions = unallocated_regions[name]

            linked_regions = dict()
            region_size = -1

            for region, cell_name in regions:
                linked_region = [(name, region)]
                current_size = region.size

                while region.next_region:
                    name = region.next_region
                    region = list(
                        filter(
                            lambda x: x[1] == cell_name,
                            unallocated_regions[name],
                        )
                    )[0][0]

                    current_size += region.size
                    linked_region.append((name, region))

                if region_size < 0:
                    region_size = current_size
                elif region_size != current_size:
                    raise Exception(
                        "Invalid cells.yml: linked regions not consistent accross cells"
                    )

                linked_regions[cell_name] = linked_region

            physical_start_addr = get_physical_mem(region_size)

            for cell_name, linked_region in linked_regions.items():
                virtual_start_address = None

                if linked_region[0][1].virtual_start_addr is None:
                    virtual_start_address = get_virtual_mem(
                        physical_start_addr, region_size, cell_name
                    )
                    virtual_range = (
                        virtual_start_address,
                        virtual_start_address + region.size,
                    )
                    bisect.insort(
                        virtual_alloc_ranges[cell_name], virtual_range
                    )

                phy_start_addr = physical_start_addr
                for name, region in linked_region:
                    region.physical_start_addr = phy_start_addr

                    if virtual_start_address:
                        region.virtual_start_addr = virtual_start_address
                        virtual_start_address += region.size

                    phy_start_addr += region.size

                    # remove region in case it was not popped
                    # from the beginning of unallocated_regions
                    if name in unallocated_regions:
                        del unallocated_regions[name]

                    if name in keys_in_order:
                        keys_in_order.remove(name)

            regions = None
