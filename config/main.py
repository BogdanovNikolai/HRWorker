"""
Модуль для загрузки и предоставления конфигурационных данных из .env файла.

Содержит класс Config, который предоставляет доступ ко всем переменным окружения,
используемым в приложении.
"""

import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

class Config:
    """
    Класс конфигурации приложения.

    Предоставляет доступ к переменным окружения, используемым в приложении.
    """

    # === Redis ===
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "hh_app_")

    # === PostgreSQL ===
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")

    # === HeadHunter API Tokens ===
    CLIENT_ID1 = os.getenv("CLIENT_ID1")
    CLIENT_SECRET1 = os.getenv("CLIENT_SECRET1")
    ACCESS_TOKEN1 = os.getenv("ACCESS_TOKEN1")
    REFRESH_TOKEN1 = os.getenv("REFRESH_TOKEN1")
    REDIRECT_URI1 = os.getenv("REDIRECT_URI1")

    CLIENT_ID2 = os.getenv("CLIENT_ID2")
    CLIENT_SECRET2 = os.getenv("CLIENT_SECRET2")
    ACCESS_TOKEN2 = os.getenv("ACCESS_TOKEN2")
    REFRESH_TOKEN2 = os.getenv("REFRESH_TOKEN2")
    REDIRECT_URI2 = os.getenv("REDIRECT_URI2")

    # Список access-токенов для балансировки нагрузки
    HH_ACCESS_TOKENS = [token for token in [
        os.getenv("ACCESS_TOKEN1"),
        os.getenv("ACCESS_TOKEN2")
    ] if token]

    # === DeepSeek AI ===
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    # === Flask App ===
    SECRET_KEY = os.getenv("SECRET_KEY")

    # === Логирование ===
    LOG_LEVEL = os.getenv("LOG_LEVEL")
    LOG_FILE = os.getenv("LOG_FILE")

    # === Директории ===
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    AREAS_CACHE_PATH = os.getenv("AREAS_CACHE_PATH", "utils/areas_cache.json")

    # === Лимиты и таймауты ===
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
    TTL_HOURS = int(os.getenv("TTL_HOURS", "48"))

    # === Вакансии ===
    DEFAULT_EMPLOYER_ID = int(os.getenv("DEFAULT_EMPLOYER_ID", "104309"))

    # === SQLAlchemy ===
    SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

    # === EStaff images ===
    ESTAFF_MODULE_ICON = os.getenv("ESTAFF_MODULE_ICON")
    ESTAFF_MODULE_ICON_2 = os.getenv("ESTAFF_MODULE_ICON_2")
    ESTAFF_SAVE = os.getenv("ESTAFF_SAVE")
    ESTAFF_SAVE_DUBLE = os.getenv("ESTAFF_SAVE_DUBLE")