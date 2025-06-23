"""
Модуль для работы с Redis.

Содержит класс RedisManager для управления задачами и временными данными.
"""

from datetime import datetime
import redis
import json
import uuid
from typing import List, Optional
from config import conf
from utils.logger import setup_logger


logger = setup_logger(__name__)


class RedisManager:
    """
    Класс для взаимодействия с Redis.

    Attributes:
        client (redis.Redis): Клиент Redis.
        ttl_seconds (int): Время жизни ключа в секундах.
        key_prefix (str): Префикс для всех ключей.
    """

    TTL_WEEK = 60 * 60 * 24 * 7  # 7 дней

    def __init__(self):
        self.client = redis.Redis(
            host=conf.REDIS_HOST,
            port=conf.REDIS_PORT,
            db=conf.REDIS_DB,
            password=conf.REDIS_PASSWORD,
            decode_responses=True
        )
        self.ttl_seconds = self.TTL_WEEK
        self.key_prefix = conf.REDIS_KEY_PREFIX

    def _make_key(self, task_id: str) -> str:
        """Формирует ключ в Redis с префиксом."""
        return f"{self.key_prefix}{task_id}"

    def create_task(self, resume_ids: List[str], description: Optional[str] = "") -> str:
        """
        Создаёт новую задачу в Redis.

        Args:
            resume_ids (list): Список ID резюме.
            description (str | None): Описание вакансии для последующего анализа.

        Returns:
            str: Уникальный ID задачи.
        """
        task_id = str(uuid.uuid4())
        key = self._make_key(task_id)

        task_data = {
            "resume_ids": resume_ids,
            "description": description or "",
            "created_at": datetime.now().isoformat()
        }

        try:
            self.client.setex(key, self.ttl_seconds, json.dumps(task_data))
            logger.info(f"Создана задача {task_id} с {len(resume_ids)} резюме и описанием длиной {len(description)} символов")
            return task_id
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            raise


    def get_task_data(self, task_id: str) -> Optional[dict]:
        """
        Получает данные задачи из Redis (включая description).

        Args:
            task_id (str): ID задачи.

        Returns:
            dict | None: Словарь с данными задачи или None, если задача не найдена.
        """
        key = self._make_key(task_id)
        data = self.client.get(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON для задачи {task_id}")
            return None


    def get_task_resume_ids(self, task_id: str) -> Optional[List[str]]:
        """
        Получает только список ID резюме по задаче.

        Args:
            task_id (str): ID задачи.

        Returns:
            list | None: Список ID резюме или None.
        """
        task_data = self.get_task_data(task_id)
        return task_data["resume_ids"] if task_data else None

    def get_task(self, task_id: str) -> Optional[List[str]]:
        """
        Получает задачу из Redis.

        Args:
            task_id (str): ID задачи.

        Returns:
            list | None: Список ID резюме или None, если задача не найдена.
        """
        key = self._make_key(task_id)
        data = self.client.get(key)
        if not data:
            return None
        return json.loads(data)

    def delete_task(self, task_id: str) -> None:
        """
        Удаляет задачу из Redis.

        Args:
            task_id (str): ID задачи.
        """
        key = self._make_key(task_id)
        self.client.delete(key)
        logger.info(f"Задача {task_id} удалена")

    def clear_old_tasks(self) -> int:
        """
        Удаляет все устаревшие задачи.

        Returns:
            int: Количество удалённых задач.
        """
        deleted_count = 0
        keys = self.client.keys(f"{self.key_prefix}*")
        for key in keys:
            if not self.client.exists(key):
                continue
            ttl = self.client.ttl(key)
            if ttl <= 0:
                self.client.delete(key)
                deleted_count += 1
        logger.info(f"Очищено {deleted_count} устаревших задач")
        return deleted_count
    
    def update_task_progress(self, task_id: str, progress: int, status: str = "in_progress") -> None:
        key = self._make_key(task_id)
        data = self.get_task_data(task_id)
        if not data:
            return
        data["progress"] = progress
        data["status"] = status
        data["updated_at"] = datetime.now().isoformat()
        try:
            self.client.setex(key, self.ttl_seconds, json.dumps(data))
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса задачи {task_id}: {e}")

    def update_task_resume_ids(self, task_id: str, resume_ids: List[str]) -> None:
        key = self._make_key(task_id)
        data = self.get_task_data(task_id)
        if not data:
            return
        data["resume_ids"] = resume_ids
        try:
            self.client.setex(key, self.ttl_seconds, json.dumps(data))
        except Exception as e:
            logger.error(f"Ошибка при обновлении resume_ids задачи {task_id}: {e}")