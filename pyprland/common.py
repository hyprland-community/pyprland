import os
import logging

__all__ = ["DEBUG", "get_logger", "init_logger"]

DEBUG = os.environ.get("DEBUG", False)


class PyprError(Exception):
    pass


class LogObjects:
    handlers: list[logging.Handler] = []


def init_logger(filename=None, force_debug=False):
    global DEBUG
    if force_debug:
        DEBUG = True

    class ScreenLogFormatter(logging.Formatter):
        LOG_FORMAT = (
            r"%(levelname)s:%(name)s - %(message)s // %(filename)s:%(lineno)d"
            if DEBUG
            else r"%(levelname)s: %(message)s"
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
        handler = logging.FileHandler(filename)
        handler.setFormatter(
            logging.Formatter(
                fmt=r"%(asctime)s [%(levelname)s] %(name)s :: %(message)s :: %(filename)s:%(lineno)d"
            )
        )
        LogObjects.handlers.append(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(ScreenLogFormatter())
    LogObjects.handlers.append(handler)


def get_logger(name="pypr", level=None):
    logger = logging.getLogger(name)
    if level is None:
        logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    else:
        logger.setLevel(level)
    logger.propagate = False
    for handler in LogObjects.handlers:
        logger.addHandler(handler)
    logger.debug(f"Logger initialized for {name}")
    return logger
