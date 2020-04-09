from pathlib import Path

import ruamel.yaml

from cleo import Command

from ..model import AutojailConfig

automate_available = False
try:
    import automate

    automate_available = True
except ImportError:
    automate_available = False


class BaseCommand(Command):
    CONFIG_NAME = "autojail.yml"
    CELLS_CONFIG_NAME = "cells.yml"
    BOARD_CONFIG_NAME = "board.yml"

    def __init__(self):
        super().__init__()

        self.autojail_config = None
        self.config_path = Path.cwd() / self.CONFIG_NAME
        if self.config_path.exists():
            with self.config_path.open() as f:
                yaml = ruamel.yaml.YAML()
                config_dict = yaml.load(f)
                self.autojail_config = AutojailConfig(**config_dict)

        self.automate_context = None
        if automate_available:
            automate_config = automate.AutomateConfig()
            self.automate_context = automate.AutomateContext(automate_config)
