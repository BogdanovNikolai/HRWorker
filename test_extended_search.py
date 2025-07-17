#!/usr/bin/env python3
"""
Тестовый скрипт для проверки расширенной функциональности поиска резюме.
"""

import requests
import json
from urllib.parse import urlencode

def test_extended_search():
    """Тестирует расширенный поиск с различными параметрами."""
    
    base_url = "http://localhost:5000"
    
    # Тест 1: Базовый поиск
    print("=== Тест 1: Базовый поиск ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],  # Москва
        'total': '10',
        'per_page': '10'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Базовый поиск работает")
    else:
        print("✗ Базовый поиск не работает")
        print(f"Ответ: {response.text}")
    
    # Тест 2: Поиск с фильтрами зарплаты
    print("\n=== Тест 2: Поиск с фильтрами зарплаты ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],
        'salary_from': '100000',
        'salary_to': '300000',
        'currency': 'RUR',
        'total': '5'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Поиск с фильтрами зарплаты работает")
    else:
        print("✗ Поиск с фильтрами зарплаты не работает")
    
    # Тест 3: Поиск с фильтрами опыта
    print("\n=== Тест 3: Поиск с фильтрами опыта ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],
        'experience': ['between1And3', 'between3And6'],
        'employment': ['full'],
        'schedule': ['fullDay'],
        'total': '5'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Поиск с фильтрами опыта работает")
    else:
        print("✗ Поиск с фильтрами опыта не работает")
    
    # Тест 4: Поиск с текстовыми параметрами
    print("\n=== Тест 4: Поиск с текстовыми параметрами ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],
        'text_logic': 'all',
        'text_field': 'skills',
        'order_by': 'relevance',
        'total': '5'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Поиск с текстовыми параметрами работает")
    else:
        print("✗ Поиск с текстовыми параметрами не работает")
    
    # Тест 5: Поиск с дополнительными фильтрами
    print("\n=== Тест 5: Поиск с дополнительными фильтрами ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],
        'age_from': '25',
        'age_to': '35',
        'gender': 'male',
        'job_search_status': ['active_search'],
        'period': '30',
        'total': '5'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Поиск с дополнительными фильтрами работает")
    else:
        print("✗ Поиск с дополнительными фильтрами не работает")
    
    # Тест 6: Поиск с метками
    print("\n=== Тест 6: Поиск с метками ===")
    params = {
        'keywords': 'python разработчик',
        'region': ['2019'],
        'label': ['only_with_photo', 'only_with_salary'],
        'total': '5'
    }
    
    response = requests.get(f"{base_url}/search", params=params)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✓ Поиск с метками работает")
    else:
        print("✗ Поиск с метками не работает")

def test_form_rendering():
    """Тестирует отображение формы поиска."""
    
    base_url = "http://localhost:5000"
    
    print("\n=== Тест отображения формы ===")
    response = requests.get(f"{base_url}/search")
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        # Проверяем наличие новых полей в форме
        checks = [
            ('text_logic', 'Логика поиска'),
            ('text_field', 'Поле поиска'),
            ('salary_from', 'Зарплата от'),
            ('salary_to', 'Зарплата до'),
            ('currency', 'Валюта'),
            ('experience', 'Опыт работы'),
            ('employment', 'Тип занятости'),
            ('schedule', 'График работы'),
            ('age_from', 'Возраст от'),
            ('age_to', 'Возраст до'),
            ('gender', 'Пол'),
            ('job_search_status', 'Статус поиска работы'),
            ('period', 'Период публикации'),
            ('order_by', 'Сортировка'),
            ('label', 'Только с фотографией'),
        ]
        
        for field, description in checks:
            if field in content or description in content:
                print(f"✓ Поле '{field}' найдено")
            else:
                print(f"✗ Поле '{field}' не найдено")
    else:
        print("✗ Форма не загружается")

if __name__ == "__main__":
    print("Тестирование расширенной функциональности поиска резюме")
    print("=" * 60)
    
    try:
        test_form_rendering()
        test_extended_search()
        print("\n" + "=" * 60)
        print("Тестирование завершено!")
    except requests.exceptions.ConnectionError:
        print("✗ Не удалось подключиться к серверу. Убедитесь, что приложение запущено на http://localhost:5000")
    except Exception as e:
        print(f"✗ Ошибка при тестировании: {e}") 