from ..test import TestRunner
from .base import BaseCommand


class TestCommand(BaseCommand):
    """ Run tests to verify generated jailhouse configuration

    test
    """

    def handle(self) -> int:
        runner = TestRunner("./test.yml")

        runner.run()

        return 0
