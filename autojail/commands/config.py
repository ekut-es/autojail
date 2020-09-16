from pathlib import Path

from ..config import ConfigWizard
from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """Create the Jailhouse configurations

    config
    """

    def handle(self) -> None:
        board_yml_path = Path.cwd() / self.BOARD_CONFIG_NAME
        if not board_yml_path.exists():
            self.line(f"<error>{board_yml_path} could not be found</error>")
            self.line("Please run <comment>automate extract</comment> first")
            return None

        wizard = ConfigWizard(self, board_yml_path)
        wizard.run()
        wizard.save()
