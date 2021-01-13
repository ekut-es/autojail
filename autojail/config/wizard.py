from typing import FrozenSet, Optional, Union

from dataclasses import dataclass, field

from autojail.model.datatypes import IntegerList

from ..commands.base import BaseCommand
from ..model import (
    Board,
    ByteSize,
    CellConfig,
    DebugConsole,
    HypervisorMemoryRegion,
    JailhouseConfig,
    MemoryRegion,
)


@dataclass()
class RootConfigArgs:
    name: str = "root cell"
    memory: ByteSize = ByteSize.validate("512 MB")
    hypervisor_memory: ByteSize = ByteSize.validate("8 MB")
    console: Optional[str] = None
    flags: FrozenSet[str] = frozenset()


class WizardBase:
    def __init__(self, command: BaseCommand, board: Board):
        self.command = command
        self.board = board


class RootConfigWizard(WizardBase):
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

    def run(self, args: RootConfigArgs) -> JailhouseConfig:
        name = args.name
        flags = (
            args.flags
            if args.flags is not None
            else ["SYS_VIRTUAL_DEBUG_CONSOLE"]
        )
        hypervisor_memory = HypervisorMemoryRegion(size=args.hypervisor_memory)

        debug_console: Union[str, DebugConsole] = DebugConsole(
            type="CON_TYPE_NONE", address=0x0, size=0x0, flags=[]
        )
        if args.console is None:
            if self.board.stdout_path:
                console_name = self.board.stdout_path.split(":")[0]
                debug_console = console_name
        elif args.console:
            debug_console = args.console

        cpus = list(range(len(self.board.cpuinfo)))

        main_memory = MemoryRegion(
            size=args.memory,
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


@dataclass
class InmateConfigArgs:
    name: str = "guest"
    type: str = "linux"
    memory: ByteSize = ByteSize.validate("512 MB")
    console: Optional[str] = None
    flags: FrozenSet[str] = frozenset()
    devices: FrozenSet[str] = frozenset()
    cpus: IntegerList = field(default_factory=IntegerList)


class InmateConfigWizard(WizardBase):
    def add(
        self, args: InmateConfigArgs, config: JailhouseConfig
    ) -> JailhouseConfig:

        return config

    def remove(self, name: str, config: JailhouseConfig) -> JailhouseConfig:
        for id, cell in config.cells.items():
            if id == name or cell.name == name:
                if cell.type == "root":
                    raise Exception(
                        "Cannot remove root cell from jailhouse config"
                    )
                del config.cells["id"]
                return config

        raise Exception(f"Could not find cell with name or id {name}")
