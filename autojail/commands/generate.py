from pathlib import Path

import ruamel.yaml

from ..config import JailhouseConfigurator
from ..model import Board
from .base import BaseCommand


class GenerateCommand(BaseCommand):
    """Generate the Jailhouse configurations

    generate
    """

    def handle(self) -> None:
        cells_yml_path = Path.cwd() / self.CELLS_CONFIG_NAME

        if not cells_yml_path.exists():
            self.line(f"<error>{cells_yml_path} could not be found</error>")
            return None

        board_yml_path = Path.cwd() / self.BOARD_CONFIG_NAME
        if not board_yml_path.exists():
            self.line(f"<error>{board_yml_path} could not be found</error>")
            self.line("Please run <comment>automate extract</comment> first")
            return None

        with board_yml_path.open() as f:
            yaml = ruamel.yaml.YAML()
            board_dict = yaml.load(f)
            board_info = Board(**board_dict)

        configurator = JailhouseConfigurator(board_info)
        configurator.read_cell_yml(str(cells_yml_path))
        configurator.prepare()
        configurator.write_config("./")