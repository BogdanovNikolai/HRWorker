"""
Модуль для настройки централизованного логгера.

Содержит функцию setup_logger(), которая настраивает логгер с выводом как в консоль,
так и в файл. Уровень логирования берётся из переменной окружения LOG_LEVEL.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(name: str = __name__, log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Настраивает и возвращает логгер с указанными параметрами.

    Args:
        name (str): Имя логгера. Обычно используется __name__ модуля.
        log_file (Optional[str]): Путь к файлу лога. Если не указан, используется значение из env.
        level (str): Уровень логирования. Например: DEBUG, INFO, WARNING, ERROR, CRITICAL.

    Returns:
        logging.Logger: Настроенный экземпляр логгера.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Избегаем дублирования хендлеров
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый вывод
    file_path = log_file or os.getenv("LOG_FILE", "app.log")
    try:
        file_handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Не удалось создать файл лога '{file_path}': {e}")

    return logger