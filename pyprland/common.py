""" Shared utilities: logging """

import os
import re
import logging
from dataclasses import dataclass

__all__ = ["DEBUG", "get_logger", "state", "PyprError", "apply_variables"]

DEBUG = os.environ.get("DEBUG", False)


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


def get_logger(name="pypr", level=None) -> logging.Logger:
    """Returns a named logger

    Args:
        name (str): logger's name
        level (int): logger's level (auto if not set)
    """
    logger = logging.getLogger(name)
    if level is None:
        logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
    else:
        logger.setLevel(level)
    logger.propagate = False
    for handler in LogObjects.handlers:
        logger.addHandler(handler)
    logger.info('Logger "%s" initialized', name)
    return logger


@dataclass
class SharedState:
    "Stores commonly requested properties"
    active_workspace: str = ""  # workspace name
    active_monitor: str = ""  # monitor name
    active_window: str = ""  # window address


state = SharedState()
"""
Exposes most-commonly accessed attributes to avoid specific IPC requests
- `active_monitor` monitor's name
- `active_workspace` workspace's name
- `active_window` window's address
"""


def apply_variables(template: str, variables: dict[str, str]):
    """Replace [var_name] with content from supplied variables
    Args:
        template: the string template
        variables: a dict containing the variables to replace
    """
    pattern = r"\[([^\[\]]+)\]"

    def replace(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return re.sub(pattern, replace, template)


def apply_filter(text, filt_cmd: str):
    """Apply filters to text
    Currently supports only "s" command fom vim/ed"""
    if not filt_cmd:
        return text
    if filt_cmd[0] == "s":  # vi-like substitute
        (_, base, replacement, opts) = filt_cmd.split(filt_cmd[1])
        return re.sub(base, replacement, text, count=0 if "g" in opts else 1)
    return text
