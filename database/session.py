"""
Модуль для управления сессиями SQLAlchemy.

Содержит engine, базовый класс для моделей и фабрику сессий.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import conf

# Прямой путь к БД (временно, для теста)
db_url = "postgresql://HRWorker_user:12345678@localhost:5432/HRWorker_database"

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Получает сессию БД для использования в приложении (например, через Depends в Flask).

    Yields:
        Session: Объект сессии SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()