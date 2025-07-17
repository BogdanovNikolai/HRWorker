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
from api.avito.main import AvitoAPIClient
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

    def __init__(self, hh_client: Optional[HHApiClient] = None, avito_client: Optional[AvitoAPIClient] = None):
        self.hh_client = hh_client or HHApiClient()
        self.avito_client = avito_client or AvitoAPIClient()
        self.resume_repo = ResumeRepository(db=next(get_db()))
        self.ttl_hours = 48  # Значение из config.conf.TTL_HOURS

    def check_cache(self, resume_id: str, source: str = "hh") -> bool:
        """
        Проверяет, есть ли резюме в кэше и актуально ли оно.

        Args:
            resume_id (str): ID резюме.
            source (str): Источник резюме ("hh" или "avito").

        Returns:
            bool: True, если резюме существует и актуально.
        """
        cached = self.resume_repo.get_by_source_and_resume_id(source=source, resume_id=str(resume_id))
        if not cached:
            return False
        return self.is_cache_valid(cached)

    def get_cached_resume(self, resume_id: str, source: str = "hh") -> Optional[Dict[str, Any]]:
        """
        Возвращает резюме из кэша (БД), если оно есть и актуально.

        Args:
            resume_id (str): ID резюме.
            source (str): Источник ("hh" или "avito").

        Returns:
            dict | None: Резюме из кэша или None.
        """
        resume_url = f"https://hh.ru/resume/{resume_id}" 
        cached = self.resume_repo.get_by_source_and_resume_id(source=source, resume_id=str(resume_id))
        if not cached:
            return None
        if not self.is_cache_valid(cached):
            logger.warning(f"Резюме {resume_id} ({source}) устарело")
            return None
        return self._format_cached_resume(cached)

    def is_cache_valid(self, resume: Any) -> bool:
        """
        Проверяет, истёк ли срок жизни резюме.

        Args:
            resume: Резюме из кэша (объект БД).

        Returns:
            bool: True, если резюме ещё актуально.
        """
        now = datetime.utcnow()
        expiry_time = resume.received_at + timedelta(hours=self.ttl_hours)
        return now <= expiry_time

    def save_to_cache(self, resume_data: Dict[str, Any], source: str = "hh") -> None:
        """
        Сохраняет резюме в БД без изменений.
        """
        if not resume_data.get("id"):
            logger.warning("Резюме без ID не может быть сохранено")
            return

        if self.resume_repo.resume_exists(resume_data["id"], source):
            logger.debug(f"Резюме {resume_data['id']} ({source}) уже существует в БД. Пропускаем сохранение.")
            return

        try:
            self.resume_repo.create_resume(resume_data, source)
        except Exception as e:
            logger.error(f"Ошибка при сохранении резюме в БД: {e}")

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
            "link": db_resume.link,
            "source": db_resume.source,
        }

    def search(
    self,
    keywords: str,
    source: str = "hh",
    region: List[str] = ["113"],
    total: int = 50,
    per_page: int = 50,
    description: Optional[str] = "",
    # Параметры текстового поиска
    text_logic: Optional[str] = None,
    text_field: Optional[str] = None,
    text_period: Optional[str] = None,
    # Параметры зарплаты
    salary_from: Optional[int] = None,
    salary_to: Optional[int] = None,
    currency: Optional[str] = None,
    # Параметры фильтрации
    age_from: Optional[int] = None,
    age_to: Optional[int] = None,
    experience: Optional[List[str]] = None,
    education_levels: Optional[List[str]] = None,
    employment: Optional[List[str]] = None,
    schedule: Optional[List[str]] = None,
    gender: Optional[str] = None,
    job_search_status: Optional[List[str]] = None,
    # Параметры дат
    period: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    # Параметры переезда
    relocation: Optional[str] = None,
    # Дополнительные фильтры
    order_by: Optional[str] = None,
    labels: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
        """
        Выполняет поиск резюме по ключевым словам и фильтрам.
        Возвращает сырые данные резюме.
        
        Args:
            source (str): Источник поиска — "hh" или "avito".
        """
        logger.info(f"Начинаем поиск резюме на {source}: {keywords}, зарплата до {salary_to}, регион {region}")
        
        if source == "hh":
            # Логируем входные параметры
            logger.info("=== ПАРАМЕТРЫ ПОИСКА ===")
            logger.info(f"Ключевые слова: {keywords}")
            logger.info(f"Регион: {region}")
            logger.info(f"Общее количество: {total}")
            logger.info(f"На страницу: {per_page}")
            logger.info(f"Описание: {description}")
            
            # Логируем текстовые параметры
            if any([text_logic, text_field, text_period]):
                logger.info("--- Текстовые параметры ---")
                logger.info(f"Логика поиска: {text_logic}")
                logger.info(f"Поле поиска: {text_field}")
                logger.info(f"Период опыта: {text_period}")
            
            # Логируем параметры зарплаты
            if any([salary_from, salary_to, currency]):
                logger.info("--- Параметры зарплаты ---")
                logger.info(f"Зарплата от: {salary_from}")
                logger.info(f"Зарплата до: {salary_to}")
                logger.info(f"Валюта: {currency}")
            
            # Логируем параметры фильтрации
            if any([age_from, age_to, experience, education_levels, employment, schedule, gender, job_search_status]):
                logger.info("--- Параметры фильтрации ---")
                logger.info(f"Возраст от: {age_from}")
                logger.info(f"Возраст до: {age_to}")
                logger.info(f"Опыт работы: {experience}")
                logger.info(f"Образование: {education_levels}")
                logger.info(f"Тип занятости: {employment}")
                logger.info(f"График работы: {schedule}")
                logger.info(f"Пол: {gender}")
                logger.info(f"Статус поиска: {job_search_status}")
            
            # Логируем параметры дат
            if any([period, date_from, date_to]):
                logger.info("--- Параметры дат ---")
                logger.info(f"Период (дни): {period}")
                logger.info(f"Дата от: {date_from}")
                logger.info(f"Дата до: {date_to}")
            
            # Логируем параметры переезда
            if relocation:
                logger.info("--- Параметры переезда ---")
                logger.info(f"Готовность к переезду: {relocation}")
            
            # Логируем дополнительные фильтры
            if any([order_by, labels]):
                logger.info("--- Дополнительные фильтры ---")
                logger.info(f"Сортировка: {order_by}")
                logger.info(f"Метки: {labels}")
            
            logger.info("=== КОНЕЦ ПАРАМЕТРОВ ===")
            
            raw_search_result = self.hh_client.get_all_resumes(
                keywords=keywords,
                region=region,
                total=total,
                per_page=per_page,
                description=description,
                # Параметры текстового поиска
                text_logic=text_logic,
                text_field=text_field,
                text_period=text_period,
                # Параметры зарплаты
                salary_from=salary_from,
                salary_to=salary_to,
                currency=currency,
                # Параметры фильтрации
                age_from=age_from,
                age_to=age_to,
                experience=experience,
                education_levels=education_levels,
                employment=employment,
                schedule=schedule,
                gender=gender,
                job_search_status=job_search_status,
                # Параметры дат
                period=period,
                date_from=date_from,
                date_to=date_to,
                # Параметры переезда
                relocation=relocation,
                # Дополнительные фильтры
                order_by=order_by,
                labels=labels,
            )
        elif source == "avito":
            raw_search_result = self.avito_client.resumes(
                query=keywords,
                # location=region,
                total=total,
            )
            
            for item in raw_search_result.get("items", []):
                if 'salary' in item:
                    item['salary'] = self.avito_client.format_salary(item['salary'])
        else:
            raise ValueError(f"Неизвестный источник: {source}")

        found = raw_search_result.get("found", 0)
        items = raw_search_result.get("items", [])

        logger.info(f"Найдено {len(items)} резюме на {source}")
        
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
            # Поддержка разных источников через префикс или словарь
            if resume_id.startswith("hh_"):
                source = "hh"
                clean_id = resume_id.replace("hh_", "")
            elif resume_id.startswith("avito_"):
                source = "avito"
                clean_id = resume_id.replace("avito_", "")
            else:
                source = "hh"
                clean_id = resume_id

            cached_resume = self.get_cached_resume(clean_id, source)
            if cached_resume:
                items.append(cached_resume)
                continue

            if source == "hh":
                full_resume = self.hh_client.get_resume_details(clean_id)
            elif source == "avito":
                full_resume = self.avito_client.resume(clean_id)
                full_resume['link'] = f"{full_resume.get('url')}" #avito.ru
            else:
                logger.warning(f"Неизвестный источник резюме: {source}")
                continue

            if not full_resume:
                logger.warning(f"Не удалось получить полные данные резюме {clean_id} ({source})")
                continue

            self.save_to_cache(full_resume, source)
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
    
    # --- Методы для работы с вакансиями Avito ---
    def get_company_vacancies_avito(self) -> Dict[str, Any]:
        """
        Получает список вакансий компании через Avito API.
        Returns:
            dict: Словарь с ключами 'found' и 'items'.
        """
        return self.avito_client.get_vacancies()
    
    def get_vacancy_by_id_avito(self, vacancy_id: int) -> Dict[str, Any]:
        """Получает вакансию по ID через Avito API."""
        return self.avito_client.get_vacancy_by_id(vacancy_id=vacancy_id)
    
    def get_negotiations_by_vacancy_avito(self, vacancy_id) -> Dict[str, Any]:
        """
        Получает список откликов по конкретной вакансии через Avito API.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            dict: Словарь с ключами 'found' и 'items'.
        """
        # Получаем все ID откликов с обязательным параметром updatedAtFrom
        from datetime import datetime, timedelta
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        applications_dict = self.avito_client.get_application_ids(updated_at_from=month_ago)
        application_list = applications_dict.get('applies', [])
        
        if not application_list:
            return {"found": 0, "items": []}
        
        # Получаем ID откликов
        application_ids = [app['id'] for app in application_list]
        
        # Получаем детали откликов
        applications = self.avito_client.get_applications_by_ids(application_ids)
        applies = applications.get('applies', [])
        
        # Фильтруем отклики по конкретной вакансии
        filtered_applies = [app for app in applies if app.get('vacancy_id') == vacancy_id]
        
        return {
            "found": len(filtered_applies),
            "items": filtered_applies
        }
    
    def get_new_negotiations_by_vacancy_avito(self, vacancy_id) -> Dict[str, Any]:
        """
        Получает список новых откликов по конкретной вакансии через Avito API.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            dict: Словарь с ключами 'found' и 'items'.
        """
        # Получаем все ID откликов с фильтром по дате (например, за последний месяц)
        from datetime import datetime, timedelta
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        applications_dict = self.avito_client.get_application_ids(updated_at_from=month_ago)
        application_list = applications_dict.get('applies', [])
        
        if not application_list:
            return {"found": 0, "items": []}
        
        # Получаем ID откликов
        application_ids = [app['id'] for app in application_list]
        
        # Получаем детали откликов
        applications = self.avito_client.get_applications_by_ids(application_ids)
        applies = applications.get('applies', [])
        
        # Фильтруем отклики по конкретной вакансии и только непросмотренные
        filtered_applies = [
            app for app in applies 
            if app.get('vacancy_id') == vacancy_id and not app.get('is_viewed', False)
        ]
        
        return {
            "found": len(filtered_applies),
            "items": filtered_applies
        }
    
    def get_resume_ids_from_negotiations_avito(self, vacancy_id: int) -> List[str]:
        """
        Получает список ID резюме из откликов по вакансии Avito.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            list[str]: Список ID резюме.
        """
        negotiations = self.avito_client.get_vacancy_responses(vacancy_id)
        resume_ids = []
        for n in negotiations.get("items", []):
            if n.get("resume_id"):
                resume_ids.append(f"avito_{n['resume_id']}")
        return resume_ids
    
    def get_new_resume_ids_from_negotiations_avito(self, vacancy_id: int) -> List[str]:
        """
        Получает список ID новых резюме из откликов по вакансии Avito.
        Args:
            vacancy_id (int): ID вакансии.
        Returns:
            list[str]: Список ID новых резюме.
        """
        negotiations = self.avito_client.get_new_vacancy_responses(vacancy_id)
        resume_ids = []
        for n in negotiations.get("items", []):
            if n.get("resume_id"):
                resume_ids.append(f"avito_{n['resume_id']}")
        return resume_ids
    
    def read_negotiations_avito(self, vacancy_id: int, response_ids: List[int]) -> bool:
        """
        Помечает список откликов как прочитанные через Avito API.
        Args:
            vacancy_id (int): ID вакансии.
            response_ids (List[int]): Список ID откликов для отметки как прочитанные.
        Returns:
            bool: True если успешно, False в противном случае.
        """
        # В Avito API нет прямого метода для отметки откликов как прочитанные
        # Можно реализовать через обновление статуса или просто возвращать True
        # так как основная логика - это получение откликов
        return True