from typing import Optional

from ..model.parameters import GenerateConfig
from .passes import BasePass


class CPUAllocatorPass(BasePass):
    def __init__(self, params: Optional[GenerateConfig]):
        self.parameters = params
        super(CPUAllocatorPass, self).__init__()

    def __call__(self, board, config):
        reserved_cpus = set()
        num_cpus = len(board.cpuinfo)

        for cell in config.cells.values():
            if cell.type != "root":
                reserved_cpus.update(cell.cpus)

        for cell_name, cell in config.cells.items():
            if not cell.cpus:
                if cell.type == "root":
                    cell.cpus = list(range(0, num_cpus))
                else:
                    if (
                        self.parameters
                        and cell_name in self.parameters.cpu_allocation
                    ):
                        cell_cpus = self.parameters.cpu_allocation[cell_name]
                        assert (
                            reserved_cpus.isdisjoint(cell_cpus)
                            and "Invalid state detected: passed CPU allocation parameters conflict with CPU allocations defined in cells.yml"
                        )
                        cell.cpus = cell_cpus
                    else:
                        for i in range(len(board.cpuinfo)):
                            if i not in reserved_cpus:
                                reserved_cpus.add(i)
                                cell.cpus = [i]
                                break
                assert len(cell.cpus) > 0

        return board, config
