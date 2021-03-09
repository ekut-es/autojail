import shlex
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dataclasses import dataclass

from ..model.board import Board
from ..model.config import AutojailConfig
from ..model.jailhouse import JailhouseConfig
from ..model.test import TestConfig, TestEntry
from ..utils.connection import Connection, connect
from ..utils.deploy import deploy_target
from ..utils.logging import getLogger
from .test import TestProvider


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

        self._wait_for_connection()

        try:
            self._deploy()
        except Exception as e:
            print(str(e))
            self.logger.critical("Could not deploy to target, trying reset ...")
            self._run_reset()
            return

        results: Dict[str, TestResult] = {}
        for name, test in tests.items():
            self.logger.debug("Starting test: %s", name)
            result = self._run_test(test)
            self.logger.info(
                "%s, %s", name, "PASSED" if result.passed else "FAILED"
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
        generic_provider = TestProvider(
            self.autojail_config, self.jailhouse_config, self.board_info
        )
        tests = generic_provider.tests()
        for name, test in self.test_config.items():
            tests[name] = test

        return tests

    def _deploy(self) -> None:
        deploy_target(self.connection, Path("./deploy.tar.gz"))

    def _run_script(self, script):
        script_name = ""
        script_path = None
        with tempfile.NamedTemporaryFile(
            prefix="autojail_test", suffix=".sh", delete=False
        ) as tmpfile:
            try:
                tmpfile.writelines([(c + "\n").encode("utf-8") for c in script])
                tmpfile.close()
                script_path = Path(tmpfile.name)
                script_name = script_path.name
                self.connection.put(tmpfile.name, "/tmp")
            finally:
                if script_path and script_path.exists():
                    script_path.unlink()

        self.connection.run(f"/bin/bash /tmp/{script_name}")
        self.connection.run(f"rm -f /tmp/{script_name}")

    def _wait_for_connection(self):
        if self.connection is None or not self.connection.is_connected:
            self.connection = connect(
                self.autojail_config, self.automate_context
            )

            assert self.connection.is_connected

    def _run_local_command(self, command) -> int:
        self.logger.info("Running: %s", str(command))
        retval = subprocess.run(shlex.split(command))
        return retval.returncode

    def _run_start(self):
        for command in self.autojail_config.start_command:
            self._run_local_command(command)

    def _run_reset(self):
        if self.autojail_config.reset_command:
            for command in self.autojail_config.reset_command:
                self._run_local_command(command)
        else:
            self.logger.warning(
                "No reset command given trying stop, followed by start"
            )
            self._run_start()
            self._run_stop()

    def _run_stop(self):
        for command in self.autojail_config.start_command:
            self._run_local_command(command)
