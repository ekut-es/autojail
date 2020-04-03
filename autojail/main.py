from cleo import Application

from .commands import InitCommand


class AutojailApp(Application):
    def __init__(self):

        super().__init__()

        self.add(InitCommand())


app = AutojailApp()
