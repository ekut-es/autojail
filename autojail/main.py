from cleo import Application

from .commands import InitCommand, ExtractCommand, ConfigCommand, TestCommand
from .utils import ClikitLoggingHandler


class AutojailApp(Application):
    def __init__(self):
        super().__init__()

        self.logging_handler = ClikitLoggingHandler.setup_for(
            "autojail", self._preliminary_io
        )

        self.add(InitCommand())
        self.add(ExtractCommand())
        self.add(ConfigCommand())
        self.add(TestCommand())


app = AutojailApp()
