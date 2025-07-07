"""
Модуль для настройки централизованного логгера.

Содержит функцию setup_logger(), которая настраивает логгер с выводом как в консоль,
так и в файл. Уровень логирования берётся из переменной окружения LOG_LEVEL.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from config import conf


class SharedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def _open(self):
        return open(self.baseFilename, self.mode, encoding=self.encoding)


def setup_logger(name: str = __name__, log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Настраивает и возвращает логгер с указанными параметрами.
    """

    logger = logging.getLogger(name)

    # Преобразуем строку уровня логирования в числовой уровень
    level = os.getenv("LOG_LEVEL", level).upper()
    numeric_level = getattr(logging, level, logging.INFO)
    logger.setLevel(numeric_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый хендлер
    file_path = log_file or conf.LOG_FILE
    log_dir = os.path.dirname(file_path) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = SharedTimedRotatingFileHandler(
            filename=file_path,
            when='H',
            interval=12,
            backupCount=90,
            encoding='utf-8',
            delay=False,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Не удалось создать файл лога '{file_path}': {e}")

    return logger