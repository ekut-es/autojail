from pathlib import Path
from ..model import Board, MemoryRegion


class BoardInfoExtractor:
    def __init__(self, name, board, data_root):
        self.name = name
        self.board = board
        self.data_root = Path(data_root)

    def read_iomem(self, filename):
        with open(filename, "r") as iomem_info:

            start_addr = 0
            end_addr = 0
            size_calculated = 0
            temp = 0
            compare_count = 2
            physical_start_addr = []

            size = []
            memory_regions = []
            res = 1
            res2 = 1
            for x in iomem_info:
                start_addr, temp, *rest = x.split("-", 1)
                temp = temp.strip()
                start_addr = start_addr.strip()
                physical_start_addr.append(start_addr)
                end_addr, temp = temp.split(":")

                end_addr = end_addr.split(" ", 1)[0]
                # end_addr_list.append(end_addr)
                size_calculated = int(end_addr, 16) - int(start_addr, 16)
                size.append(size_calculated)

                temp = temp.strip()
                res = any(temp in sublist for sublist in memory_regions)
                compare_count = 1
                if res == 0:
                    memory_regions.append(temp)
                else:
                    while res != 0:
                        if res != 0:
                            compare_count += 1
                            if (
                                temp[-1].isdigit() == 1
                                or temp[-2].isdigit() == 1
                                and temp[-2] == "_"
                                or temp[-3] == "_"
                            ):
                                temp = temp.rsplit("_", 1)[0]
                                temp = temp.strip() + "_" + str(compare_count)
                            else:
                                temp = temp.strip() + "_" + str(compare_count)
                            res2 = any(
                                temp in sublist for sublist in memory_regions
                            )
                            if res2 == 0:
                                memory_regions.append(temp)

                                res = 0
                            else:
                                res = 1
        mem_regs = {}
        for i, name in enumerate(memory_regions):
            memory_region = MemoryRegion(
                physical_start_addr=int(physical_start_addr[i], 16),
                virtual_start_addr=int(physical_start_addr[i], 16),
                size=size[i],
                flags=["MEM_READ"],
            )
            mem_regs[name] = memory_region

        return mem_regs

    def extract(self):
        memory_regions = self.read_iomem(self.data_root / "proc" / "iomem")

        board = Board(
            name=self.name, board=self.board, memory_regions=memory_regions
        )
        return board


if __name__ == "__main__":
    from devtools import debug
    import sys

    extractor = BoardInfoExtractor(sys.argv[1], sys.argv[2], sys.argv[3])
    board_info = extractor.extract()

    debug(board_info)
