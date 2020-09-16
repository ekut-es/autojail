from pathlib import Path

from ..commands.base import BaseCommand


class ConfigWizard:
    def __init__(self, command: BaseCommand, board_yaml_path: Path):
        self.command = command
        self.board_yaml_path = board_yaml_path

    def run(self):
        pass

    def save(self):
        pass
