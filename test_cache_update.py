#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager.main import DataManager

def test_cache_update():
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕНИЯ КЭША AVITO ===")
    
    dm = DataManager()
    
    # Проверяем кэш до обновления
    print("\n1. Кэш до обновления:")
    cached_vacancies = dm.get_company_vacancies_avito()
    print(f"Вакансий в кэше: {len(cached_vacancies)}")
    
    # Обновляем кэш
    print("\n2. Обновляем кэш...")
    dm.update_vacancies_cache_avito()
    
    # Проверяем кэш после обновления
    print("\n3. Кэш после обновления:")
    cached_vacancies = dm.get_company_vacancies_avito()
    print(f"Вакансий в кэше: {len(cached_vacancies)}")
    
    if cached_vacancies:
        print("\nПервые 3 вакансии:")
        for i, vacancy in enumerate(cached_vacancies[:3]):
            print(f"{i+1}. {vacancy.get('title', 'Без названия')}")
            print(f"   ID: {vacancy.get('id')}")
            print(f"   Город: {vacancy.get('city', 'Не указан')}")
            print(f"   Всего откликов: {vacancy.get('responses_total', 0)}")
            print(f"   Новых откликов: {vacancy.get('responses_unread', 0)}")
            print()

if __name__ == "__main__":
    test_cache_update() 