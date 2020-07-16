from .passes import BasePass


class CPUAllocatorPass(BasePass):
    def __call__(self, board, config):
        reserved_cpus = set()
        num_cpus = len(board.cpuinfo)

        for cell in config.cells.values():
            if cell.type != "root":
                reserved_cpus.update(cell.cpus)

        for cell in config.cells.values():
            if not cell.cpus:
                if cell.type == "root":
                    cell.cpus = list(range(0, num_cpus))
                else:
                    for i in range(len(board.cpuinfo)):
                        if i not in reserved_cpus:
                            reserved_cpus.add(i)
                            cell.cpus = [i]

        return board, config
