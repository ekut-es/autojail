from typing import Optional

from ..model.parameters import GenerateConfig, GenerateParameters, Partitions
from .passes import BasePass


class CPUAllocatorPass(BasePass):
    def __init__(
        self,
        set_params: Optional[GenerateConfig],
        gen_params: Optional[GenerateParameters],
    ):
        self.set_parameters = set_params
        self.gen_params = gen_params
        super(CPUAllocatorPass, self).__init__()

    def __call__(self, board, config):
        reserved_cpus = set()

        def get_next_available_cpu():
            for i in range(len(board.cpuinfo)):
                if i not in reserved_cpus:
                    return i

            raise KeyError()

        num_cpus = len(board.cpuinfo)
        no_cpus_total = 0

        for cell in config.cells.values():
            if cell.type != "root":
                cell_cpus = cell.cpus
                if not cell_cpus:
                    no_cpus_total += 1

                reserved_cpus.update(cell.cpus)

        if self.gen_params and no_cpus_total > 0:
            avail_cpus = {i for i in range(len(board.cpuinfo))} - reserved_cpus
            assert len(avail_cpus) >= no_cpus_total + 1

            root_reserved = get_next_available_cpu()
            avail_cpus.remove(root_reserved)

            partitions = Partitions()
            partitions.choices = list(avail_cpus)
            partitions.partitions = no_cpus_total
            partitions.ordered = True

            self.gen_params.cpu_allocation = partitions

        no_cpus_index = 0
        for cell in config.cells.values():
            if not cell.cpus:
                if cell.type == "root":
                    cell.cpus = list(range(0, num_cpus))
                else:
                    if self.set_parameters:
                        assert (
                            len(self.set_parameters.cpu_allocation)
                            > no_cpus_index
                        )

                        cell_cpus = self.set_parameters.cpu_allocation[
                            no_cpus_index
                        ]
                        assert (
                            reserved_cpus.isdisjoint(cell_cpus)
                            and "Invalid state detected: passed CPU allocation parameters conflict with CPU allocations defined in cells.yml"
                        )
                        cell.cpus = cell_cpus
                    else:
                        cell_cpu = get_next_available_cpu()
                        reserved_cpus.add(cell_cpu)
                        cell.cpus = [cell_cpu]

                no_cpus_index += 1
                assert len(cell.cpus) > 0

        return board, config
