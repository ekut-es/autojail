import shlex
import subprocess

from ..model.board import Board
from ..model.config import AutojailConfig
from ..model.jailhouse import JailhouseConfig
from ..model.test import TestConfig
from ..utils.logging import getLogger


class TestRunner:
    def __init__(
        self,
        autojail_config: AutojailConfig,
        board_info: Board,
        jailhouse_config: JailhouseConfig,
        test_config: TestConfig,
    ) -> None:
        self.autojail_config = autojail_config
        self.board_info = board_info
        self.jailhouse_config = jailhouse_config
        self.test_config = test_config

        self.logger = getLogger()

    def run(self) -> None:
        try:
            self._run_start()
        except Exception:
            self.logger.critical("Could not start target, trying reset ...")
            self._run_reset()

        try:
            self._run_stop()
        except Exception:
            self.logger.critical("Could not stop target, trying reset ...")
            self._run_reset()

    def _run_script(self, script):
        for command in script:
            self._run_command(command)

    def _run_command(self, command) -> int:
        self.logger.info("Running: %s", str(command))
        retval = subprocess.run(shlex.split(command))
        return retval.returncode

    def _run_start(self):
        self._run_script(self.autojail_config.start_command)

    def _run_reset(self):
        if self.autojail_config.reset_command:
            self._run_script(self.autojail_config.reset_command)
        else:
            self.logger.warning(
                "No reset command given trying stop, followed by start"
            )
            self._run_script(self.autojail_config.stop_command)
            self._run_script(self.autojail_config.start_command)

    def _run_stop(self):
        self._run_script(self.autojail_config.stop_command)
