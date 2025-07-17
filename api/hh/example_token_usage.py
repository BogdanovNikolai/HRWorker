"""
Примеры использования функций для получения и управления токенами HeadHunter API.

Этот файл демонстрирует:
1. Как получить URL для авторизации
2. Как обменять authorization code на токены
3. Как обновлять токены
4. Как проверять валидность токенов
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from api.hh.main import (
    get_authorization_url,
    get_tokens_from_code,
    get_tokens_from_refresh_token,
    validate_token,
    get_token_info,
    HHApiClient
)
from config.main import Config as conf

def example_get_authorization_url():
    """
    Пример получения URL для авторизации пользователя.
    """
    print("=== Пример получения URL авторизации ===")
    
    # Используем данные из конфигурации
    client_id = conf.CLIENT_ID1
    redirect_uri = conf.REDIRECT_URI1
    
    if not client_id or not redirect_uri:
        print("Ошибка: CLIENT_ID1 или REDIRECT_URI1 не настроены в .env файле")
        return
    
    # Генерируем URL для авторизации
    auth_url = get_authorization_url(client_id, redirect_uri, state="random_state_string")
    print(f"URL для авторизации: {auth_url}")
    print("Пользователь должен перейти по этому URL и авторизоваться")
    print("После авторизации он получит authorization code")

def example_exchange_code_for_tokens():
    """
    Пример обмена authorization code на токены.
    """
    print("\n=== Пример обмена кода на токены ===")
    
    # Эти данные нужно получить после авторизации пользователя
    client_id = conf.CLIENT_ID1
    client_secret = conf.CLIENT_SECRET1
    redirect_uri = conf.REDIRECT_URI1
    
    if not all([client_id, client_secret, redirect_uri]):
        print("Ошибка: Не все необходимые данные настроены в .env файле")
        return
    
    # authorization_code получается после успешной авторизации пользователя
    # В реальном приложении это значение приходит от HeadHunter
    authorization_code = "P4U8TJDUJEI0I9R0FA8LPEOBNQ6A28LLEPB9N7JNSR0B7E2N74ITMNVGM73FHCR7"  # Замените на реальный код
    
    try:
        token_data = get_tokens_from_code(
            client_id,
            client_secret,
            authorization_code,
            redirect_uri
        )
        
        print("Токены успешно получены:")
        print(f"Access Token: {token_data['access_token'][:20]}...")
        print(f"Refresh Token: {token_data['refresh_token'][:20]}...")
        print(f"Expires In: {token_data['expires_in']} секунд")
        print(f"Token Type: {token_data.get('token_type', 'Bearer')}")
        
        # Сохраняем токены в .env файл
        print("\n💾 Сохраняем токены в .env файл...")
        if save_tokens_to_env(token_data):
            print("✅ Токены успешно сохранены!")
            print("Теперь запустите тест: python test_tokens.py")
        else:
            print("❌ Не удалось сохранить токены")
        
    except Exception as e:
        print(f"Ошибка при получении токенов: {e}")

def save_tokens_to_env(token_data):
    """
    Сохраняет токены в .env файл.
    """
    import os
    
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    
    if not os.path.exists(env_file):
        print(f"❌ Файл .env не найден: {env_file}")
        return False
    
    try:
        # Читаем текущий .env файл
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Обновляем токены
        updated_access = False
        updated_refresh = False
        
        for i, line in enumerate(lines):
            if line.startswith('ACCESS_TOKEN1='):
                lines[i] = f"ACCESS_TOKEN1={token_data['access_token']}\n"
                updated_access = True
            elif line.startswith('REFRESH_TOKEN1='):
                lines[i] = f"REFRESH_TOKEN1={token_data['refresh_token']}\n"
                updated_refresh = True
        
        # Если токены не найдены, добавляем их
        if not updated_access:
            lines.append(f"ACCESS_TOKEN1={token_data['access_token']}\n")
        if not updated_refresh:
            lines.append(f"REFRESH_TOKEN1={token_data['refresh_token']}\n")
        
        # Записываем обновленный файл
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("✅ Токены сохранены в .env файл!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении токенов: {e}")
        return False

def example_refresh_tokens():
    """
    Пример обновления токенов.
    """
    print("\n=== Пример обновления токенов ===")
    
    client_id = conf.CLIENT_ID1
    client_secret = conf.CLIENT_SECRET1
    refresh_token = conf.REFRESH_TOKEN1
    
    if not all([client_id, client_secret, refresh_token]):
        print("Ошибка: Не все необходимые данные настроены в .env файле")
        return
    
    try:
        token_data = get_tokens_from_refresh_token(
            client_id,
            client_secret,
            refresh_token
        )
        
        print("Токены успешно обновлены:")
        print(f"New Access Token: {token_data['access_token']}...")
        if 'refresh_token' in token_data:
            print(f"New Refresh Token: {token_data['refresh_token']}...")
        print(f"Expires In: {token_data['expires_in']} секунд")
        
        # Сохраняем токены в .env файл
        print("\n💾 Сохраняем токены в .env файл...")
        if save_tokens_to_env(token_data):
            print("✅ Токены успешно сохранены!")
            print("Теперь запустите тест: python test_tokens.py")
        else:
            print("❌ Не удалось сохранить токены")
        
    except Exception as e:
        print(f"Ошибка при обновлении токенов: {e}")

def example_validate_token():
    """
    Пример проверки валидности токена.
    """
    print("\n=== Пример проверки валидности токена ===")
    
    access_token = conf.ACCESS_TOKEN1
    
    if not access_token:
        print("Ошибка: ACCESS_TOKEN1 не настроен в .env файле")
        return
    
    is_valid = validate_token(access_token)
    print(f"Токен валиден: {is_valid}")
    
    if is_valid:
        token_info = get_token_info(access_token)
        if token_info:
            print("Информация о токене:")
            print(f"Пользователь: {token_info.get('first_name', '')} {token_info.get('last_name', '')}")
            print(f"Email: {token_info.get('email', '')}")
            print(f"ID: {token_info.get('id', '')}")

def example_using_hh_client():
    """
    Пример использования HHApiClient для работы с токенами.
    """
    print("\n=== Пример использования HHApiClient ===")
    
    # Создаем экземпляр клиента
    client = HHApiClient()
    
    # Проверяем валидность текущего токена
    is_valid = client.validate_current_token()
    print(f"Текущий токен валиден: {is_valid}")
    
    if not is_valid:
        print("Токен невалиден, пытаемся обновить...")
        try:
            client.refresh_access_token()
            print("Токен успешно обновлен")
        except Exception as e:
            print(f"Ошибка при обновлении токена: {e}")
            return
    
    # Получаем информацию о текущем пользователе
    user_info = client.get_current_token_info()
    if user_info:
        print("Информация о текущем пользователе:")
        print(f"Имя: {user_info.get('first_name', '')} {user_info.get('last_name', '')}")
        print(f"Email: {user_info.get('email', '')}")
    
    # Генерируем URL для авторизации (если нужно получить новые токены)
    try:
        auth_url = client.get_authorization_url(state="example_state")
        print(f"\nURL для получения новых токенов: {auth_url}")
    except Exception as e:
        print(f"Ошибка при генерации URL авторизации: {e}")

def main():
    """
    Основная функция для демонстрации всех примеров.
    """
    print("Демонстрация функций для работы с токенами HeadHunter API")
    print("=" * 60)
    
    # Запускаем все примеры
    example_get_authorization_url()
    example_exchange_code_for_tokens()
    example_refresh_tokens()
    example_validate_token()
    example_using_hh_client()
    
    print("\n" + "=" * 60)
    print("Демонстрация завершена")

if __name__ == "__main__":
    main() 