from .models import Resume
from .repository import ResumeRepository
from .session import engine, Base, get_db

def init_db():
    """
    Создаёт все таблицы в БД, если их ещё нет.
    """
    Base.metadata.create_all(bind=engine)