"""
Модуль экспорта данных.

Содержит классы для выгрузки резюме в форматы CSV/XLSX.
"""

import csv
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from redis_manager import redis_manager
from data_manager.resume_processor import ResumeProcessor
from database.repository import ResumeRepository
from database.session import get_db
from utils.logger import setup_logger


logger = setup_logger(__name__)


class Exporter:
    """
    Базовый класс для экспорта резюме в различные форматы.

    Attributes:
        data (list): Список резюме для экспорта.
        resume_repo (ResumeRepository): Репозиторий для работы с БД.
    """

    def __init__(self, data: List[Dict[str, Any]] = None):
        self.data = data or []
        self.resume_repo = ResumeRepository(next(get_db()))

    def load_from_cache(self, task_id: str) -> None:
        """
        Загружает данные по task_id из Redis.

        Args:
            task_id (str): Идентификатор задачи.
        """
        resume_ids = redis_manager.get_task(task_id)
        if not resume_ids:
            logger.warning(f"Задача {task_id} не найдена или истекло время жизни")
            return

        items = []
        for resume_id in resume_ids:
            cached = self._get_cached_resume(resume_id)
            if cached:
                items.append(cached)

        self.data = items

    def _get_cached_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает резюме из кэша или из БД.

        Args:
            resume_id (str): ID резюме.

        Returns:
            dict | None: Обработанные данные резюме.
        """
        # Попробуем получить из Redis
        cache_key = f"processed_resume:{resume_id}"
        cached = redis_manager.client.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.warning(f"Не удалось расшифровать кэш {cache_key}: {e}")

        # Если нет — получаем из БД
        resume_url = f"https://hh.ru/resume/{resume_id}" 
        db_resume = self.resume_repo.get_by_link(resume_url)
        if not db_resume:
            logger.warning(f"Резюме {resume_id} не найдено в БД")
            return None

        # Обрабатываем и сохраняем в кэш
        try:
            processed = ResumeProcessor(db_resume.__dict__).process()
            redis_manager.client.setex(cache_key, 86400, json.dumps(processed))
            return processed
        except Exception as e:
            logger.error(f"Ошибка при обработке резюме {resume_id}: {e}")
            return None

    def prepare_data(self) -> List[Dict[str, Any]]:
        """
        Подготавливает данные для экспорта — оставляет только нужные поля,
        корректно обрабатывает зарплату и город, вместо пустого значения ставит "—".
        """
        result = []
        for item in self.data:
            # --- Опыт работы ---
            experience = item.get("experience", "")
            experience_text = ""

            if isinstance(experience, str):
                try:
                    # Попробуем распарсить JSON, если это возможно
                    parsed_exp = json.loads(experience)
                    if isinstance(parsed_exp, list):
                        experience = parsed_exp
                    else:
                        experience = []
                except json.JSONDecodeError:
                    experience = []

            if isinstance(experience, list):
                for exp in experience:
                    if isinstance(exp, dict):
                        company = exp.get("company", "").strip()
                        position = exp.get("position", "").strip()
                        description = exp.get("description", "").strip()

                        if company or position or description:
                            experience_text += f"Компания: {company}\n"
                            experience_text += f"Должность: {position}\n"
                            experience_text += f"Описание: {description}\n\n"

            # --- ФИО ---
            full_name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()

            # --- Город ---
            area = item.get("area", None)
            city = "—"
            if isinstance(area, dict):
                city = area.get("name", "—").strip()
            elif isinstance(area, str):
                try:
                    area_dict = json.loads(area)
                    if isinstance(area_dict, dict):
                        city = area_dict.get("name", "—").strip()
                except json.JSONDecodeError:
                    pass

            # --- Зарплата ---
            salary_data = item.get("salary", None)
            salary = "—"
            if isinstance(salary_data, dict):
                amount = salary_data.get("amount")
                currency = salary_data.get("currency")
                if amount is not None and currency:
                    salary = f"{amount} {currency}"
            elif isinstance(salary_data, str) and salary_data.strip():
                try:
                    salary_dict = json.loads(salary_data)
                    if isinstance(salary_dict, dict):
                        amount = salary_dict.get("amount")
                        currency = salary_dict.get("currency")
                        if amount is not None and currency:
                            salary = f"{amount} {currency}"
                except json.JSONDecodeError:
                    pass

            # --- Возраст ---
            age = str(item.get("age", "")).strip() or "—"

            # --- Должность ---
            title = str(item.get("title", "")).strip() or "—"

            # --- Ссылка на резюме ---
            link = (item.get("alternate_url") or item.get("link") or "").strip()

            # --- Соответствие (%) ---
            match_percent = str(item.get("match_percent", "")).strip() or "—"

            # --- Формируем запись ---
            simplified = {
                "ID": str(item.get("id", "")).strip() or "—",
                "ФИО": full_name or "—",
                "Возраст": age,
                "Город": city,
                "Должность": title,
                "Зарплата": salary,
                "Опыт": experience_text.strip(),
                "Соответствие (%)": match_percent,
                "Ссылка": link,
            }

            result.append(simplified)
        return result

    def save(self, path: str) -> None:
        """
        Сохраняет данные в файл. Должен быть реализован в дочернем классе.

        Args:
            path (str): Путь к файлу.
        """
        raise NotImplementedError("Метод должен быть реализован в дочернем классе")


class CSVExporter(Exporter):
    """
    Экспортирует резюме в формат CSV.
    """

    def save(self, path: str) -> None:
        """
        Сохраняет данные в CSV-файл.

        Args:
            path (str): Путь к файлу.
        """
        data = self.prepare_data()
        if not data:
            logger.warning("Нет данных для экспорта в CSV")
            print("Нет данных для экспорта")
            return

        fieldnames = data[0].keys() if data else []

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, mode="w", encoding="utf-8", newline="", errors="replace") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"CSV-файл успешно сохранён: {file_path}")
            print(f"Файл успешно сохранён: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении CSV: {e}")
            print(f"Ошибка при сохранении CSV: {e}")
            raise


class XLSXExporter(Exporter):
    """
    Экспортирует резюме в формат Excel (XLSX).
    """

    def save(self, path: str) -> None:
        """
        Сохраняет данные в XLSX-файл.

        Args:
            path (str): Путь к файлу.
        """
        data = self.prepare_data()
        if not data:
            logger.warning("Нет данных для экспорта в Excel")
            print("Нет данных для экспорта")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Резюме"

        # Заголовки
        headers = list(data[0].keys())
        ws.append(headers)
        ws.row_dimensions[1].font = Font(bold=True)
        for col in ws.columns:
            for cell in col:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Данные
        for row in data:
            ws.append([str(value) if not isinstance(value, list) else ", ".join(value) for value in row.values()])

        # Автоподбор ширины колонок
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = min(adjusted_width, 50)

        # Сохранение
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            wb.save(file_path)
            logger.info(f"XLSX-файл успешно сохранён: {file_path}")
            print(f"Файл успешно сохранён: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении XLSX: {e}")
            print(f"Ошибка при сохранении XLSX: {e}")
            raise