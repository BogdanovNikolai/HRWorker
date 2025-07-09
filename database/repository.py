"""
Модуль содержит функции для работы с данными в базе данных.

Предоставляет CRUD-операции над моделью Resume.
"""

import json
from typing import Optional, List
from database.models import Resume
from sqlalchemy.orm import Session
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ResumeRepository:
    """
    Репозиторий для работы с резюме в базе данных.

    Methods:
        get_by_link(db, link): Возвращает резюме по ссылке.
        create_resume(db, resume_data): Добавляет новое резюме в БД.
        get_all_resumes(db, skip, limit): Возвращает список резюме с пагинацией.
        delete_resume(db, resume_id): Удаляет резюме по ID.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_source_and_resume_id(self, source: str, resume_id: str) -> Optional[Resume]:
        """
        Возвращает резюме по source и resume_id.
        """
        return self.db.query(Resume).filter(
            Resume.source == source,
            Resume.id == resume_id
        ).first()

    def get_by_link(self, link: str) -> Optional[Resume]:
        """
        Ищет резюме по полной ссылке.

        Args:
            link (str): Полная ссылка на резюме.

        Returns:
            Resume | None: Найденное резюме или None.
        """
        return self.db.query(Resume).filter(Resume.link == link).first()

    def resume_exists(self, resume_id: str, source: str = "hh") -> bool:
        return self.db.query(Resume.id).filter(Resume.id == resume_id).filter(Resume.source == source).first() is not None

    def create_resume(self, resume_data: dict, source: str = "hh") -> Resume:
        if source == "avito":
            resume_data_params = resume_data.get("params")
            experience = json.dumps(resume_data_params.get("experience_list"))
            exp = resume_data_params.get("experience")
            months = int(exp) if exp else None
            link = resume_data.get("url")
        else: # hh
            experience = json.dumps(resume_data.get("experience"))
            exp = resume_data.get("total_experience")
            months = exp.get("months") if isinstance(exp, dict) else None
            link = resume_data.get("alternate_url")
            
        exp_dump = experience
        total_months = months
        resume_link = link

        db_resume = Resume(
            id=resume_data.get("id"),
            source=source,
            first_name=resume_data.get("first_name"),
            middle_name=resume_data.get("middle_name"),
            last_name=resume_data.get("last_name"),
            title=resume_data.get("title"),
            age=resume_data.get("age"),
            location=resume_data.get("area", {}).get("name"),
            salary_json=json.dumps(resume_data.get("salary")) if resume_data.get("salary") else None,
            experience=exp_dump,
            total_experience_months=total_months,
            link=resume_link,
        )
        self.db.add(db_resume)
        self.db.commit()
        self.db.refresh(db_resume)
        return db_resume

    @classmethod
    def get_all_resumes(self, skip: int = 0, limit: int = 100) -> List[Resume]:
        """
        Возвращает список резюме с пагинацией.

        Args:
            skip (int): Количество записей для пропуска.
            limit (int): Максимальное количество возвращаемых записей.

        Returns:
            list[Resume]: Список резюме.
        """
        return self.db.query(Resume).offset(skip).limit(limit).all()

    @staticmethod
    def delete_resume(db: Session, resume_id: int) -> None:
        """
        Удаляет резюме по ID.

        Args:
            db (Session): Сессия SQLAlchemy.
            resume_id (int): ID резюме.
        """
        db.query(Resume).filter(Resume.id == resume_id).delete()
        db.commit()