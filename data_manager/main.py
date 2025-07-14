"""
Основной модуль data_manager.

Содержит класс DataManager — точку входа для всех операций с данными.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from api.hh.main import HHApiClient
from api.avito.main import AvitoAPIClient
from data_manager.resume_processor import ResumeProcessor
from data_manager.search_engine import SearchEngine
from database.repository import ResumeRepository
from redis_manager import RedisManager
from database.session import get_db
from utils.logger import setup_logger
from threading import Thread

logger = setup_logger(__name__)


class DataManager:
    """
    Главный класс, объединяющий все компоненты data_manager.
    
    Attributes:
        hh_client (HHApiClient): Клиент для обращения к HeadHunter API.
        search_engine (SearchEngine): Логика поиска и кэширования.
        resume_repo (ResumeRepository): Работа с резюме в базе данных.
        redis_manager (RedisManager): Для хранения задач и прогресса.
    """

    def __init__(self):
        self.hh_client = HHApiClient()
        self.avito_client = AvitoAPIClient()
        self.search_engine = SearchEngine(self.hh_client)
        self.resume_repo = ResumeRepository(next(get_db()))
        self.redis_manager = RedisManager()

    def search_resumes(
    self,
    keywords: str,
    salary_to: Optional[int] = None,
    region: List[str] = ["113"],
    not_living: bool = False,
    total: int = 50,
    per_page: int = 50,
    description: Optional[str] = "",
    source: str = "hh",
) -> str:
        """
        Синхронно выполняет поиск резюме и сохраняет результаты.
        Возвращает task_id для последующего получения результата.
        """
        task_id = self.redis_manager.create_task([], description=description)

        try:
            resumes = self.search_engine.search(
                keywords=keywords,
                salary_to=salary_to,
                region=region,
                not_living=not_living,
                total=total,
                per_page=per_page,
                source=source,
            )
            if not isinstance(resumes, list):
                logger.error("Ошибка поиска: ожидался список резюме")
                resumes = []

            resume_ids = [r.get("id") for r in resumes if r.get("id")]
            self.redis_manager.update_task_resume_ids(task_id, resume_ids)
            self.redis_manager.update_task_progress(task_id, 100, "completed")
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска: {e}")
            self.redis_manager.update_task_progress(task_id, 0, "failed")
            raise  # Перебрасываем ошибку, чтобы Flask мог обработать её

        return task_id

    def get_task_resumes( # ТУТ ALTERNATE_URL
        self,
        task_id: str,
        offset: int = 0,
        limit: int = 20,
        source: str = "hh",  # Возможные значения: 'hh' или 'avito'
    ) -> Dict[str, Any]:
        """
        Возвращает список резюме по task_id.
        Если указан source='avito', загружает резюме с Avito, иначе с HH.
        Если resume_id содержит префикс (hh_ или avito_), он переопределяет источник.
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
        count = 1

        for resume_id in paginated_ids:
            str_resume_id = str(resume_id)

            # Определяем текущий источник на основе префикса или общего параметра source
            if str_resume_id.startswith("hh_"):
                current_source = "hh"
                clean_id = str_resume_id.replace("hh_", "")
            elif str_resume_id.startswith("avito_"):
                current_source = "avito"
                clean_id = str_resume_id.replace("avito_", "")
            else:
                current_source = source  # <-- Используем переданный source
                clean_id = str_resume_id

            logger.info(f"Обрабатываем резюме ID: {clean_id}, источник: {current_source} — {count}/{len(paginated_ids)}")
            count = count + 1

            # Проверяем кэш
            cached_resume = self.search_engine.get_cached_resume(clean_id, source=current_source)
            if cached_resume:
                if current_source == "avito":
                    if cached_resume['total_experience']:
                        cached_resume['total_experience'] = {'months': cached_resume.get('total_experience').get('months') * 12}
                items.append(cached_resume)
                continue

            # Загружаем полные данные в зависимости от источника
            full_resume = None
            if current_source == "hh":
                full_resume = self.hh_client.get_resume_details(clean_id)
            elif current_source == "avito":
                full_resume = self.avito_client.resume(clean_id)
                # Форматируем зарплату, если есть
                if full_resume and 'salary' in full_resume:
                    full_resume['salary'] = self.avito_client.format_salary(full_resume['salary'])
                if full_resume:
                    params = full_resume.get("params")
                    experience = params.get("experience") if params.get("experience") else 0
                    full_resume['total_experience'] = {'months': experience * 12}
                full_resume['link'] = f"{full_resume.get('url')}" #avito.ru
            else:
                logger.warning(f"Неизвестный источник резюме: {current_source}")
                continue

            if not full_resume:
                logger.warning(f"Не удалось получить полные данные резюме {clean_id} ({current_source})")
                continue
            
            # Сохраняем в кэш и добавляем в результаты
            self.search_engine.save_to_cache(full_resume, source=current_source)
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
        task_id = self.redis_manager.create_task([], description="Получение списка вакансий")

        def background_get_vacancies():
            try:
                vacancies = self.search_engine.get_company_vacancies()
                resume_ids = [v.get("id") for v in vacancies if v.get("id")]
                self.redis_manager.update_task_resume_ids(task_id, resume_ids)
                self.redis_manager.update_task_progress(task_id, 100, "completed")
            except Exception as e:
                logger.error(f"Ошибка при получении вакансий: {e}")
                self.redis_manager.update_task_progress(task_id, 0, "failed")

        Thread(target=background_get_vacancies).start()
        return task_id

    def start_get_negotiations_task(self, vacancy_id: int) -> str:
        """
        Запускает фоновую задачу получения новых откликов по вакансии.
        Returns:
            str: task_id новой задачи.
        """
        task_desc = f"Отклики по вакансии {vacancy_id}"
        task_id = self.redis_manager.create_task(description=task_desc)

        def background_get_negotiations():
            try:
                resume_ids = self.search_engine.get_new_resume_ids_from_negotiations(vacancy_id)
                self.redis_manager.update_task_resume_ids(task_id, resume_ids)
                self.redis_manager.update_task_progress(task_id, 100, "completed")
            except Exception as e:
                logger.error(f"Ошибка при получении откликов: {e}")
                self.redis_manager.update_task_progress(task_id, 0, "failed")

        Thread(target=background_get_negotiations).start()
        return task_id

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

    def get_new_resume_ids_from_negotiations(self, vacancy_id: int) -> Tuple[List[str], List[int]]:
        """
        Получает список ID новых резюме из откликов по вакансии.
        """
        negotiations = self.hh_client.get_negotiations_by_vacancy(vacancy_id)
        new_resumes = []
        n_ids = []

        for n in negotiations:
            resume = n.get("resume", {})
            if not resume:
                continue

            resume_id = resume.get("id")
            if not resume_id:
                continue

            has_updates = n.get("has_updates", False)
            if has_updates:
                n_ids.append(n.get("id"))
                new_resumes.append(resume_id)

        return new_resumes, n_ids

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
    
    def read_negotiations(self, negotiation_ids: List[int]) -> bool:
        """
        Помечает список откликов как прочитанные.
        """
        return self.search_engine.read_negotiations(negotiation_ids)

    def update_vacancies_cache(self):
        """
        Обновляет кэш вакансий в Redis.
        Вызывается ежедневно в 8:00 через APScheduler.
        """
        logger.info("Начинаем фоновое обновление кэша вакансий...")

        raw_vacancies = self.get_company_vacancies()

        if not isinstance(raw_vacancies, list):
            logger.error(f"Ожидается список вакансий, получено: {type(raw_vacancies)}")
            return {"error": "Неверный формат данных от HH"}

        vacancy_list = []
        for i, v in enumerate(raw_vacancies, start=1):
            if not isinstance(v, dict):
                logger.warning(f"Найден неверный элемент: {v!r}")
                continue

            v_id = v.get("id")
            vacancy = self.get_vacancy_by_id(v_id)
            negotiations = self.get_negotiations_by_vacancy(v_id)
            city = vacancy.get("address", {}).get("city", "") if vacancy else ""

            total = len(negotiations)
            unread = sum(1 for n in negotiations if n.get("has_updates", False))

            vacancy_list.append({
                "title": v.get("name", "Без названия"),
                "id": v_id,
                "city": city,
                "responses_total": total,
                "responses_unread": unread,
                "url": v.get("alternate_url", "#")
            })

        # Сохраняем в Redis под фиксированным ключом
        cache_key = "cached_company_vacancies"
        self.redis_manager.client.setex(cache_key, 60 * 60 * 24, json.dumps(vacancy_list, ensure_ascii=False))  # TTL: 24 часа
        logger.info(f"Кэш вакансий обновлён: {len(vacancy_list)} вакансий сохранено в Redis.")