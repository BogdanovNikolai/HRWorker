#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логирования запросов к HeadHunter API.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager.main import DataManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

def test_search_logging():
    """Тестирует логирование при поиске резюме."""
    
    print("=== Тест логирования поиска резюме ===")
    
    try:
        dm = DataManager()
        
        # Тест 1: Простой поиск
        print("\n1. Простой поиск")
        task_id = dm.search_resumes(
            keywords="python разработчик",
            region=["2019"],  # Москва
            total=5,
            per_page=5
        )
        print(f"Task ID: {task_id}")
        
        # Тест 2: Поиск с фильтрами
        print("\n2. Поиск с фильтрами")
        task_id = dm.search_resumes(
            keywords="python разработчик",
            region=["2019"],
            total=3,
            per_page=3,
            salary_from=100000,
            salary_to=300000,
            experience=["between1And3", "between3And6"],
            employment=["full"],
            order_by="relevance"
        )
        print(f"Task ID: {task_id}")
        
        # Тест 3: Поиск с текстовыми параметрами
        print("\n3. Поиск с текстовыми параметрами")
        task_id = dm.search_resumes(
            keywords="python разработчик",
            region=["2019"],
            total=2,
            per_page=2,
            text_logic="all",
            text_field="skills",
            age_from=25,
            age_to=35,
            gender="male"
        )
        print(f"Task ID: {task_id}")
        
        print("\n=== Тест логирования завершен ===")
        print("Проверьте файл logs/app.log для просмотра логов")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        print(f"Ошибка: {e}")

def test_resume_details_logging():
    """Тестирует логирование при получении деталей резюме."""
    
    print("\n=== Тест логирования деталей резюме ===")
    
    try:
        dm = DataManager()
        
        # Получаем список резюме для тестирования
        task_id = dm.search_resumes(
            keywords="python",
            region=["2019"],
            total=2,
            per_page=2
        )
        
        # Получаем резюме из задачи
        resumes = dm.get_task_resumes(task_id, offset=0, limit=1)
        
        if resumes.get("items"):
            resume_id = resumes["items"][0].get("id")
            if resume_id:
                print(f"Тестируем получение деталей резюме: {resume_id}")
                
                # Получаем детали резюме (это вызовет логирование)
                full_resume = dm.hh_client.get_resume_details(str(resume_id))
                
                if full_resume:
                    print(f"Детали получены: {full_resume.get('title', 'Без названия')}")
                else:
                    print("Детали не получены")
            else:
                print("ID резюме не найден")
        else:
            print("Резюме не найдены")
            
        print("\n=== Тест деталей резюме завершен ===")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании деталей резюме: {e}")
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    print("Тестирование логирования запросов к HeadHunter API")
    print("=" * 60)
    
    test_search_logging()
    test_resume_details_logging()
    
    print("\n" + "=" * 60)
    print("Все тесты завершены!")
    print("Проверьте файл logs/app.log для просмотра подробных логов") 