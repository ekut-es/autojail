from pathlib import Path

import ruamel.yaml

from .base import BaseCommand
from ..extract import BoardConfigurator
from ..model import Board


class ConfigCommand(BaseCommand):
    """Create the Jailhouse configurations

    config
    """

    def handle(self):
        cells_yml_path = Path.cwd() / self.CELLS_CONFIG_NAME

        if not cells_yml_path.exists():
            self.line(f"<error>{cells_yml_path} could not be found</error>")
            return -1

        board_yml_path = Path.cwd() / self.BOARD_CONFIG_NAME
        if not board_yml_path.exists():
            self.line(f"<error>{board_yml_path} could not be found</error>")
            self.line(f"Please run <comment>automate extract</comment> first")
            return -1

        with board_yml_path.open() as f:
            yaml = ruamel.yaml.YAML()
            board_dict = yaml.load(f)
            board_info = Board(**board_dict)

        testwriter = BoardConfigurator(board_info)
        testwriter.read_cell_yml(str(cells_yml_path))
        testwriter.prepare()
        testwriter.write_config("./")
