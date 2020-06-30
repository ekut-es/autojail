from cleo import Application
from cleo.config.application_config import ApplicationConfig

from .commands import InitCommand, ExtractCommand, ConfigCommand, TestCommand
from .utils import ClikitLoggingHandler
from . import __version__


class LoggingAppConfig(ApplicationConfig):
    def __init__(self):
        super().__init__("autojail", version=__version__)

    def create_io(self, *args, **kwargs):
        io = super().create_io(*args, **kwargs)
        ClikitLoggingHandler.setup_for("autojail", io)
        return io


class AutojailApp(Application):
    def __init__(self):
        super().__init__(config=LoggingAppConfig())

        self.add(InitCommand())
        self.add(ExtractCommand())
        self.add(ConfigCommand())
        self.add(TestCommand())


app = AutojailApp()
