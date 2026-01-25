"""Logging setup and utilities."""

import logging

from .ansi import LogStyles, make_style, should_colorize
from .debug import is_debug, set_debug

__all__ = [
    "LogObjects",
    "get_logger",
    "init_logger",
]


class LogObjects:
    """Reusable objects for loggers."""

    handlers: list[logging.Handler] = []


def init_logger(filename: str | None = None, force_debug: bool = False) -> None:
    """Initialize the logging system.

    Args:
        filename: Optional filename to log to
        force_debug: If True, force debug level
    """
    if force_debug:
        set_debug(True)

    class ScreenLogFormatter(logging.Formatter):
        """A custom formatter, adding colors based on log level.

        Respects NO_COLOR environment variable and TTY detection.
        """

        LOG_FORMAT = r"%(name)25s - %(message)s // %(filename)s:%(lineno)d" if is_debug() else r"%(message)s"

        def __init__(self) -> None:
            super().__init__()
            use_colors = should_colorize()
            if use_colors:
                warn_pre, warn_suf = make_style(*LogStyles.WARNING)
                err_pre, err_suf = make_style(*LogStyles.ERROR)
                crit_pre, crit_suf = make_style(*LogStyles.CRITICAL)
            else:
                warn_pre = warn_suf = err_pre = err_suf = crit_pre = crit_suf = ""

            self._formatters = {
                logging.DEBUG: logging.Formatter(self.LOG_FORMAT),
                logging.INFO: logging.Formatter(self.LOG_FORMAT),
                logging.WARNING: logging.Formatter(warn_pre + self.LOG_FORMAT + warn_suf),
                logging.ERROR: logging.Formatter(err_pre + self.LOG_FORMAT + err_suf),
                logging.CRITICAL: logging.Formatter(crit_pre + self.LOG_FORMAT + crit_suf),
            }

        def format(self, record: logging.LogRecord) -> str:
            return self._formatters[record.levelno].format(record)

    logging.basicConfig()
    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(logging.Formatter(fmt=r"%(asctime)s [%(levelname)s] %(name)s :: %(message)s :: %(filename)s:%(lineno)d"))
        LogObjects.handlers.append(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ScreenLogFormatter())
    LogObjects.handlers.append(stream_handler)


def get_logger(name: str = "pypr", level: int | None = None) -> logging.Logger:
    """Return a named logger.

    Args:
        name (str): logger's name
        level (int): logger's level (auto if not set)

    Returns:
        The logger instance
    """
    logger = logging.getLogger(name)
    if level is None:
        logger.setLevel(logging.DEBUG if is_debug() else logging.WARNING)
    else:
        logger.setLevel(level)
    logger.propagate = False
    for handler in LogObjects.handlers:
        logger.addHandler(handler)
    logger.info('Logger "%s" initialized', name)
    return logger
