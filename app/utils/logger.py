"""
Thin wrapper around the standard logging module so that application code
gets a consistently named, pre-configured logger without repeating
boilerplate at every call site.
"""
import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"attendguard.{name}")
