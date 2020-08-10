from ..test import TestRunner
from .base import BaseCommand


class TestCommand(BaseCommand):
    """ Run tests to verify generated jailhouse configuration

    test
    """

    def handle(self) -> None:
        runner = TestRunner("./test.yml")

        runner.run()
