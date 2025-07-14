"""
Точка входа приложения.

Запуск Flask-сервера и инициализация системы.
"""

import os
from app import app, init_scheduler, check_and_update_vacancies_cache_on_startup
from config import conf
from database import init_db
from threading import Thread
from utils.logger import setup_logger

logger = setup_logger(__name__)

def run_scheduler_and_check_cache():
    init_scheduler()
    check_and_update_vacancies_cache_on_startup()

if __name__ == "__main__":
    init_db()

    startup_thread = Thread(target=run_scheduler_and_check_cache)
    startup_thread.start()
    
    logger.info("=== Запуск сервера ===")

    app.run(host="0.0.0.0", port=5000, debug=False)