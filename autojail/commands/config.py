import logging

import ruamel.yaml

from autojail.model.jailhouse import JailhouseConfig

from ..config import (
    InmateConfigArgs,
    InmateConfigWizard,
    RootConfigArgs,
    RootConfigWizard,
)
from ..model.datatypes import (
    ByteSize,
    ExpressionInt,
    HexInt,
    IntegerList,
    JailhouseFlagList,
)
from .base import BaseCommand


class ConfigCommandBase(BaseCommand):
    def _save_jailhouse_config(self, config: JailhouseConfig):
        if config is not None:
            with self.cells_config_path.open("w") as f:
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


class InitCommand(ConfigCommandBase):
    """ Initialize a jailhouse configuration 
    
    init
        {--f|force : if set overwrites existing cells.yml}
        {--r|root-name= : name of root cell}
        {--m|root-memory= : amount of memory for root cell} 
        {--hypervisor-memory= : amount of memory for hypervisor}
        {--c|console= : device tree path or alias of debug uart}
        {--flags= : Jailhouse flags for root cell}
    """  # noqa

    def _parse_args(self) -> RootConfigArgs:

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
        args = self._parse_args()
        if self.cells_config_path.exists() and not self.option("force"):
            self.line(
                f"{self.cells_config_path} already exists use -f to overwrite"
            )

        board_info = self.load_board_info()
        if not board_info:
            return

        wizard = RootConfigWizard(self, board_info)
        config = wizard.run(args)

        self._save_jailhouse_config(config)


class AddCommand(ConfigCommandBase):
    """ Add a inmate to the configuration 
    
    add
        {name : name of cell}
        {--t|type= : type of cell one of "bare", "linux"}
        {--m|memory= : amount of memory for inmate} 
        {--c|console= : device tree path or alias of debug uart}
        {--F|flags= : jailhouse flags for guest cell}
        {--d|device= : device to add to inmate device tree path or alias}
        {--C|cpus= : comma separated list of cpus for inmate}
    """  # noqa

    def _parse_args(self):
        name = self.argument("name")
        type = self.option("type")
        memory = self.option("memory")
        console = self.option("console")
        flags = self.option("flags")
        devices = self.option("device")
        cpus = self.option("cpus")

        args = InmateConfigArgs(name=name)
        if type is not None:
            assert type in ["linux", "bare"]
            args.type = type

        if memory is not None:
            args.memory = ByteSize.validate(memory)

        if console is not None:
            args.console = console

        if flags is not None:
            args.flags = frozenset(flags.split(","))

        if devices is not None:
            args.devices = devices

        if cpus is not None:
            args.cpus = IntegerList.validate(cpus)

        return args

    def handle(self):
        args = self._parse_args()
        board_info = self.load_board_info()
        if not board_info:
            return

        jailhouse_config = self.load_jailhouse_config()

        wizard = InmateConfigWizard(self, board_info)
        config = wizard.add(args, jailhouse_config)
        self._save_jailhouse_config(config)


class RemoveCommand(ConfigCommandBase):
    """ Delete a guest cell from the configuration 
    
    remove
        {name : Name of Cell to remove}
    """  # noqa

    def handle(self):
        name = self.argument("name")
        board_info = self.load_board_info()
        if not board_info:
            return

        jailhouse_config = self.load_jailhouse_config()
        wizard = InmateConfigWizard(self, board_info)
        config = wizard.remove(name, jailhouse_config)
        self._save_jailhouse_config(config)


class ConfigCommand(ConfigCommandBase):
    """Create Jailhouse configurations

    config
    """  # noqa

    commands = [InitCommand(), AddCommand(), RemoveCommand()]

    def handle(self) -> int:
        # FIXME replace in v0.3 with:
        # return logging.warning("directly calling jailhouse config has been deprecated")

        logging.warning(
            "directly calling 'jailhouse config' has been deprecated and will be removed in the next version"
        )
        logging.warning("please use 'jailhouse config init' instead")

        args = RootConfigArgs()
        if self.cells_config_path.exists() and not self.option("force"):
            self.line(
                f"{self.cells_config_path} already exists use -f to overwrite"
            )

        board_info = self.load_board_info()
        if not board_info:
            return 1

        wizard = RootConfigWizard(self, board_info)
        config = wizard.run(args)

        self._save_jailhouse_config(config)

        return 0
