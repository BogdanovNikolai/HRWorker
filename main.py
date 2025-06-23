"""
Точка входа приложения.

Запуск Flask-сервера и инициализация системы.
"""

import os
from app import app
from config import conf
from database import init_db


if __name__ == "__main__":
    init_db()

    # host = conf.HH_HOST
    # port = conf.HH_PORT
    # debug = conf.DEBUG_MODE

    print(f"=== Запуск сервера ===")
    # print(f"Host: {host}")
    # print(f"Port: {port}")
    # print(f"Debug: {'включен' if debug else 'выключен'}")

    app.run(host="0.0.0.0", port=5000, debug=False)