"""
Модуль для взаимодействия с HeadHunter API.
Содержит класс HHApiClient, реализующий методы:
- Авторизация через OAuth2
- Получение резюме по ключевым словам
- Получение полных данных по отдельному резюме
- Получение вакансий компании
- Получение откликов по вакансии
- Проверка лимитов просмотра резюме
Все методы используют токен из config.conf.HH_ACCESS_TOKENS.
"""

import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
import json
from typing import List, Dict, Any, Optional
from functools import wraps
from config import conf
from utils.logger import setup_logger
from redis_manager import redis_manager
from ai import ai_evaluator

logger = setup_logger(__name__)

def parse_keywords(keywords: str) -> List[str]:
    # Ищем либо "фразы в кавычках", либо отдельные слова
    return re.findall(r'"[^"]+"|\S+', keywords)

def retry_on_limit_exceeded(max_retries=3, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            current_delay = delay

            while retries <= max_retries:
                try:
                    return func(self, *args, **kwargs)
                except requests.HTTPError as e:
                    status = e.response.status_code
                    if status in (403, 429):
                        logger.warning(f"Лимит исчерпан или слишком много запросов ({status}), переключаем токен...")
                        self.use_next_token()
                        retries += 1
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue
                    elif status == 504:  # Gateway Timeout
                        logger.warning("Получен ответ 504 Gateway Timeout. Повторяем попытку.")
                        retries += 1
                        time.sleep(current_delay)
                        current_delay *= backoff
                        continue
                    else:
                        raise
                except (requests.ConnectTimeout, requests.ConnectionError) as e:
                    logger.warning(f"Сетевая ошибка: {e}. Ждём {current_delay} секунд и повторяем...")
                    retries += 1
                    time.sleep(current_delay)
                    current_delay *= backoff
                    continue

            logger.error("Превышено количество попыток. Операция не выполнена.")
            raise Exception("Превышено количество попыток подключения к API")
        return wrapper
    return decorator


def refresh_token_if_needed(func):
    """
    Декоратор для проверки истечения срока действия токена.
    Если токен истёк — обновляет его перед выполнением метода класса.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_token_expired():
            logger.info("Текущий токен истёк. Обновляем...")
            self.refresh_access_token()
        return func(self, *args, **kwargs)
    return wrapper


class HHApiClient:
    """
    Клиент для работы с HeadHunter API.
    Attributes:
        base_url (str): Базовый URL API HH.
        client_id (str): ID клиента для OAuth.
        client_secret (str): Секретный ключ клиента.
        access_token (str): Текущий токен доступа.
        refresh_token (str): Токен для обновления доступа.
        redirect_uri (str): URI перенаправления после авторизации.
        token_expiry (datetime): Время истечения текущего токена.
        cache_ttl (int): Время жизни кэша в секундах.
    """

    CACHE_TTL = 5  # 5 секунд

    def __init__(self):
        self.base_url = "https://api.hh.ru" 
        self.client_id = conf.CLIENT_ID1
        self.client_secret = conf.CLIENT_SECRET1
        self.access_token = conf.ACCESS_TOKEN1
        self.refresh_token = conf.REFRESH_TOKEN1
        self.redirect_uri = conf.REDIRECT_URI1
        self.token_expiry = datetime.utcnow() + timedelta(days=14)
        self.cache_ttl = self.CACHE_TTL

    def _make_cache_key(self, url: str, params: dict, source: str = "hh") -> str:
        """Формирует ключ кэша на основе URL и параметров."""
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{source}_api:{url}?{sorted_params}"

    def _get_cached_response(self, url: str, params: dict) -> Optional[Dict[str, Any]]:
        """Получает закэшированный ответ из Redis."""
        cache_key = self._make_cache_key(url, params)
        cached = redis_manager.client.get(cache_key)
        if cached:
            logger.debug(f"Ответ взят из кэша: {cache_key}")
            try:
                if isinstance(cached, str):
                    return json.loads(cached)
                elif isinstance(cached, bytes):
                    return json.loads(cached.decode('utf-8'))
                else:
                    return cached
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Ошибка декодирования кэша: {cache_key}")
                return None
        return None

    def _save_to_cache(self, url: str, params: dict, data: dict) -> None:
        """Сохраняет ответ в Redis."""
        cache_key = self._make_cache_key(url, params)
        try:
            redis_manager.client.setex(cache_key, self.cache_ttl, json.dumps(data, ensure_ascii=False))
            logger.debug(f"Ответ сохранён в кэше: {cache_key}")
        except Exception as e:
            logger.warning(f"Не удалось сохранить ответ в кэше: {e}")

    def is_token_expired(self) -> bool:
        """
        Проверяет, истёк ли срок действия текущего токена.
        Returns:
            bool: True, если токен истёк.
        """
        return datetime.utcnow() >= self.token_expiry

    def use_next_token(self):
        """
        Переключается на следующий токен из списка.
        Работает только с access_token.
        """
        tokens = [token for token in conf.HH_ACCESS_TOKENS if token is not None]
        try:
            current_index = tokens.index(self.access_token)
        except ValueError:
            logger.warning("Текущий токен не найден в списке")
            current_index = -1

        next_index = (current_index + 1) % len(tokens)
        self.access_token = tokens[next_index]
        self.token_expiry = datetime.utcnow() + timedelta(days=14)
        logger.info(f"Переключились на токен {next_index}: {self.access_token[:8]}...")

    def refresh_access_token(self) -> None:
        """
        Обновляет access_token через refresh_token.
        Обновляет заголовки авторизации и время истечения токена.
        Raises:
            Exception: Если обновление не удалось.
        """
        url = "https://hh.ru/oauth/token" 
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)
            self.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            logger.info("Токен успешно обновлён")
        except requests.RequestException as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            raise
        except KeyError as e:
            logger.error(f"В ответе отсутствуют ожидаемые данные: {e}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки с текущим access_token.
        Returns:
            dict: Заголовки для запросов к API.
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "HH-User-Agent",
        }

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_all_resumes(
        self,
        keywords: str,
        region: List[str] = ["113"],
        total: int = 1,
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
    ) -> Dict[str, Any]:
        if per_page > 50:
            raise ValueError("Параметр 'per_page' не может быть больше 50.")
        if not keywords or not keywords.strip():
            raise ValueError("Параметр 'keywords' обязателен и не может быть пустым.")
        if region is None:
            raise ValueError("Параметр 'region' обязателен.")

        all_items = []
        page = 0
        empty_or_few_count = 0  # Счётчик подряд идущих неполных страниц

        # Определяем параметр relocation
        if relocation is None:
            relocation = "living_or_relocation"
        
        # Определяем статус поиска работы
        if job_search_status is None:
            job_search_status = ["active_search", "looking_for_offers"]

        while len(all_items) < total:
            remaining = total - len(all_items)
            current_per_page = min(per_page, remaining)
            keywords_list = parse_keywords(keywords)
            keywords_query = ' '.join(keywords_list)

            params = {
                "text": keywords_query,
                "relocation": relocation,
                "job_search_status": job_search_status,
                "area": region,
                "page": page,
                "per_page": current_per_page
            }

            # Параметры текстового поиска
            if text_logic:
                params["text.logic"] = text_logic
            if text_field:
                params["text.field"] = text_field
            if text_period:
                params["text.period"] = text_period

            # Параметры зарплаты
            if salary_from is not None:
                params["salary_from"] = salary_from
            if salary_to is not None:
                params["salary_to"] = salary_to
            if currency:
                params["currency"] = currency

            # Параметры фильтрации
            if age_from is not None:
                params["age_from"] = age_from
            if age_to is not None:
                params["age_to"] = age_to
            if experience:
                params["experience"] = experience
            if education_levels:
                params["education_levels"] = education_levels
            if employment:
                params["employment"] = employment
            if schedule:
                params["schedule"] = schedule
            if gender:
                params["gender"] = gender

            # Параметры дат
            if period is not None:
                params["period"] = period
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to

            # Дополнительные фильтры
            if order_by:
                params["order_by"] = order_by
            if labels:
                params["label"] = labels

            # Автоматически добавляем label для зарплаты если указана
            if salary_from is not None or salary_to is not None:
                if "label" not in params:
                    params["label"] = []
                if isinstance(params["label"], str):
                    params["label"] = [params["label"]]
                if "only_with_salary" not in params["label"]:
                    params["label"].append("only_with_salary")

            url = f"{self.base_url}/resumes"
            encoded_params = urlencode(params, doseq=True)
            full_url = f"{url}?{encoded_params}"
            logger.info(f"Выполняется GET-запрос к API HeadHunter: {full_url}")
            logger.info(f"Параметры запроса: {params}")

            cached = self._get_cached_response(url, params)
            if cached:
                logger.info(f"Получены данные из кэша для страницы {page}")
                items = cached.get("items", [])
                all_items.extend(items)
                page += 1
                # Проверка количества возвращённых резюме
                if len(items) < current_per_page:
                    empty_or_few_count += 1
                    logger.info(f"Неполная страница {page}: получено {len(items)} из {current_per_page}")
                else:
                    empty_or_few_count = 0
                if empty_or_few_count >= 3:
                    logger.info("Три подряд неполные страницы — завершаем загрузку.")
                    break
                continue

            headers = self.get_headers()
            try:
                logger.info(f"Отправляем HTTP запрос к HH API (страница {page})")
                response = requests.get(url, headers=headers, params=params)
                logger.info(f"Получен ответ от HH API: статус {response.status_code}")
                
                response.raise_for_status()
                result = response.json()
                
                # Логируем статистику ответа
                items = result.get("items", [])
                found = result.get("found", 0)
                pages = result.get("pages", 0)
                per_page_actual = result.get("per_page", 0)
                
                logger.info(f"Статистика ответа HH API:")
                logger.info(f"  - Найдено всего: {found}")
                logger.info(f"  - Страниц: {pages}")
                logger.info(f"  - На странице: {per_page_actual}")
                logger.info(f"  - Получено резюме: {len(items)}")
                
                all_items.extend(items)
                self._save_to_cache(url, params, result)
                page += 1

                if len(items) < current_per_page:
                    empty_or_few_count += 1
                else:
                    empty_or_few_count = 0

                if empty_or_few_count >= 3:
                    logger.info("Три подряд неполные страницы — завершаем загрузку.")
                    break

            except Exception as e:
                logger.error(f"Ошибка при запросе страницы {page}: {e}")
                raise

        logger.info("=== ИТОГИ ПОИСКА ===")
        logger.info(f"Всего загружено резюме: {len(all_items)}")
        logger.info(f"Обработано страниц: {page}")
        logger.info(f"Запрошено резюме: {total}")
        logger.info("=== КОНЕЦ ПОИСКА ===")
        
        return {"found": len(all_items), "items": all_items}

    def check_and_handle_resume_limit(self):
        """
        Проверяет текущие лимиты просмотра резюме.
        Если лимит исчерпан — автоматически переключается на следующий токен.
        """
        manager = self.get_current_manager()
        manager_id = manager.get("manager", {}).get("id")
        if not manager_id:
            logger.warning("Не удалось получить ID менеджера")
            return

        limits = self.get_resume_limits(manager_id)
        resume_left = limits.get("left", {}).get("resume_view", 0)

        if resume_left <= 0:
            logger.warning("Лимит просмотра резюме исчерпан. Переключаем токен.")
            self.use_next_token()

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_resume_details(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает полные данные по одному резюме.

        Args:
            resume_id (str): ID резюме.

        Returns:
            dict | None: Полные данные резюме или None, если не найдено или ошибка доступа.
        """
        self.check_and_handle_resume_limit()
        url = f"{self.base_url}/resumes/{resume_id}"
        headers = self.get_headers()
        params = {}

        logger.info(f"Запрос деталей резюме: {resume_id}")

        # Шаг 1: Проверяем кэш
        cached = self._get_cached_response(url, params)
        if cached:
            logger.info(f"Резюме {resume_id} получено из кэша")
            return cached

        # Шаг 2: Делаем запрос
        try:
            logger.info(f"Отправляем HTTP запрос для резюме {resume_id}")
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"Получен ответ для резюме {resume_id}: статус {response.status_code}")
            
            response.raise_for_status()
            resume_data = response.json()
            
            # Логируем основную информацию о резюме
            title = resume_data.get("title", "Без названия")
            area = resume_data.get("area", {}).get("name", "Не указан")
            salary = resume_data.get("salary", {})
            salary_amount = salary.get("amount") if salary else None
            
            logger.info(f"Детали резюме {resume_id}:")
            logger.info(f"  - Название: {title}")
            logger.info(f"  - Регион: {area}")
            logger.info(f"  - Зарплата: {salary_amount}")

            # Шаг 3: Сохраняем в кэш
            self._save_to_cache(url, params, resume_data)
            logger.info(f"Резюме {resume_id} сохранено в кэш")
            return resume_data
        except requests.HTTPError as e:
            if response.status_code == 404:
                logger.warning(f"Резюме не найдено: {resume_id}")
                return None
            elif response.status_code == 403:
                logger.warning(f"Нет доступа к резюме {resume_id}: лимит просмотров исчерпан")
                return None
            else:
                logger.error(f"Ошибка при получении данных резюме {resume_id}: {e}")
                raise
        except requests.RequestException as e:
            logger.error(f"Сетевая ошибка при получении резюме {resume_id}: {e}")
            raise

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_employer_vacancies(self, employer_id: int, per_page: int = 50) -> List[Dict[str, Any]]:
        """
        Получает все вакансии работодателя до тех пор, пока они есть.

        Args:
            employer_id (int): ID работодателя.
            per_page (int): Сколько вакансий запрашивать за раз (максимум 50).

        Returns:
            list[dict]: Полный список вакансий.
        """
        url = f"{self.base_url}/vacancies"
        headers = self.get_headers()
        params = {
            "employer_id": employer_id,
            "per_page": per_page
        }

        all_vacancies = []
        page = 0

        while True:
            params["page"] = page

            logger.debug(f"Запрашиваем страницу {page}")

            # Попробуем получить из кэша
            cached = self._get_cached_response(url, params)
            if cached and isinstance(cached, dict):
                items = cached.get("items", [])
                all_vacancies.extend(items)
                logger.debug(f"Из кэша получено {len(items)} вакансий, всего: {len(all_vacancies)}")
                page += 1
                continue

            # Запрос к API
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                all_vacancies.extend(items)
                self._save_to_cache(url, params, data)

                logger.debug(f"Получено {len(items)} вакансий со страницы {page}, всего: {len(all_vacancies)}")

                if len(items) < per_page:
                    logger.debug("Достигнут конец списка вакансий.")
                    break

                page += 1

            except requests.RequestException as e:
                logger.error(f"Ошибка при получении вакансий: {e}")
                raise

        return all_vacancies

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_vacancy_by_id(self, vacancy_id: int):
        """
        Получение данных о вакансии по ID
        """
        url = f"{self.base_url}/vacancies/{vacancy_id}"
        headers = self.get_headers()
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        vacancy = response.json()
        
        return vacancy

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_negotiations_by_vacancy(self, vacancy_id: int, per_page: int = 50) -> List[Dict[str, Any]]:
        """
        Получает ВСЕ отклики по вакансии до тех пор, пока они есть.

        Args:
            vacancy_id (int): ID вакансии.
            per_page (int): Сколько откликов запрашивать за раз (максимум 50).

        Returns:
            list[dict]: Полный список откликов.
        """
        logger.debug(f"Получаем отклики к вакансии {vacancy_id}")

        url = f"{self.base_url}/negotiations/response"
        headers = self.get_headers()
        params = {
            "vacancy_id": vacancy_id,
            "per_page": per_page
        }

        all_negotiations = []
        page = 0

        while True:
            params["page"] = page

            logger.debug(f"Запрашиваем страницу {page} для вакансии {vacancy_id}")

            # Попробуем получить из кэша
            cached = self._get_cached_response(url, params)
            if cached and isinstance(cached, dict):
                items = cached.get("items", [])
                all_negotiations.extend(items)
                logger.debug(f"Из кэша получено {len(items)} откликов со страницы {page}, всего: {len(all_negotiations)}")
                page += 1
                continue

            # Делаем запрос к API
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                all_negotiations.extend(items)
                self._save_to_cache(url, params, data)

                logger.debug(f"Получено {len(items)} откликов со страницы {page}, всего: {len(all_negotiations)}")

                if len(items) < per_page:
                    logger.debug(f"Достигнут конец списка откликов для вакансии {vacancy_id}")
                    break

                page += 1

            except requests.RequestException as e:
                logger.error(f"Ошибка при получении откликов: {e}")
                raise

        logger.debug(f"Всего получено {len(all_negotiations)} откликов по вакансии {vacancy_id}")

        return all_negotiations

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_new_negotiations_by_vacancy(self, vacancy_id: int, per_page: int = 50) -> List[Dict[str, Any]]:
        """
        Получает только новые (непрочитанные) отклики по вакансии.
        Args:
            vacancy_id (int): ID вакансии.
            total (int): Общее количество откликов, которое нужно получить.
            per_page (int): Сколько откликов запрашивать за раз (максимум 50).
        Returns:
            list[dict]: Список новых откликов.
        """
        all_negotiations = self.get_negotiations_by_vacancy(vacancy_id, per_page=per_page)
        return [n for n in all_negotiations if n.get("has_updates", False)]

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_resume_limits(self, manager_id: int) -> Dict[str, Any]:
        """
        Получает информацию о лимитах на просмотр резюме у менеджера.
        Если лимит исчерпан (left.resume_view == 0), автоматически переключается на следующий токен.

        Args:
            manager_id (int): ID менеджера.

        Returns:
            dict: Информация о лимитах.
        """
        url = f"{self.base_url}/employers/{conf.DEFAULT_EMPLOYER_ID}/managers/{manager_id}/limits/resume"
        headers = self.get_headers()
        params = {}

        cached = self._get_cached_response(url, params)
        if cached:
            return cached

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            limits_data = response.json()
            logger.debug(f"Получены лимиты просмотра резюме: {limits_data}")

            # Проверяем, не исчерпан ли лимит
            resume_left = limits_data.get("left", {}).get("resume_view", 0)
            if resume_left == 0:
                logger.warning("Лимит просмотра резюме исчерпан. Переключаем токен.")
                self.use_next_token()  # Меняем токен глобально

            self._save_to_cache(url, params, limits_data)
            return limits_data

        except requests.RequestException as e:
            logger.error(f"Ошибка при получении лимитов просмотра резюме: {e}")
            raise

    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def get_current_manager(self) -> Dict[str, Any]:
        """
        Получает информацию о текущем пользователе (менеджере).

        Returns:
            dict: Информация о менеджере.
        """
        url = f"{self.base_url}/me"
        headers = self.get_headers()
        params = {}

        cached = self._get_cached_response(url, params)
        if cached:
            return cached

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            manager_data = response.json()
            logger.debug(f"Получены данные текущего менеджера")
            self._save_to_cache(url, params, manager_data)
            return manager_data
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении данных о менеджере: {e}")
            raise
    
    @retry_on_limit_exceeded(max_retries=5, delay=2)
    @refresh_token_if_needed
    def read_negotiations(self, negotiation_ids: List[int]) -> bool:
        """
        Помечает отклики как прочитанные.
        https://dev.hh.ru/doc_api_negotiations.html#post-read 
        """
        url = f"{self.base_url}/negotiations/read"
        headers = self.get_headers()
        params = {"topic_id": negotiation_ids}

        response = requests.post(url, headers=headers, params=params)
        
        if response.status_code == 204:
            return True  # Успешно
        else:
            logger.warning(f"Ошибка при пометке откликов как прочитанных: {response.status_code}, {response.text}")
            return False