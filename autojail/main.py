from cleo import Application

from .commands import (
    InitCommand,
    ExtractCommand,
    ConfigCommand,
)  # , TestCommand


class AutojailApp(Application):
    def __init__(self):

        super().__init__()

        self.add(InitCommand())
        self.add(ExtractCommand())
        self.add(ConfigCommand())


#        self.add(TestCommand())


app = AutojailApp()
