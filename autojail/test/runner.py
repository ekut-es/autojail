import shlex
import subprocess
import threading
from typing import Any, Dict, List, Optional, Union

from dataclasses import dataclass

from ..model.board import Board
from ..model.config import AutojailConfig
from ..model.jailhouse import JailhouseConfig
from ..model.test import TestConfig, TestEntry
from ..utils.connection import Connection, connect
from ..utils.logging import getLogger


@dataclass
class TestResult:
    passed: bool
    metrics: Dict[str, Union[float, int, bool]]


class TestRunner:
    def __init__(
        self,
        autojail_config: AutojailConfig,
        board_info: Board,
        jailhouse_config: JailhouseConfig,
        test_config: TestConfig,
        automate_context: Any,
    ) -> None:
        self.autojail_config = autojail_config
        self.board_info = board_info
        self.jailhouse_config = jailhouse_config
        self.test_config = test_config
        self.automate_context = automate_context

        self.logger = getLogger()

        self.threads: List[threading.Thread] = []
        self.connection: Optional[Connection] = None

    def run(self) -> None:
        tests = self._prepare_tests()

        self.logger.info("Resetting target board")
        self._run_reset()

        try:
            self._deploy()
        except Exception:
            self.logger.critical("Could not deploy to target, trying reset ...")
            self._run_stop()
            return

        self._wait_for_connection()

        results: Dict[str, TestResult] = {}
        for name, test in tests.items():
            self.logger.debug("Starting test: %s", name)
            result = self._run_test(test)
            self.logger.info(
                "%s, %s", name, "PASSED" if result.passed else "Failed"
            )
            results[name] = result
        try:
            self._run_stop()
        except Exception:
            self.logger.critical("Could not stop target, trying reset ...")
            self._run_reset()

    def _run_test(self, test: TestEntry):
        script = test.script
        self._run_script(script)
        return TestResult(passed=True, metrics={})

    def _prepare_tests(self) -> Dict[str, TestEntry]:
        tests = {}
        for name, test in self.test_config.items():
            tests[name] = test

        return tests

    def _deploy(self) -> None:
        return

    def _run_script(self, script):
        current_targets = []
        for command in script:
            if isinstance(command, str):
                if current_targets:
                    for target in current_targets:
                        target.run(command, warn=True)
                else:
                    self._run_command(command)

    def _wait_for_connection(self):
        if self.connection is None or not self.connection.is_connected:
            self.connection = connect(
                self.autojail_config, self.automate_context
            )

            assert self.connection.is_connected

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
