#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager.main import DataManager
from api.avito.main import AvitoAPIClient
from datetime import datetime, timedelta
import json

def debug_avito_vacancies():
    print("=== ДЕТАЛЬНАЯ ОТЛАДКА AVITO ВАКАНСИЙ ===")
    
    dm = DataManager()
    client = AvitoAPIClient()
    
    # 1. Получаем сырые вакансии
    print("\n1. Получаем сырые вакансии из API:")
    raw_vacancies = client.get_vacancies()
    print(f"Тип ответа: {type(raw_vacancies)}")
    print(f"Ключи в ответе: {list(raw_vacancies.keys()) if isinstance(raw_vacancies, dict) else 'Нет ключей'}")
    
    if isinstance(raw_vacancies, dict):
        resources = raw_vacancies.get('resources', [])
        print(f"Количество ресурсов: {len(resources)}")
        
        if resources:
            print("Первая вакансия:")
            print(json.dumps(resources[0], indent=2, ensure_ascii=False))
    
    # 2. Получаем отклики за месяц
    print("\n2. Получаем отклики за месяц:")
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    applications_dict = client.get_application_ids(updated_at_from=month_ago)
    print(f"Тип ответа откликов: {type(applications_dict)}")
    print(f"Ключи в ответе откликов: {list(applications_dict.keys()) if isinstance(applications_dict, dict) else 'Нет ключей'}")
    
    applies = applications_dict.get('applies', [])
    print(f"Количество откликов за месяц: {len(applies)}")
    
    if applies:
        print("Первый отклик:")
        print(json.dumps(applies[0], indent=2, ensure_ascii=False))
    
    # 3. Получаем детали откликов
    if applies:
        print("\n3. Получаем детали откликов:")
        app_ids = [app['id'] for app in applies[:5]]  # Берем первые 5
        details = client.get_applications_by_ids(app_ids)
        print(f"Тип ответа деталей: {type(details)}")
        print(f"Ключи в ответе деталей: {list(details.keys()) if isinstance(details, dict) else 'Нет ключей'}")
        
        applies_details = details.get('applies', [])
        print(f"Количество деталей откликов: {len(applies_details)}")
        
        if applies_details:
            print("Детали первого отклика:")
            print(json.dumps(applies_details[0], indent=2, ensure_ascii=False))
            
            # Проверяем наличие vacancy_id
            vacancy_ids = set()
            for app in applies_details:
                vacancy_id = app.get('vacancy_id')
                if vacancy_id:
                    vacancy_ids.add(vacancy_id)
            
            print(f"\nУникальные vacancy_id в откликах: {sorted(list(vacancy_ids))}")
    
    # 4. Проверяем кэш вакансий
    print("\n4. Проверяем кэш вакансий:")
    cached_vacancies = dm.get_company_vacancies_avito()
    print(f"Количество вакансий в кэше: {len(cached_vacancies)}")
    
    if cached_vacancies:
        print("Первая вакансия из кэша:")
        print(json.dumps(cached_vacancies[0], indent=2, ensure_ascii=False))
        
        # Проверяем отклики для каждой вакансии
        for i, vacancy in enumerate(cached_vacancies[:3]):  # Проверяем первые 3
            print(f"\n--- Вакансия {i+1}: {vacancy.get('title', 'Без названия')} ---")
            print(f"ID вакансии: {vacancy.get('id')}")
            print(f"Всего откликов: {vacancy.get('responses_total', 0)}")
            print(f"Новых откликов: {vacancy.get('responses_unread', 0)}")
            
            # Получаем отклики для этой вакансии
            negotiations = dm.get_negotiations_by_vacancy_avito(vacancy.get('id'))
            print(f"Отклики получены: {len(negotiations)}")
            
            if negotiations:
                print("Первый отклик:")
                print(json.dumps(negotiations[0], indent=2, ensure_ascii=False))

def debug_vacancy_responses():
    print("\n=== ОТЛАДКА ОТКЛИКОВ ПО КОНКРЕТНОЙ ВАКАНСИИ ===")
    
    dm = DataManager()
    client = AvitoAPIClient()
    
    # Получаем первую вакансию из кэша
    cached_vacancies = dm.get_company_vacancies_avito()
    if not cached_vacancies:
        print("Нет вакансий в кэше")
        return
    
    vacancy = cached_vacancies[0]
    vacancy_id = vacancy.get('id')
    print(f"Тестируем вакансию: {vacancy.get('title')} (ID: {vacancy_id})")
    
    # Получаем отклики через search_engine
    print("\n1. Отклики через search_engine:")
    negotiations = dm.search_engine.get_negotiations_by_vacancy_avito(vacancy_id)
    print(f"Найдено откликов: {negotiations.get('found', 0)}")
    
    if negotiations.get('items'):
        print("Первый отклик:")
        print(json.dumps(negotiations['items'][0], indent=2, ensure_ascii=False))
    
    # Получаем отклики напрямую через API
    print("\n2. Отклики напрямую через API:")
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    applications_dict = client.get_application_ids(updated_at_from=month_ago)
    applies = applications_dict.get('applies', [])
    
    # Фильтруем по vacancy_id
    filtered_applies = [app for app in applies if app.get('vacancy_id') == vacancy_id]
    print(f"Откликов для вакансии {vacancy_id}: {len(filtered_applies)}")
    
    if filtered_applies:
        print("Первый отклик:")
        print(json.dumps(filtered_applies[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    debug_avito_vacancies()
    debug_vacancy_responses() 