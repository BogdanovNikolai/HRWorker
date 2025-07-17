#!/usr/bin/env python3
"""
Скрипт для получения новых токенов HeadHunter API.
Используйте после получения authorization code.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def get_new_tokens():
    """Получает новые токены по authorization code."""
    print("🔄 Получение новых токенов HeadHunter API")
    print("=" * 50)
    
    # Получаем данные из .env
    client_id = os.getenv('CLIENT_ID1')
    client_secret = os.getenv('CLIENT_SECRET1')
    redirect_uri = os.getenv('REDIRECT_URI1')
    
    if not all([client_id, client_secret, redirect_uri]):
        print("❌ Ошибка: Не все необходимые переменные найдены в .env")
        print("Убедитесь, что CLIENT_ID1, CLIENT_SECRET1 и REDIRECT_URI1 настроены")
        return
    
    # Генерируем URL для авторизации
    from api.hh.main import get_authorization_url
    auth_url = get_authorization_url(client_id, redirect_uri, "new_tokens")
    
    print("📋 Инструкция:")
    print("1. Перейдите по ссылке ниже и авторизуйтесь:")
    print(f"   {auth_url}")
    print("\n2. После авторизации вы будете перенаправлены на URL вида:")
    print(f"   {redirect_uri}?code=AUTHORIZATION_CODE&state=new_tokens")
    print("\n3. Скопируйте AUTHORIZATION_CODE из URL")
    print("\n4. Введите его ниже:")
    
    # Запрашиваем authorization code
    auth_code = input("\nВведите authorization code: ").strip()
    
    if not auth_code:
        print("❌ Authorization code не введен")
        return
    
    # Получаем токены
    try:
        from api.hh.main import get_tokens_from_code
        
        print("\n🔄 Получаем токены...")
        token_data = get_tokens_from_code(
            client_id,
            client_secret,
            auth_code,
            redirect_uri
        )
        
        print("✅ Токены успешно получены!")
        print(f"✅ Access Token: {token_data['access_token'][:20]}...")
        print(f"✅ Refresh Token: {token_data['refresh_token'][:20]}...")
        print(f"✅ Expires In: {token_data['expires_in']} секунд")
        
        # Сохраняем в .env
        print("\n💾 Обновляем .env файл...")
        update_env_file(token_data)
        
        print("\n✅ Токены сохранены в .env файл!")
        print("Теперь запустите: python test_tokens.py")
        
    except Exception as e:
        print(f"❌ Ошибка при получении токенов: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ сервера: {e.response.text}")

def update_env_file(token_data):
    """Обновляет .env файл новыми токенами."""
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print(f"❌ Файл {env_file} не найден")
        return
    
    # Читаем текущий .env файл
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Обновляем токены
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('ACCESS_TOKEN1='):
            lines[i] = f"ACCESS_TOKEN1={token_data['access_token']}\n"
            updated = True
        elif line.startswith('REFRESH_TOKEN1='):
            lines[i] = f"REFRESH_TOKEN1={token_data['refresh_token']}\n"
            updated = True
    
    # Если токены не найдены, добавляем их
    if not updated:
        lines.append(f"ACCESS_TOKEN1={token_data['access_token']}\n")
        lines.append(f"REFRESH_TOKEN1={token_data['refresh_token']}\n")
    
    # Записываем обновленный файл
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    """Основная функция."""
    get_new_tokens()

if __name__ == "__main__":
    main() 