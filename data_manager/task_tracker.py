from redis_manager import RedisManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TaskTracker:
    def __init__(self):
        self.redis = RedisManager()

    def create_task(self, description: str = "", resume_ids: list = None) -> str:
        """Создаёт новую задачу с начальным прогрессом."""
        return self.redis.create_task(resume_ids or [], description)

    def update_progress(self, task_id: str, progress: int, status: str = "in_progress") -> None:
        """Обновляет прогресс выполнения задачи."""
        self.redis.update_task_progress(task_id, progress, status)

    def get_progress(self, task_id: str) -> dict:
        """Возвращает текущий прогресс и статус задачи."""
        task_data = self.redis.get_task_data(task_id)
        if not task_data:
            return {
                "task_id": task_id,
                "progress": 0,
                "status": "not_found",
                "description": ""
            }
        return {
            "task_id": task_id,
            "progress": task_data.get("progress", 0),
            "status": task_data.get("status", "created"),
            "description": task_data.get("description", "")
        }