import functools
import inspect
import logging
from .logger import setup_logger

_cached_logger = None

def get_logger():
    global _cached_logger
    if _cached_logger is None:
        _cached_logger = setup_logger("default_logger")
    return _cached_logger

def log_function_call(func=None, *, logger=None):
    def decorator(_func):
        @functools.wraps(_func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()

            caller_info = inspect.getframeinfo(inspect.currentframe().f_back)
            logger.info(
                f"Вызов функции '{_func.__name__}' из {caller_info.filename}:{caller_info.lineno} "
                f"с аргументами args={args}, kwargs={kwargs}"
            )
            return _func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)