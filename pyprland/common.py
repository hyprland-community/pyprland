""" Shared utilities: logging """
import logging
import time
import os

__all__ = ["DEBUG", "get_logger", "init_logger"]

DEBUG = os.environ.get("DEBUG", False)


def cache50ms(func):
    """Caches an async function so it can't be called more than once every 50ms

    Doesn't support handling of the parameters
    """
    last_result = None
    last_update = 0.0

    async def _cached_fn(*args):
        nonlocal last_result, last_update

        t = time.time()
        if last_update + 0.05 > t:
            return last_result
        last_result = await func(*args)
        last_update = t
        return last_result

    return _cached_fn


class PyprError(Exception):
    """Used for errors which already triggered logging"""


class LogObjects:
    """Reusable objects for loggers"""

    handlers: list[logging.Handler] = []


def init_logger(filename=None, force_debug=False):
    """initializes the logging system"""
    global DEBUG
    if force_debug:
        DEBUG = True

    class ScreenLogFormatter(logging.Formatter):
        "A custom formatter, adding colors"
        LOG_FORMAT = (
            r"%(name)25s - %(message)s // %(filename)s:%(lineno)d"
            if DEBUG
            else r"%(message)s"
        )
        RESET_ANSI = "\x1b[0m"

        FORMATTERS = {
            logging.DEBUG: logging.Formatter(LOG_FORMAT + RESET_ANSI),
            logging.INFO: logging.Formatter(LOG_FORMAT + RESET_ANSI),
            logging.WARNING: logging.Formatter("\x1b[33;20m" + LOG_FORMAT + RESET_ANSI),
            logging.ERROR: logging.Formatter("\x1b[31;20m" + LOG_FORMAT + RESET_ANSI),
            logging.CRITICAL: logging.Formatter("\x1b[31;1m" + LOG_FORMAT + RESET_ANSI),
        }

        def format(self, record):
            return self.FORMATTERS[record.levelno].format(record)

    logging.basicConfig()
    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(
            logging.Formatter(
                fmt=r"%(asctime)s [%(levelname)s] %(name)s :: %(message)s :: %(filename)s:%(lineno)d"
            )
        )
        LogObjects.handlers.append(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ScreenLogFormatter())
    LogObjects.handlers.append(stream_handler)


def get_logger(name="pypr", level=None):
    "Returns a logger for `name`"
    logger = logging.getLogger(name)
    if level is None:
        logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
    else:
        logger.setLevel(level)
    logger.propagate = False
    for handler in LogObjects.handlers:
        logger.addHandler(handler)
    logger.info("Logger initialized for %s", name)
    return logger
