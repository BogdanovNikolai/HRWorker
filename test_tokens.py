#!/usr/bin/env python3
"""
Простой тест для проверки токенов HeadHunter API.
Запускайте из корневой папки проекта.
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_env_variables():
    """Проверяем наличие необходимых переменных окружения."""
    print("=== Проверка переменных окружения ===")
    
    required_vars = [
        'CLIENT_ID1',
        'CLIENT_SECRET1', 
        'ACCESS_TOKEN1',
        'REFRESH_TOKEN1',
        'REDIRECT_URI1'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}..." if len(value) > 10 else f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: НЕ НАЙДЕН")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Отсутствуют переменные: {', '.join(missing_vars)}")
        print("Добавьте их в файл .env")
        return False
    
    print("\n✅ Все необходимые переменные найдены!")
    return True

def test_token_functions():
    """Тестируем функции работы с токенами."""
    print("\n=== Тестирование функций токенов ===")
    
    try:
        from api.hh.main import (
            get_authorization_url,
            get_tokens_from_refresh_token,
            validate_token,
            get_token_info,
            HHApiClient
        )
        
        # Тест 1: Генерация URL авторизации
        print("1. Тестируем генерацию URL авторизации...")
        client_id = os.getenv('CLIENT_ID1')
        redirect_uri = os.getenv('REDIRECT_URI1')
        
        if client_id and redirect_uri:
            auth_url = get_authorization_url(client_id, redirect_uri, "test_state")
            print(f"✅ URL авторизации: {auth_url}")
        else:
            print("❌ Не удалось сгенерировать URL авторизации")
        
        # Тест 2: Проверка валидности токена
        print("\n2. Тестируем валидность токена...")
        access_token = os.getenv('ACCESS_TOKEN1')
        
        if access_token:
            is_valid = validate_token(access_token)
            print(f"✅ Токен валиден: {is_valid}")
            
            if is_valid:
                token_info = get_token_info(access_token)
                if token_info:
                    print(f"✅ Пользователь: {token_info.get('first_name', '')} {token_info.get('last_name', '')}")
                    print(f"✅ Email: {token_info.get('email', '')}")
        else:
            print("❌ ACCESS_TOKEN1 не найден")
        
        # Тест 3: Обновление токена
        print("\n3. Тестируем обновление токена...")
        client_secret = os.getenv('CLIENT_SECRET1')
        refresh_token = os.getenv('REFRESH_TOKEN1')
        
        if all([client_id, client_secret, refresh_token]):
            try:
                token_data = get_tokens_from_refresh_token(client_id, client_secret, refresh_token)
                print("✅ Токены успешно обновлены!")
                print(f"✅ Новый access_token: {token_data['access_token'][:20]}...")
                print(f"✅ Expires in: {token_data['expires_in']} секунд")
                
                # Сохраняем новые токены
                print("\n💾 Сохраните новые токены в .env файл:")
                print(f"ACCESS_TOKEN1={token_data['access_token']}")
                if 'refresh_token' in token_data:
                    print(f"REFRESH_TOKEN1={token_data['refresh_token']}")
                    
            except Exception as e:
                print(f"❌ Ошибка при обновлении токена: {e}")
        else:
            print("❌ Не все данные для обновления токена найдены")
        
        # Тест 4: HHApiClient
        print("\n4. Тестируем HHApiClient...")
        try:
            client = HHApiClient()
            is_valid = client.validate_current_token()
            print(f"✅ HHApiClient токен валиден: {is_valid}")
            
            if is_valid:
                user_info = client.get_current_token_info()
                if user_info:
                    print(f"✅ Пользователь клиента: {user_info.get('first_name', '')} {user_info.get('last_name', '')}")
        except Exception as e:
            print(f"❌ Ошибка при тестировании HHApiClient: {e}")
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Убедитесь, что вы запускаете скрипт из корневой папки проекта")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

def main():
    """Основная функция."""
    print("🧪 Тестирование токенов HeadHunter API")
    print("=" * 50)
    
    # Проверяем переменные окружения
    if not test_env_variables():
        print("\n❌ Тест не пройден: отсутствуют необходимые переменные")
        return
    
    # Тестируем функции
    test_token_functions()
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    main() 