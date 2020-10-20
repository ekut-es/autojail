from typing import Union

from ..commands.base import BaseCommand
from ..model import (
    Board,
    CellConfig,
    DebugConsole,
    HypervisorMemoryRegion,
    JailhouseConfig,
    MemoryRegion,
)


class ConfigWizard:
    def __init__(self, command: BaseCommand, board: Board):
        self.command = command
        self.board = board
        self.config = None

    def run(self):
        root_wizard = RootConfigWizard(self.board)
        self.config = root_wizard.run()


class RootConfigWizard:
    """ Creates a simple root cell configuration similar to the following 

        The configuration corresponds to the following config:

        cells:
            root:
                type: root 
                name: "Raspberry PI4"
                flags: [SYS_VIRTUAL_DEBUG_CONSOLE]

                hypervisor_memory:
                  size: 16 MB

                debug_console: serial0 

                cpus: 0-3

                memory_regions:
                    Main Memory:
                        size: 768 MB
                        flags: [MEM_READ, MEM_WRITE, MEM_EXECUTE, MEM_DMA]
    """  # noqa

    def __init__(self, board: Board):
        self.board = board

    def run(self) -> JailhouseConfig:
        name = "Root Cell"
        flags = ["SYS_VIRTUAL_DEBUG_CONSOLE"]
        hypervisor_memory = HypervisorMemoryRegion(size="16 MB")

        debug_console: Union[str, DebugConsole] = ""
        if self.board.stdout_path:
            console_name = self.board.stdout_path.split(":")[0]
            debug_console = console_name
        else:
            debug_console = DebugConsole(
                type="CON_TYPE_NONE", address=0x0, size=0x0, flags=[]
            )

        cpus = list(range(len(self.board.cpuinfo)))

        main_memory = MemoryRegion(
            size="768 MB",
            flags=["MEM_READ", "MEM_WRITE", "MEM_EXECUTE", "MEM_DMA"],
        )

        cell_config = CellConfig(
            name=name,
            type="root",
            flags=flags,
            hypervisor_memory=hypervisor_memory,
            debug_console=debug_console,
            cpus=cpus,
            memory_regions={"Main Memory": main_memory},
        )
        config = JailhouseConfig(cells={"root": cell_config})

        return config
