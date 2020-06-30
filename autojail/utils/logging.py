import logging

from clikit.api.io import flags as verbosity


def getLogger():
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

    def __init__(self, io, level=logging.NOTSET):
        super().__init__(level=level)
        self.io = io

    def emit(self, record: logging.LogRecord):
        level = _levels[record.levelno]
        text = record.getMessage()
        self.io.write_line(text, flags=level)

    @classmethod
    def setup_for(cls, name, io):
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        log.handlers = [cls(io)]
        log.debug("Logger initialized.")
