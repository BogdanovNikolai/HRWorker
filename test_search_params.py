#!/usr/bin/env python3
"""
Тест для проверки передачи параметров поиска обратно в форму поиска.
"""

import requests
import json
from urllib.parse import urlencode, parse_qs

def test_search_parameters_preservation():
    """Тестирует сохранение и передачу параметров поиска"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Тестирование сохранения параметров поиска...")
    
    # Тестовые параметры поиска
    search_params = {
        "keywords[]": ["python developer", "middle"],
        "source": "hh",
        "region": ["2019", "1"],  # Москва и Россия
        "total": "10",
        "per_page": "5",
        "salary_from": "100000",
        "salary_to": "200000",
        "currency": "RUR",
        "experience": ["between1And3", "between3And6"],
        "education_levels": ["higher", "bachelor"],
        "employment": ["full"],
        "schedule": ["fullDay", "remote"],
        "age_from": "25",
        "age_to": "35",
        "gender": "male",
        "job_search_status": ["active_search"],
        "period": "30",
        "relocation": "living_or_relocation",
        "order_by": "relevance",
        "label": ["only_with_salary", "only_with_photo"],
        "text_logic[]": ["all", "any"],
        "text_field[]": ["everywhere", "title"],
        "description": "Тестовое описание вакансии"
    }
    
    try:
        # Шаг 1: Выполняем поиск
        print("\n1️⃣ Выполняем поиск с параметрами...")
        response = requests.get(f"{base_url}/search", params=search_params, allow_redirects=False)
        print(f"   Статус ответа: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            print(f"   Перенаправление на: {redirect_url}")
            
            if "/search_preview/" in redirect_url:
                task_id = redirect_url.split("/search_preview/")[1].split("?")[0]
                print(f"   Task ID: {task_id}")
                
                # Шаг 2: Проверяем страницу предварительного просмотра
                print("\n2️⃣ Проверяем страницу предварительного просмотра...")
                preview_response = requests.get(f"{base_url}/search_preview/{task_id}")
                
                if preview_response.status_code == 200:
                    print("   ✅ Страница предварительного просмотра загружена")
                    
                    # Ищем кнопку "Изменить поиск" и извлекаем URL
                    if "Изменить поиск" in preview_response.text:
                        print("   ✅ Кнопка 'Изменить поиск' найдена")
                        
                        # Извлекаем URL кнопки "Изменить поиск"
                        import re
                        modify_search_pattern = r'href="([^"]*search[^"]*\?[^"]*)"'
                        match = re.search(modify_search_pattern, preview_response.text)
                        
                        if match:
                            modify_search_url = match.group(1)
                            print(f"   URL кнопки 'Изменить поиск': {modify_search_url}")
                            
                            # Шаг 3: Проверяем переход к форме поиска с параметрами
                            print("\n3️⃣ Проверяем переход к форме поиска с параметрами...")
                            
                            # Извлекаем параметры из URL
                            if "?" in modify_search_url:
                                query_string = modify_search_url.split("?", 1)[1]
                                parsed_params = parse_qs(query_string)
                                
                                print("   Параметры в URL кнопки 'Изменить поиск':")
                                for key, values in parsed_params.items():
                                    print(f"     {key}: {values}")
                                
                                # Проверяем ключевые параметры
                                expected_params = {
                                    "keywords[]": ["python developer", "middle"],
                                    "source": ["hh"],
                                    "region": ["2019", "1"],
                                    "total": ["10"],
                                    "per_page": ["5"],
                                    "salary_from": ["100000"],
                                    "salary_to": ["200000"],
                                    "currency": ["RUR"],
                                    "experience": ["between1And3", "between3And6"],
                                    "education_levels": ["higher", "bachelor"],
                                    "employment": ["full"],
                                    "schedule": ["fullDay", "remote"],
                                    "age_from": ["25"],
                                    "age_to": ["35"],
                                    "gender": ["male"],
                                    "job_search_status": ["active_search"],
                                    "period": ["30"],
                                    "relocation": ["living_or_relocation"],
                                    "order_by": ["relevance"],
                                    "label": ["only_with_salary", "only_with_photo"],
                                    "text_logic[]": ["all", "any"],
                                    "text_field[]": ["everywhere", "title"],
                                    "description": ["Тестовое описание вакансии"]
                                }
                                
                                # Проверяем соответствие параметров
                                missing_params = []
                                for key, expected_values in expected_params.items():
                                    if key not in parsed_params:
                                        missing_params.append(f"Отсутствует: {key}")
                                    elif parsed_params[key] != expected_values:
                                        missing_params.append(f"Не совпадает {key}: ожидалось {expected_values}, получено {parsed_params[key]}")
                                
                                if missing_params:
                                    print("   ❌ Проблемы с параметрами:")
                                    for issue in missing_params:
                                        print(f"     {issue}")
                                else:
                                    print("   ✅ Все параметры корректно переданы")
                                
                                # Шаг 4: Проверяем загрузку формы поиска с параметрами
                                print("\n4️⃣ Проверяем загрузку формы поиска с параметрами...")
                                form_response = requests.get(f"{base_url}/search", params=parsed_params)
                                
                                if form_response.status_code == 200:
                                    print("   ✅ Форма поиска загружена с параметрами")
                                    
                                    # Проверяем, что параметры отображаются в форме
                                    form_text = form_response.text
                                    
                                    # Проверяем ключевые слова
                                    if "python developer" in form_text and "middle" in form_text:
                                        print("   ✅ Ключевые слова отображаются в форме")
                                    else:
                                        print("   ❌ Ключевые слова не отображаются в форме")
                                    
                                    # Проверяем зарплату
                                    if "100000" in form_text and "200000" in form_text:
                                        print("   ✅ Параметры зарплаты отображаются в форме")
                                    else:
                                        print("   ❌ Параметры зарплаты не отображаются в форме")
                                        
                                else:
                                    print(f"   ❌ Ошибка загрузки формы: {form_response.status_code}")
                                    
                        else:
                            print("   ❌ Не удалось найти URL кнопки 'Изменить поиск'")
                    else:
                        print("   ❌ Кнопка 'Изменить поиск' не найдена")
                        
                else:
                    print(f"   ❌ Ошибка загрузки предварительного просмотра: {preview_response.status_code}")
                    
            else:
                print("   ❌ Неожиданный URL перенаправления")
                
        else:
            print(f"   ❌ Неожиданный статус ответа: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Не удалось подключиться к серверу. Убедитесь, что приложение запущено.")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def test_simple_search_parameters():
    """Тестирует простые параметры поиска"""
    
    base_url = "http://localhost:5000"
    
    print("\n🧪 Тестирование простых параметров поиска...")
    
    # Простые параметры
    simple_params = {
        "keywords[]": ["python"],
        "source": "hh",
        "region": ["2019"],
        "total": "5"
    }
    
    try:
        response = requests.get(f"{base_url}/search", params=simple_params, allow_redirects=False)
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            task_id = redirect_url.split("/search_preview/")[1].split("?")[0]
            
            preview_response = requests.get(f"{base_url}/search_preview/{task_id}")
            
            if preview_response.status_code == 200:
                # Извлекаем URL кнопки "Изменить поиск"
                import re
                modify_search_pattern = r'href="([^"]*search[^"]*\?[^"]*)"'
                match = re.search(modify_search_pattern, preview_response.text)
                
                if match:
                    modify_search_url = match.group(1)
                    query_string = modify_search_url.split("?", 1)[1]
                    parsed_params = parse_qs(query_string)
                    
                    print("   Простые параметры в URL:")
                    for key, values in parsed_params.items():
                        print(f"     {key}: {values}")
                    
                    # Проверяем основные параметры
                    if "keywords[]" in parsed_params and "region" in parsed_params:
                        print("   ✅ Основные параметры переданы корректно")
                    else:
                        print("   ❌ Основные параметры не переданы")
                        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестов передачи параметров поиска")
    print("=" * 60)
    
    test_search_parameters_preservation()
    test_simple_search_parameters()
    
    print("\n" + "=" * 60)
    print("🏁 Тестирование завершено") 