from pathlib import Path

import ruamel.yaml

from ..config import RootConfigArgs, RootConfigWizard
from ..model import Board
from ..model.datatypes import (
    ByteSize,
    ExpressionInt,
    HexInt,
    IntegerList,
    JailhouseFlagList,
)
from .base import BaseCommand


class InitCommand(BaseCommand):
    """ Initialize a jailhouse configuration 
    
    init
        {--f|force : if set overwrites existing cells.yml}
        {--r|root-name= : name of root cell}
        {--m|root-memory= : amount of memory for root cell} 
        {--hypervisor-memory= : amount of memory for hypervisor}
        {--c|console= : device tree path or alias of debug uart}
        {--flags= : Jailhouse flags for root cell}
    """  # noqa

    def _read_args(self) -> RootConfigArgs:

        name = self.option("root-name")
        memory = self.option("root-memory")
        hypervisor_memory = self.option("hypervisor-memory")
        console = self.option("console")
        flags = self.option("flags")

        args = RootConfigArgs()
        if name is not None:
            args.name = name

        if memory is not None:
            args.memory = ByteSize.validate(memory)

        if hypervisor_memory is not None:
            args.hypervisor_memory = ByteSize.validate(hypervisor_memory)

        if console is not None:
            args.console = console

        if flags is not None:
            args.flags = flags.split(",")

        return args

    def handle(self) -> None:
        args = self._read_args()
        cells_yml_path = Path.cwd() / self.CELLS_CONFIG_NAME
        if cells_yml_path.exists() and not self.option("force"):
            self.line(f"{cells_yml_path} already exists use -f to overwrite")

        board_yml_path = Path.cwd() / self.BOARD_CONFIG_NAME
        if not board_yml_path.exists():
            self.line(f"<error>{board_yml_path} could not be found</error>")
            self.line("Please run <comment>automate extract</comment> first")
            return None

        with board_yml_path.open() as f:
            yaml = ruamel.yaml.YAML()
            board_dict = yaml.load(f)
            board_info = Board(**board_dict)

        wizard = RootConfigWizard(self, board_info)
        config = wizard.run(args)

        if config is not None:
            with cells_yml_path.open("w") as f:
                yaml = ruamel.yaml.YAML()
                yaml.register_class(HexInt)
                yaml.register_class(ByteSize)
                yaml.register_class(IntegerList)
                yaml.register_class(JailhouseFlagList)
                yaml.register_class(ExpressionInt)

                cells_dict = config.dict(
                    exclude_unset=True, exclude_defaults=True
                )
                yaml.dump(cells_dict, f)


class AddCommand(BaseCommand):
    """ Add a guest cell to the configuration 
    
    add
    """  # noqa

    pass


class RemoveCommand(BaseCommand):
    """ Delete a guest cell from the configuration 
    
    remove
    """  # noqa

    pass


class ConfigCommand(BaseCommand):
    """Create Jailhouse configurations

    config
    """  # noqa

    commands = [InitCommand(), AddCommand(), RemoveCommand()]

    def handle(self):  # type: () -> int
        return self.call("help", self._config.name)
