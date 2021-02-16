from typing import Tuple

from ..model import Board, JailhouseConfig, MemoryRegionData
from ..utils import get_overlap
from .passes import BasePass


class InferRootSharedPass(BasePass):
    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        root_cell = None
        for cell in config.cells.values():
            if cell.type == "root":
                root_cell = cell
                break

        if root_cell is None:
            self.logger.warning("Could not find root cell")
            return board, config

        assert root_cell.memory_regions is not None

        for cell in config.cells.values():
            assert cell.memory_regions is not None

            if cell.type == "root":
                continue

            for name, region in cell.memory_regions.items():
                if not isinstance(region, MemoryRegionData):
                    continue
                for root_name, root_region in root_cell.memory_regions.items():
                    if not isinstance(root_region, MemoryRegionData):
                        continue

                    assert region.physical_start_addr is not None
                    assert region.size is not None

                    assert root_region.physical_start_addr is not None
                    assert root_region.size is not None

                    overlap = get_overlap(
                        (
                            region.physical_start_addr,
                            region.physical_start_addr + region.size,
                        ),
                        (
                            root_region.physical_start_addr,
                            root_region.physical_start_addr + root_region.size,
                        ),
                    )
                    if overlap > 0:
                        if (
                            "MEM_ROOTSHARED" not in region.flags
                            and "MEM_LOADABLE" not in region.flags
                        ):
                            self.logger.warning(
                                "Memory region %s overlaps with region %s in root cell",
                                name,
                                root_name,
                            )
                            self.logger.warning(
                                "Assuming MEM_ROOTSHARED is missing"
                            )

                            region.flags.append("MEM_ROOTSHARED")

        return board, config
