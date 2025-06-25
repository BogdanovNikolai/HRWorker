"""
Модуль поиска резюме по ключевым словам.

Содержит класс SearchEngine для работы с фильтрами, TTL проверкой и Redis-кэшированием.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database.repository import ResumeRepository
from database.session import get_db
from data_manager.resume_processor import ResumeProcessor
from api.hh.main import HHApiClient
from utils.logger import setup_logger
from redis_manager import redis_manager
from config import conf

logger = setup_logger(__name__)


class SearchEngine:
    """
    Реализует логику поиска резюме по заданным параметрам.

    Attributes:
        hh_client (HHApiClient): Клиент для обращения к HeadHunter API.
        resume_repo (ResumeRepository): Репозиторий для работы с БД.
        ttl_hours (int): Время жизни кэшированного резюме.
    """

    def __init__(self, hh_client: HHApiClient = None):
        self.hh_client = hh_client or HHApiClient()
        self.resume_repo = ResumeRepository(db=next(get_db()))
        self.ttl_hours = 48  # Значение из config.conf.TTL_HOURS

    def check_cache(self, resume_id: str) -> bool:
        """
        Проверяет, есть ли резюме в кэше и актуально ли оно.

        Args:
            resume_id (str): ID резюме.

        Returns:
            bool: True, если резюме существует и актуально.
        """
        cached = self.resume_repo.get_by_link(resume_id)
        if not cached:
            return False
        return self.is_cache_valid(cached)

    def get_cached_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает резюме из кэша (БД), если оно есть и актуально.

        Args:
            resume_id (str): ID резюме.

        Returns:
            dict | None: Резюме из кэша или None.
        """
        resume_url = f"https://hh.ru/resume/{resume_id}" 
        cached = self.resume_repo.get_by_link(resume_url)
        if not cached:
            return None
        if not self.is_cache_valid(cached):
            logger.warning(f"Резюме {resume_id} устарело")
            return None
        return self._format_cached_resume(cached)

    def is_cache_valid(self, resume: Dict[str, Any]) -> bool:
        """
        Проверяет, истёк ли срок жизни резюме.

        Args:
            resume (dict): Резюме из кэша.

        Returns:
            bool: True, если резюме ещё актуально.
        """
        now = datetime.utcnow()
        expiry_time = resume.received_at + timedelta(hours=self.ttl_hours)
        return now <= expiry_time

    def save_to_cache(self, resume_data: Dict[str, Any]) -> None:
        """
        Сохраняет резюме в кэш (БД) без изменений.
        """
        if not resume_data.get("id"):
            logger.warning("Резюме без ID не может быть сохранено")
            return

        if self.resume_repo.resume_exists(resume_data["id"]):
            logger.debug(f"Резюме {resume_data['id']} уже существует в БД. Пропускаем сохранение.")
            return

        try:
            self.resume_repo.create_resume(resume_data)
        except Exception as e:
            logger.error(f"Ошибка при сохранении резюме в кэш: {e}")

    def _format_cached_resume(self, db_resume: Any) -> Dict[str, Any]:
        try:
            salary = json.loads(db_resume.salary_json) if db_resume.salary_json else {}
        except json.JSONDecodeError:
            salary = {}

        try:
            experience = json.loads(db_resume.experience) if db_resume.experience else []
        except json.JSONDecodeError:
            experience = []

        return {
            "id": db_resume.id,
            "title": db_resume.title,
            "first_name": db_resume.first_name or "",
            "middle_name": db_resume.middle_name or "",
            "last_name": db_resume.last_name or "",
            "age": db_resume.age,
            "area": {"name": db_resume.location} if db_resume.location else {},
            "salary": salary,
            "experience": experience,
            "total_experience": {"months": db_resume.total_experience_months} if db_resume.total_experience_months else None,
            "alternate_url": db_resume.link
        }

    def search(
    self,
    keywords: str,
    salary_to: Optional[int] = None,
    region: List[str] = ["113"],
    total: int = 50,
    per_page: int = 50,
    description: Optional[str] = ""
) -> List[Dict[str, Any]]:
        """
        Выполняет поиск резюме по ключевым словам и фильтрам.
        Возвращает сырые данные резюме.
        """
        logger.info(f"Начинаем поиск резюме: {keywords}, зарплата до {salary_to}, регион {region}")
        
        raw_search_result = self.hh_client.get_all_resumes(
            keywords=keywords,
            salary_to=salary_to,
            region=region,
            total=total,
            per_page=per_page,
            description=description
        )

        found = raw_search_result.get("found", 0)
        items = raw_search_result.get("items", [])

        logger.info(f"Найдено {len(items)} резюме")
        
        return items

    def get_task_resumes(
    self,
    task_id: str,
    offset: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
        """
        Возвращает список резюме по task_id без пагинации — по смещению и лимиту.
        Args:
            task_id (str): Идентификатор задачи.
            offset (int): Смещение от начала списка.
            limit (int): Максимальное количество резюме для возврата.
        Returns:
            dict: Результаты поиска с метаданными (found, items).
        """
        task_data = redis_manager.get_task(task_id)

        if not task_data:
            logger.warning(f"Задача {task_id} не найдена или просрочена")
            return {
                "error": "Задача не найдена или истекло время жизни"
            }

        # Проверяем тип данных и извлекаем resume_ids
        if isinstance(task_data, dict):
            resume_ids = task_data.get("resume_ids", [])
        else:
            resume_ids = task_data

        if not isinstance(resume_ids, list):
            logger.error(f"Неверный формат resume_ids в задаче {task_id}: {type(resume_ids)}")
            return {"error": "Неверный формат данных задачи", "found": 0, "items": []}

        found = len(resume_ids)
        paginated_ids = resume_ids[offset : offset + limit]
        items = []

        for resume_id in paginated_ids:
            cached_resume = self.get_cached_resume(resume_id)
            if cached_resume:
                items.append(cached_resume)
                continue

            full_resume = self.hh_client.get_resume_details(resume_id)
            if not full_resume:
                logger.warning(f"Не удалось получить полные данные резюме {resume_id}")
                continue

            self.save_to_cache(full_resume)
            items.append(full_resume)

        return {
            "found": found,
            "items": items,
            "task_id": task_id
        }
    
    def get_company_vacancies(self) -> List[Dict[str, Any]]:
        """
        Получает список вакансий компании через HH API.
        Returns:
            list[dict]: Список вакансий.
        """
        return self.hh_client.get_employer_vacancies(employer_id=conf.DEFAULT_EMPLOYER_ID)
    
    def get_vacancy_by_id(self, vacancy_id: int):
        return self.hh_client.get_vacancy_by_id(vacancy_id=vacancy_id)
    
    def get_negotiations_by_vacancy(self, vacancy_id) -> List[Dict[str, Any]]:
        """
        Получает список откликов по конкретной вакансии.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            list[dict]: Список откликов.
        """
        return self.hh_client.get_negotiations_by_vacancy(vacancy_id=vacancy_id)
    
    def get_resume_ids_from_negotiations(self, vacancy_id: int) -> List[str]:
        """
        Получает список ID резюме из откликов по вакансии.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            list[str]: Список ID резюме.
        """
        negotiations = self.hh_client.get_negotiations_by_vacancy(vacancy_id)
        resume_ids = [n["resume"]["id"] for n in negotiations if n.get("resume")]
        return resume_ids
    
    # def get_new_resume_ids_from_negotiations(self, vacancy_id: int) -> List[str]:
    #     """
    #     Получает список ID новых резюме из откликов по вакансии.
    #     Args:
    #         vacancy_id (int): ID вакансии.
    #     Returns:
    #         list[str]: Список ID новых резюме.
    #     """
    #     negotiations = self.hh_client.get_new_negotiations_by_vacancy(vacancy_id)
    #     resume_ids = [n["resume"]["id"] for n in negotiations if n.get("resume")]
    #     return resume_ids
    
    def read_negotiations(self, negotiation_ids: List[int]) -> bool:
        """
        Помечает отклики как прочитанные через HH API.
        """
        return self.hh_client.read_negotiations(negotiation_ids)