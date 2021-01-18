import logging
from logging import Logger

from cleo.io.console_io import ConsoleIO
from clikit.api.io import flags as verbosity


def getLogger() -> Logger:  # noqa
    return logging.getLogger("autojail")


_levels = {
    logging.CRITICAL: verbosity.NORMAL,
    logging.ERROR: verbosity.NORMAL,
    logging.WARNING: verbosity.NORMAL,
    logging.INFO: verbosity.VERBOSE,
    logging.DEBUG: verbosity.DEBUG,
}


class ClikitLoggingHandler(logging.Handler):
    """Logging handler that redirects all messages to clikit io object."""

    def __init__(self, io: ConsoleIO, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self.io = io

    def emit(self, record: logging.LogRecord) -> None:
        levelno = record.levelno
        level = _levels[levelno]
        text = record.getMessage()
        if levelno in [logging.ERROR, logging.CRITICAL, logging.WARNING]:
            text = "<error>" + text + "</error>"

        self.io.write_line(text, flags=level)

    @classmethod
    def setup_for(cls, name: str, io: ConsoleIO) -> None:
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        log.handlers = [cls(io)]
        log.debug("Logger initialized.")
