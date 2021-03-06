from pathlib import Path

from ..test import TestRunner
from .base import BaseCommand


class TestCommand(BaseCommand):
    """ Run tests to verify generated jailhouse configuration

    test
    """

    def handle(self) -> int:
        board_info = self.load_board_info()
        if not board_info:
            return 1

        autojail_config = self.autojail_config
        if not autojail_config:
            return 1

        jailhouse_config = self.load_jailhouse_config(
            Path("report/generated_cells.yml")
        )
        if not jailhouse_config:
            return 1

        test_config = self.load_test_config()
        if not test_config:
            return 1

        automate_context = self.automate_context

        runner = TestRunner(
            autojail_config,
            board_info,
            jailhouse_config,
            test_config,
            automate_context,
        )

        runner.run()

        return 0
