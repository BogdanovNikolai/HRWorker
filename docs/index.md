# HRWorker | Документация

Автоматическая оценка кандидатов с помощью больших языковых моделей.

## Как начать работу?

* `python -m venv .venv` - Создать виртуальное окружение.
* `.venv\Scripts\activate` - Перейти в созданное виртуальное окружение (для Windows).
* `pip intall -r .\requirements.txt` - Установить зависимости проекта.
* Создайте файл .env в корне проекта и заполните в соответствии с примером .env.example.
* `python main.py` - Запустить точку входа в приложение.

Всё готово и сервис уже запущен!

## Архитектура проекта

    .env                # Файл переменных окружения
    .env.example        # Пример файла переменных окружения
    .gitignore          # .gitignore
    app.py              # Flask приложение (Frontend)
    areas_cache.json    # Список регионов для HeadHunter
    main.py             # Точка входа в приложение
    mkdocs.yml          # Файл конфигурации документации
    README.md           # README.md
    requirements.txt    # Зависимости проекта
    ai/
        main.py         # Модуль интеграции с ИИ
    api/
        hh/
            main.py     # Модуль интеграции с API HeadHunter
    config/
        main.py         # Модуль конфига проекта
    