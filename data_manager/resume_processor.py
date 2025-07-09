from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid
from utils.logger import setup_logger
from redis_manager import redis_manager


logger = setup_logger(__name__)


class ResumeProcessor:
    """
    Обрабатывает сырой JSON от HeadHunter и формирует словарь с ключевыми полями.

    Attributes:
        raw_data (dict): Сырые данные резюме из API HH.
        use_cache (bool): Использовать ли кэширование через Redis.
        cache_ttl (int): Время жизни кэша в секундах.
    """

    CACHE_TTL = 60 * 60 * 24  # 24 часа

    def __init__(self, raw_data: Dict[str, Any], use_cache: bool = True):
        self.raw_data = raw_data
        self.use_cache = use_cache
        self.cache_ttl = self.CACHE_TTL

    def _make_cache_key(self, resume_id: str) -> str:
        """Формирует ключ для Redis на основе ID резюме."""
        return f"processed_resume:{resume_id}"

    def _get_cached_processed_resume(self) -> Optional[Dict[str, Any]]:
        """Получает обработанное резюме из Redis по ID."""
        if not self.use_cache:
            return None

        resume_id = self.raw_data.get("id")
        if not resume_id:
            return None

        cache_key = self._make_cache_key(resume_id)
        cached = redis_manager.client.get(cache_key)
        if cached:
            logger.debug(f"Резюме {resume_id} взято из Redis-кэша")
            return json.loads(cached)
        return None

    def _save_processed_resume(self, processed_data: Dict[str, Any]) -> None:
        """Сохраняет обработанное резюме в Redis."""
        if not self.use_cache:
            return

        resume_id = processed_data.get("id") or str(uuid.uuid4())
        cache_key = self._make_cache_key(resume_id)

        try:
            redis_manager.client.setex(cache_key, self.cache_ttl, json.dumps(processed_data))
            logger.debug(f"Резюме {resume_id} сохранено в Redis")
        except Exception as e:
            logger.warning(f"Не удалось сохранить резюме в Redis: {e}")

    def process(self) -> Dict[str, Any]:
        """
        Извлекает необходимые поля из резюме.

        Проверяет кэш в Redis. Если есть — возвращает из кэша.
        Если нет — обрабатывает и сохраняет в кэш.

        Returns:
            dict: Обработанные данные резюме.
        """
        # Шаг 1: Попробуем получить из кэша
        cached = self._get_cached_processed_resume()
        if cached:
            return cached

        # Шаг 2: Проверяем, что raw_data корректный
        if not isinstance(self.raw_data, dict):
            logger.error("Неверные данные для обработки резюме: ожидался словарь")
            raise ValueError("raw_data должен быть словарём")

        # Шаг 3: Обработка сырых данных
        try:
            resume_id = self.raw_data.get("id", "unknown")

            result = {
                "id": resume_id,
                "full_name": self._get_full_name(),
                "first_name": self.raw_data.get("first_name", ""),
                "middle_name": self.raw_data.get("middle_name", ""),  # 👈 Добавили
                "last_name": self.raw_data.get("last_name", ""),
                "age": self._get_age(),
                "contacts": self._get_contacts(),
                "location": self._get_location(),
                "resume_title": self._get_title(),
                "salary_amount": self.raw_data.get("salary", {}).get("amount") if self.raw_data.get("salary") else None,
                "salary_currency": self.raw_data.get("salary", {}).get("currency") if self.raw_data.get("salary") else None,
                "experience": self._get_experience(),  # Это строка JSON
                "link": self._get_link(),
                "received_at": datetime.utcnow().isoformat()
            }

            # Шаг 4: Сохраняем в Redis
            self._save_processed_resume(result)

            logger.debug(f"Резюме {resume_id} успешно обработано")
            return result

        except Exception as e:
            logger.error(f"Ошибка при обработке резюме: {e}")
            raise

    def _get_full_name(self) -> str:
        first = self.raw_data.get("first_name")
        middle = self.raw_data.get("middle_name")
        last = self.raw_data.get("last_name")

        parts = [first, middle, last]
        full_name = " ".join([p for p in parts if p])
        return full_name or "Не указан"

    def _get_age(self) -> Optional[int]:
        age = self.raw_data.get("age")
        if isinstance(age, int):
            return age
        return None

    def _get_contacts(self) -> str:
        """Получает контакты (email, телефон)."""
        contacts = []

        for contact in self.raw_data.get("contact", []):
            contact_type = contact.get("type", {}).get("id")
            value = contact.get("value")
            if contact_type == "email":
                contacts.append(f"Email: {value}")
            elif contact_type == "cell":
                contacts.append(f"Телефон: {value}")

        return "; ".join(contacts) if contacts else "Не указано"

    def _get_location(self) -> str:
        """Получает местоположение соискателя."""
        area = self.raw_data.get("area", {})
        return area.get("name", "Не указано")

    def _get_title(self) -> str:
        """Получает название резюме (должность)."""
        return self.raw_data.get("title", "Без названия")

    def _get_experience(self) -> str:
        """Получает опыт работы в виде JSON-строки."""
        experience = self.raw_data.get("experience", [])
        return json.dumps(experience, ensure_ascii=False)

    def _get_link(self) -> str:
        """Получает ссылку на резюме."""
        return self.raw_data.get("link", "")