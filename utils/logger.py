"""
Модуль для настройки централизованного логгера.

Содержит функцию setup_logger(), которая настраивает логгер с выводом как в консоль,
так и в файл. Уровень логирования берётся из переменной окружения LOG_LEVEL.
"""

import logging
import os
import atexit
from typing import Optional
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config import conf  # убедитесь, что config.LOG_FILE указан правильно


def setup_logger(name: str = __name__, log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Настраивает и возвращает логгер с указанными параметрами.
    """

    logger = logging.getLogger(name)

    # Если логгер уже настроен — возвращаем его
    if logger.handlers:
        return logger

    # Получаем уровень логгирования из env или используем по умолчанию
    level = os.getenv("LOG_LEVEL", level).upper()
    numeric_level = getattr(logging, level, logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)

    # Файловый хендлер
    file_path = log_file or conf.LOG_FILE
    log_dir = os.path.dirname(file_path) or "."
    
    try:
        os.makedirs(log_dir, exist_ok=True)

        file_handler = ConcurrentRotatingFileHandler(
            filename=file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        logger.addHandler(file_handler)

        logger.debug(f"Логгер '{name}' настроен. Логи пишутся в: {file_path}")

    except Exception as e:
        logger.warning(f"Не удалось создать файл лога '{file_path}': {e}")

    def close_logger():
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)

    atexit.register(close_logger)

    return logger