from pathlib import Path

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """Create the Jailhouse configurations

    config
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
