#!/usr/bin/env python3
"""
Тест для проверки нового функционала поиска с предварительным просмотром.
"""

import requests
import json
import time

def test_search_preview_flow():
    """Тестирует новый flow поиска: поиск -> предварительный просмотр -> список резюме"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Тестирование нового flow поиска...")
    
    # Шаг 1: Выполняем поиск
    print("\n1️⃣ Выполняем поиск...")
    search_params = {
        "keywords[]": ["python developer"],
        "source": "hh",
        "region": ["2019"],  # Москва
        "total": "5",
        "per_page": "5"
    }
    
    try:
        response = requests.get(f"{base_url}/search", params=search_params, allow_redirects=False)
        print(f"   Статус ответа: {response.status_code}")
        
        if response.status_code == 302:  # Redirect
            redirect_url = response.headers.get('Location')
            print(f"   Перенаправление на: {redirect_url}")
            
            # Извлекаем task_id из URL
            if "/search_preview/" in redirect_url:
                task_id = redirect_url.split("/search_preview/")[1].split("?")[0]
                print(f"   Task ID: {task_id}")
                
                # Шаг 2: Проверяем страницу предварительного просмотра
                print("\n2️⃣ Проверяем страницу предварительного просмотра...")
                preview_response = requests.get(f"{base_url}/search_preview/{task_id}")
                print(f"   Статус предварительного просмотра: {preview_response.status_code}")
                
                if preview_response.status_code == 200:
                    print("   ✅ Страница предварительного просмотра загружена успешно")
                    
                    # Проверяем, что на странице есть информация о количестве найденных резюме
                    if "Найдено резюме" in preview_response.text:
                        print("   ✅ Информация о количестве резюме отображается")
                    else:
                        print("   ❌ Информация о количестве резюме не найдена")
                    
                    # Проверяем наличие кнопок
                    if "Просмотреть резюме" in preview_response.text:
                        print("   ✅ Кнопка 'Просмотреть резюме' найдена")
                    else:
                        print("   ❌ Кнопка 'Просмотреть резюме' не найдена")
                        
                    if "Изменить поиск" in preview_response.text:
                        print("   ✅ Кнопка 'Изменить поиск' найдена")
                    else:
                        print("   ❌ Кнопка 'Изменить поиск' не найдена")
                        
                    if "Новый поиск" in preview_response.text:
                        print("   ✅ Кнопка 'Новый поиск' найдена")
                    else:
                        print("   ❌ Кнопка 'Новый поиск' не найдена")
                    
                    # Шаг 3: Проверяем переход к списку резюме
                    print("\n3️⃣ Проверяем переход к списку резюме...")
                    resumes_response = requests.get(f"{base_url}/resumes/{task_id}")
                    print(f"   Статус списка резюме: {resumes_response.status_code}")
                    
                    if resumes_response.status_code == 200:
                        print("   ✅ Страница списка резюме загружена успешно")
                    else:
                        print("   ❌ Ошибка загрузки списка резюме")
                        
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

def test_search_with_no_results():
    """Тестирует поиск без результатов"""
    
    base_url = "http://localhost:5000"
    
    print("\n🧪 Тестирование поиска без результатов...")
    
    # Поиск с очень специфичными критериями, которые вряд ли найдут резюме
    search_params = {
        "keywords[]": ["very_specific_keyword_that_should_not_exist_12345"],
        "source": "hh",
        "region": ["2019"],
        "total": "5",
        "per_page": "5"
    }
    
    try:
        response = requests.get(f"{base_url}/search", params=search_params, allow_redirects=False)
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            task_id = redirect_url.split("/search_preview/")[1].split("?")[0]
            
            preview_response = requests.get(f"{base_url}/search_preview/{task_id}")
            
            if preview_response.status_code == 200:
                if "Резюме не найдены" in preview_response.text:
                    print("   ✅ Сообщение 'Резюме не найдены' отображается корректно")
                else:
                    print("   ❌ Сообщение о том, что резюме не найдены, не отображается")
                    
                if "Просмотреть резюме" not in preview_response.text:
                    print("   ✅ Кнопка 'Просмотреть резюме' скрыта для пустых результатов")
                else:
                    print("   ❌ Кнопка 'Просмотреть резюме' отображается для пустых результатов")
                    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестов нового функционала поиска")
    print("=" * 50)
    
    test_search_preview_flow()
    test_search_with_no_results()
    
    print("\n" + "=" * 50)
    print("🏁 Тестирование завершено") 