from cleo import Application
from cleo.config.application_config import ApplicationConfig
from cleo.io.console_io import ConsoleIO

from . import __version__
from .commands import ConfigCommand, ExtractCommand, InitCommand, TestCommand
from .utils import ClikitLoggingHandler


class LoggingAppConfig(ApplicationConfig):
    def __init__(self) -> None:
        super().__init__("autojail", version=__version__)

    def create_io(self, *args, **kwargs) -> ConsoleIO:
        io = super().create_io(*args, **kwargs)
        ClikitLoggingHandler.setup_for("autojail", io)
        return io


class AutojailApp(Application):
    def __init__(self) -> None:
        super().__init__(config=LoggingAppConfig())

        self.add(InitCommand())
        self.add(ExtractCommand())
        self.add(ConfigCommand())
        self.add(TestCommand())


app = AutojailApp()
