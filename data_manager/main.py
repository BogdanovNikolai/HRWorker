"""
Основной модуль data_manager.

Содержит класс DataManager — точку входа для всех операций с данными.
"""

from typing import List, Dict, Any, Optional
from api.hh.main import HHApiClient
from data_manager.resume_processor import ResumeProcessor
from data_manager.search_engine import SearchEngine
from database.repository import ResumeRepository
from redis_manager import RedisManager
from database.session import get_db
from utils.logger import setup_logger
from threading import Thread
from data_manager.task_tracker import TaskTracker

logger = setup_logger()


class DataManager:
    """
    Главный класс, объединяющий все компоненты data_manager.
    
    Attributes:
        hh_client (HHApiClient): Клиент для обращения к HeadHunter API.
        search_engine (SearchEngine): Логика поиска и кэширования.
        resume_repo (ResumeRepository): Работа с резюме в базе данных.
        redis_manager (RedisManager): Для хранения задач и прогресса.
        task_tracker (TaskTracker): Отслеживание прогресса задач.
    """

    def __init__(self):
        self.hh_client = HHApiClient()
        self.search_engine = SearchEngine(self.hh_client)
        self.resume_repo = ResumeRepository(next(get_db()))
        self.redis_manager = RedisManager()
        self.task_tracker = TaskTracker()

    def search_resumes(
    self,
    keywords: str,
    salary_to: Optional[int] = None,
    region: List[str] = ["113"],
    total: int = 50,
    per_page: int = 50,
    description: Optional[str] = ""
) -> str:
        """
        Синхронно выполняет поиск резюме и сохраняет результаты.
        Возвращает task_id для последующего получения результата.
        """
        task_id = self.task_tracker.create_task(description=description)

        try:
            resumes = self.search_engine.search(
                keywords=keywords,
                salary_to=salary_to,
                region=region,
                total=total,
                per_page=per_page
            )
            if not isinstance(resumes, list):
                logger.error("Ошибка поиска: ожидался список резюме")
                resumes = []

            resume_ids = [r.get("id") for r in resumes if r.get("id")]
            self.redis_manager.update_task_resume_ids(task_id, resume_ids)
            self.task_tracker.update_progress(task_id, 100, "completed")
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска: {e}")
            self.task_tracker.update_progress(task_id, 0, "failed")
            raise  # Перебрасываем ошибку, чтобы Flask мог обработать её

        return task_id

    def get_task_resumes(
    self,
    task_id: str,
    offset: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
        """
        Возвращает список резюме по task_id без зависимости от прогресса.
        """
        task_data = self.redis_manager.get_task_data(task_id)
        if not task_data or "resume_ids" not in task_data:
            logger.warning(f"Задача {task_id} не найдена или просрочена")
            return {
                "error": "Задача не найдена или истекло время жизни",
                "found": 0,
                "items": []
            }

        resume_ids = task_data["resume_ids"]
        found = len(resume_ids)
        paginated_ids = resume_ids[offset:offset + limit]

        items = []
        for resume_id in paginated_ids:
            cached_resume = self.search_engine.get_cached_resume(resume_id)
            if cached_resume:
                items.append(cached_resume)
                continue

            full_resume = self.hh_client.get_resume_details(resume_id)
            if not full_resume:
                logger.warning(f"Не удалось получить полные данные резюме {resume_id}")
                continue

            self.search_engine.save_to_cache(full_resume)
            items.append(full_resume)

        return {
            "found": found,
            "items": items,
            "task_id": task_id
        }

    def start_company_vacancies_task(self) -> str:
        """
        Запускает фоновую задачу получения вакансий компании.
        Returns:
            str: task_id новой задачи.
        """
        task_id = self.task_tracker.create_task(description="Получение списка вакансий")

        def background_get_vacancies():
            try:
                vacancies = self.search_engine.get_company_vacancies()
                resume_ids = [v.get("id") for v in vacancies if v.get("id")]
                self.redis_manager.update_task_resume_ids(task_id, resume_ids)
                self.task_tracker.update_progress(task_id, 100, "completed")
            except Exception as e:
                logger.error(f"Ошибка при получении вакансий: {e}")
                self.task_tracker.update_progress(task_id, 0, "failed")

        Thread(target=background_get_vacancies).start()
        return task_id

    # def start_get_negotiations_task(self, vacancy_id: int) -> str:
    #     """
    #     Запускает фоновую задачу получения новых откликов по вакансии.
    #     Returns:
    #         str: task_id новой задачи.
    #     """
    #     task_desc = f"Отклики по вакансии {vacancy_id}"
    #     task_id = self.task_tracker.create_task(description=task_desc)

    #     def background_get_negotiations():
    #         try:
    #             resume_ids = self.search_engine.get_new_resume_ids_from_negotiations(vacancy_id)
    #             self.redis_manager.update_task_resume_ids(task_id, resume_ids)
    #             self.task_tracker.update_progress(task_id, 100, "completed")
    #         except Exception as e:
    #             logger.error(f"Ошибка при получении откликов: {e}")
    #             self.task_tracker.update_progress(task_id, 0, "failed")

    #     Thread(target=background_get_negotiations).start()
    #     return task_id

    def get_negotiations_by_vacancy(self, vacancy_id) -> List[Dict[str, Any]]:
        """
        Получает список откликов по конкретной вакансии.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            list[dict]: Список откликов.
        """
        return self.search_engine.get_negotiations_by_vacancy(vacancy_id=vacancy_id)

    def get_company_vacancies(self) -> List[Dict[str, Any]]:
        """
        Получает список вакансий компании через HH API.
        """
        return self.search_engine.get_company_vacancies()

    def get_vacancy_by_id(self, vacancy_id: int):
        return self.search_engine.get_vacancy_by_id(vacancy_id=vacancy_id)

    def get_new_resume_ids_from_negotiations(self, vacancy_id: int) -> List[str]:
        """
        Получает список ID новых резюме из откликов по вакансии.
        """
        negotiations = self.hh_client.get_negotiations_by_vacancy(vacancy_id)
        new_resumes = []

        for n in negotiations:
            resume = n.get("resume", {})
            if not resume:
                continue

            resume_id = resume.get("id")
            if not resume_id:
                continue

            has_updates = n.get("has_updates", False)
            if has_updates:
                new_resumes.append(resume_id)

        return new_resumes

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает полные данные резюме.
        """
        return self.search_engine.get_cached_resume(resume_id)

    def export_resumes(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Подготавливает список резюме для экспорта.
        """
        resume_ids = self.redis_manager.get_task_resume_ids(task_id)
        results = []
        for resume_id in resume_ids or []:
            resume = self.get_resume(resume_id)
            if resume:
                results.append(resume)
        return results

    def get_current_manager(self) -> Dict[str, Any]:
        """
        Получает информацию о текущем менеджере.
        """
        return self.hh_client.get_current_manager()

    def get_current_manager_id(self) -> Optional[int]:
        """
        Получает ID текущего менеджера из данных о пользователе.
        """
        manager = self.get_current_manager()
        return manager.get("manager", {}).get("id") if manager else None

    def get_resume_limits(self, manager_id: int) -> Dict[str, Any]:
        """
        Получает лимиты просмотра резюме у менеджера.
        """
        return self.hh_client.get_resume_limits(manager_id)