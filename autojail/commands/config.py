from pathlib import Path

import ruamel.yaml

from ..config import ConfigWizard
from ..model import Board
from ..model.datatypes import (
    ByteSize,
    ExpressionInt,
    HexInt,
    IntegerList,
    JailhouseFlagList,
)
from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """Create the Jailhouse configurations

    config
        {--f|force : if set overwrites existing cells.yml}
    """  # noqa

    def handle(self) -> None:
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

        wizard = ConfigWizard(self, board_info)
        wizard.run()

        if wizard.config is not None:
            with cells_yml_path.open("w") as f:
                yaml = ruamel.yaml.YAML()
                yaml.register_class(HexInt)
                yaml.register_class(ByteSize)
                yaml.register_class(IntegerList)
                yaml.register_class(JailhouseFlagList)
                yaml.register_class(ExpressionInt)

                cells_dict = wizard.config.dict(
                    exclude_unset=True, exclude_defaults=True
                )
                yaml.dump(cells_dict, f)
