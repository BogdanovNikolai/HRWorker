"""
Модуль содержит определения ORM-моделей для взаимодействия с базой данных.

В текущей реализации представлена одна модель: Resume.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from database.session import Base
from datetime import datetime


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(100), primary_key=True, index=True)
    source = Column(String, nullable=False, default="hh")
    first_name = Column(String(128))
    middle_name = Column(String(128))
    last_name = Column(String(128))
    title = Column(String(255))
    age = Column(Integer)
    location = Column(String(100))  # город
    salary_json = Column(JSON)     # хранение оригинала 'salary'
    experience = Column(Text)      # опыт как JSON-строка
    total_experience_months = Column(Integer)  # для использования в UI
    link = Column(String(512))     # ссылка на резюме (alternate_url)
    received_at = Column(DateTime, default=datetime.utcnow)
    
# class AvitoResume(Base):
#     __tablename__ = "avitoresumes"
    
#     id = Column(String(100), primary_key=True, index=True)
#     first_name = Column(String(128))  # net L
#     middle_name = Column(String(128)) # net = platno
#     last_name = Column(String(128))   # net Г
#     title = Column(String(255))
#     age = Column(Integer) # params.age
#     location = Column(String(100))  # params.addresss
#     salary = Column(Integer)     # salary bez rublei v originale
#     experience = Column(Text)      # params.experience (years amount), experience_list: [{company, position, responsibilities, work_finish (iso), work_start (iso)}]
#     total_experience_months = Column(Integer)  # для использования в UI
#     link = Column(String(512))     # url
#     received_at = Column(DateTime, default=datetime.utcnow)