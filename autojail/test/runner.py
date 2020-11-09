from pathlib import Path
from typing import Union

from ruamel.yaml import YAML

from ..model.test import TestConfig
from ..utils.logging import getLogger


class TestRunner:
    def __init__(self, config: Union[Path, str]) -> None:
        config = Path(config)

        with config.open("r") as config_file:
            yaml = YAML()
            config_dict = yaml.load(config_file)
            self.config = TestConfig(**config_dict)

        self.logger = getLogger()

    def run(self) -> None:
        try:
            self._run_start()
        except Exception:
            self._run_reset()

        try:
            self._run_stop()
        except Exception:
            self._run_reset()

    def _run_start(self):
        for command in self.start_script:
            self.run_command(command, default_target="local")

    def _run_reset(self):
        for command in self.reset_script:
            self.run_command(command, default_target="local")

    def _run_stop(self):
        for command in self.stop_script:
            self.run_command(command, default_target="local")
