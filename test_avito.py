#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from data_manager.main import DataManager
from redis_manager import redis_manager
import json

def test_avito_vacancies():
    print("=== Тест вакансий Avito ===")
    
    # Создаем DataManager
    dm = DataManager()
    
    # Обновляем кэш
    print("Обновляем кэш вакансий...")
    dm.update_vacancies_cache_avito()
    
    # Проверяем данные в кэше
    cache_key = "cached_company_vacancies_avito"
    cached_data = redis_manager.client.get(cache_key)
    
    if cached_data:
        vacancies = json.loads(cached_data)
        print(f"Найдено {len(vacancies)} вакансий в кэше")
        
        # Показываем первые 3 вакансии с откликами
        for i, vacancy in enumerate(vacancies[:3]):
            print(f"{i+1}. {vacancy['title']}")
            print(f"   ID: {vacancy['id']}")
            print(f"   Город: {vacancy['city']}")
            print(f"   Всего откликов: {vacancy['responses_total']}")
            print(f"   Новых откликов: {vacancy['responses_unread']}")
            print()
            
            # Тестируем получение откликов для конкретной вакансии
            if vacancy['responses_total'] > 0:
                print(f"   Тестируем отклики для вакансии {vacancy['id']}...")
                negotiations = dm.get_negotiations_by_vacancy_avito(vacancy['id'])
                print(f"   Получено откликов: {negotiations.get('found', 0)}")
                
                # Показываем детали первого отклика
                if negotiations.get('items'):
                    first_response = negotiations['items'][0]
                    print(f"   Первый отклик: {first_response.get('applicant', {}).get('data', {}).get('name', 'Неизвестно')}")
                    print(f"   Просмотрен: {first_response.get('is_viewed', False)}")
                    print(f"   Vacancy ID: {first_response.get('vacancy_id')}")
                print()
    else:
        print("Нет данных в кэше")

def test_avito_responses():
    print("=== Анализ структуры откликов Avito ===")
    from api.avito.main import AvitoAPIClient
    from datetime import datetime, timedelta
    client = AvitoAPIClient()
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    apps = client.get_application_ids(updated_at_from=month_ago)
    app_ids = [app['id'] for app in apps.get('applies', [])]
    print(f"Всего найдено {len(app_ids)} откликов за месяц")
    if not app_ids:
        print("Нет откликов для анализа")
        return
    details = client.get_applications_by_ids(app_ids[:5])
    for i, app in enumerate(details.get('applies', [])):
        print(f"Отклик {i+1}:")
        for k, v in app.items():
            print(f"  {k}: {v}")
        print()

if __name__ == "__main__":
    test_avito_vacancies()
    test_avito_responses() 