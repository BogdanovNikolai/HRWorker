"""
Модуль, управляющий фоновым планировщиком задач (BackgroundScheduler).

Содержит класс `SchedulerManager`, который отвечает за инициализацию,
запуск и корректное завершение работы планировщика.
"""

import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from data_manager import dm


class SchedulerManager:
    """
    Класс для управления фоновым планировщиком задач.

    Attributes:
        scheduler (BackgroundScheduler or None): Экземпляр планировщика.
            Изначально равен None до первого вызова метода `start`.
    """

    def __init__(self):
        """
        Инициализирует новый экземпляр класса SchedulerManager.

        Устанавливает начальное состояние планировщика как None.
        """
        self.scheduler = None

    def start(self):
        """
        Запускает фоновый планировщик задач, если он ещё не запущен.

        Добавляет ежедневную задачу на обновление кэша вакансий в 8:00 утра.
        Регистрирует функцию завершения работы планировщика при выходе из приложения.
        """
        if self.scheduler is not None:
            return

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(dm.update_vacancies_cache, 'cron', hour=8)
        self.scheduler.start()
        atexit.register(self.shutdown)

    def shutdown(self):
        """
        Останавливает и завершает работу планировщика, если он был запущен.

        Очистка ресурсов, связанных с планировщиком.
        """
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None


scheduler_manager = SchedulerManager()
