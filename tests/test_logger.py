import sys
import logging
import os
import shutil
import time
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from utils.logger import setup_logger

LOG_DIR = Path("test_logs")
LOG_FILE = LOG_DIR / "test_app.log"

@pytest.fixture(autouse=True)
def clean_log_dir():
    """Перед каждым тестом очищаем директорию логов и закрываем все хэндлеры"""
    if LOG_DIR.exists():
        # Закрываем все логгеры и их хэндлеры
        for logger in logging.Logger.manager.loggerDict.values():
            if isinstance(logger, logging.Logger):
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)

        shutil.rmtree(LOG_DIR)

    LOG_DIR.mkdir(parents=True, exist_ok=True)  # создаём чистую папку

    yield

    if LOG_DIR.exists():
        # То же самое перед пост-очисткой
        for logger in logging.Logger.manager.loggerDict.values():
            if isinstance(logger, logging.Logger):
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)

        shutil.rmtree(LOG_DIR)


def test_logger_creation_and_handlers():
    logger = setup_logger(name="test_logger", log_file=str(LOG_FILE), level="DEBUG")

    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG

    handler_types = {type(h) for h in logger.handlers}
    assert logging.StreamHandler in handler_types
    assert logging.FileHandler in handler_types or any("FileHandler" in str(h.__class__) for h in logger.handlers)


def test_logger_logs_to_file():
    logger = setup_logger(name="file_test_logger", log_file=str(LOG_FILE), level="INFO")

    logger.info("Test log message to file")

    assert LOG_FILE.exists()

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Test log message to file" in content


def test_logger_prevents_duplicate_handlers():
    logger1 = setup_logger(name="dup_logger", log_file=str(LOG_FILE))
    initial_handler_count = len(logger1.handlers)

    logger2 = setup_logger(name="dup_logger", log_file=str(LOG_FILE))
    assert logger1 is logger2
    assert len(logger2.handlers) == initial_handler_count  # Не увеличилось


def test_logger_with_invalid_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "NON_EXISTENT_LEVEL")
    logger = setup_logger(name="bad_level_logger", log_file=str(LOG_FILE))
    # Должен fallback-нуться на INFO
    assert logger.level == logging.INFO


def test_log_rotation_behavior(tmp_path):
    """Тестируем ротацию: создаём логгер с частой ротацией"""
    temp_file = LOG_DIR / "rotate.log"

    # Явно создаём логгер с файловым хэндлером
    logger = setup_logger(name="rotate_logger", log_file=str(temp_file), level="DEBUG")

    # Убеждаемся, что есть FileHandler
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "FileHandler не найден в логгере"

    file_handler = file_handlers[0]

    # Пишем несколько сообщений
    for i in range(3):
        logger.debug(f"rotation test {i}")
        time.sleep(0.1)  # пауза для корректной отметки времени

    # Вызываем ротацию
    file_handler.doRollover()

    # Проверяем, что появился ротированный файл
    rotated_logs = list(LOG_DIR.glob("rotate.log*"))
    assert len(rotated_logs) >= 2  # оригинальный + ротированный


def test_logger_default_file(monkeypatch):
    monkeypatch.delenv("LOG_FILE", raising=False)
    logger = setup_logger(name="default_path_logger", level="INFO")
    default_log_path = Path("logs/app.log")

    logger.info("Default path test")

    assert default_log_path.exists()
    with open(default_log_path, "r", encoding="utf-8") as f:
        assert "Default path test" in f.read()
