#!/usr/bin/env python3
"""
Тестовый скрипт для проверки множественных текстовых полей в форме поиска.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager.main import DataManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

def test_multiple_text_fields():
    """Тестирует поиск с множественными текстовыми полями."""
    
    print("=== Тест множественных текстовых полей ===")
    
    try:
        dm = DataManager()
        
        # Тест 1: Простой поиск с одним полем (обратная совместимость)
        print("\n1. Простой поиск с одним полем")
        task_id = dm.search_resumes(
            keywords="python разработчик",
            region=["2019"],
            total=3,
            per_page=3,
            text_logic="all",
            text_field="skills"
        )
        print(f"Task ID: {task_id}")
        
        # Тест 2: Поиск с множественными полями (имитация формы)
        print("\n2. Поиск с множественными полями")
        # Имитируем данные из формы с множественными полями
        keywords_list = ["python", "middle разработчик", "django"]
        text_logic_list = ["all", "phrase", "any"]
        text_field_list = ["skills", "title", "experience"]
        
        # Объединяем в один запрос (как делает app.py)
        keywords = " ".join(keywords_list)
        text_logic = text_logic_list[0]  # Используем логику первого поля
        text_field = text_field_list[0]  # Используем поле первого поля
        
        print(f"Объединенные ключевые слова: '{keywords}'")
        print(f"Логика поиска: {text_logic}")
        print(f"Поле поиска: {text_field}")
        
        task_id = dm.search_resumes(
            keywords=keywords,
            region=["2019"],
            total=3,
            per_page=3,
            text_logic=text_logic,
            text_field=text_field
        )
        print(f"Task ID: {task_id}")
        
        # Тест 3: Сложный поиск с фильтрами
        print("\n3. Сложный поиск с фильтрами")
        keywords_list = ["python", "senior", "team lead"]
        keywords = " ".join(keywords_list)
        
        task_id = dm.search_resumes(
            keywords=keywords,
            region=["2019"],
            total=2,
            per_page=2,
            text_logic="all",
            text_field="title",
            salary_from=150000,
            salary_to=500000,
            experience=["between3And6", "moreThan6"],
            employment=["full"],
            order_by="relevance"
        )
        print(f"Task ID: {task_id}")
        
        # Тест 4: Поиск с исключениями
        print("\n4. Поиск с исключениями")
        keywords_list = ["python", "не junior", "не стажер"]
        keywords = " ".join(keywords_list)
        
        task_id = dm.search_resumes(
            keywords=keywords,
            region=["2019"],
            total=2,
            per_page=2,
            text_logic="except",
            text_field="everywhere"
        )
        print(f"Task ID: {task_id}")
        
        print("\n=== Тест множественных полей завершен ===")
        print("Проверьте файл logs/app.log для просмотра логов")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        print(f"Ошибка: {e}")

def test_form_data_processing():
    """Тестирует обработку данных формы."""
    
    print("\n=== Тест обработки данных формы ===")
    
    # Имитируем данные, которые приходят из формы
    form_data = {
        'keywords[]': ['python', 'middle разработчик', 'django'],
        'text_logic[]': ['all', 'phrase', 'any'],
        'text_field[]': ['skills', 'title', 'experience'],
        'region': ['2019'],
        'total': '5',
        'per_page': '5'
    }
    
    print("Данные формы:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    
    # Обработка как в app.py
    keywords_list = form_data.get('keywords[]', [])
    text_logic_list = form_data.get('text_logic[]', [])
    text_field_list = form_data.get('text_field[]', [])
    
    if keywords_list and len(keywords_list) > 1:
        keywords = " ".join(keywords_list)
        text_logic = text_logic_list[0] if text_logic_list else "all"
        text_field = text_field_list[0] if text_field_list else "everywhere"
        
        print(f"\nОбработанные данные:")
        print(f"  Объединенные ключевые слова: '{keywords}'")
        print(f"  Логика поиска: {text_logic}")
        print(f"  Поле поиска: {text_field}")
        
        print(f"\nДетали полей:")
        for i, (kw, logic, field) in enumerate(zip(keywords_list, text_logic_list, text_field_list)):
            print(f"  Поле {i+1}: '{kw}' (логика: {logic}, поле: {field})")
    else:
        keywords = keywords_list[0] if keywords_list else ""
        text_logic = text_logic_list[0] if text_logic_list else None
        text_field = text_field_list[0] if text_field_list else None
        
        print(f"\nОбработанные данные (одно поле):")
        print(f"  Ключевые слова: '{keywords}'")
        print(f"  Логика поиска: {text_logic}")
        print(f"  Поле поиска: {text_field}")

if __name__ == "__main__":
    print("Тестирование множественных текстовых полей")
    print("=" * 60)
    
    test_form_data_processing()
    test_multiple_text_fields()
    
    print("\n" + "=" * 60)
    print("Все тесты завершены!")
    print("Проверьте файл logs/app.log для просмотра подробных логов") 