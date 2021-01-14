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

    def _run_script(self, script):
        for command in script:
            print(command)

    def _run_command(self, command) -> int:
        print(command)
        return 0

    def _run_start(self):
        self._run_script(self.start_script)

    def _run_reset(self):
        self._run_script(self.reset_script)

    def _run_stop(self):
        self._run_script(self.stop_script)
