#!/usr/bin/env python3
"""
Скрипт для сохранения новых токенов в .env файл.
Используйте после успешного обновления токенов.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def save_new_tokens():
    """Сохраняет новые токены в .env файл."""
    print("💾 Сохранение новых токенов в .env файл")
    print("=" * 50)
    
    # Новые токены из вывода
    new_access_token = "USERT9SGQN7TTIIPA3V1..."  # Замените на полный токен
    new_refresh_token = "USERL1B5CU7KJ1BKLH25..."  # Замените на полный токен
    
    print("Введите новые токены:")
    print("(Скопируйте их из вывода предыдущего теста)")
    
    new_access_token = input("Введите новый ACCESS_TOKEN: ").strip()
    new_refresh_token = input("Введите новый REFRESH_TOKEN: ").strip()
    
    if not new_access_token or not new_refresh_token:
        print("❌ Токены не введены")
        return
    
    # Обновляем .env файл
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print(f"❌ Файл {env_file} не найден")
        return
    
    # Читаем текущий .env файл
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Обновляем токены
    updated_access = False
    updated_refresh = False
    
    for i, line in enumerate(lines):
        if line.startswith('ACCESS_TOKEN1='):
            lines[i] = f"ACCESS_TOKEN1={new_access_token}\n"
            updated_access = True
        elif line.startswith('REFRESH_TOKEN1='):
            lines[i] = f"REFRESH_TOKEN1={new_refresh_token}\n"
            updated_refresh = True
    
    # Если токены не найдены, добавляем их
    if not updated_access:
        lines.append(f"ACCESS_TOKEN1={new_access_token}\n")
    if not updated_refresh:
        lines.append(f"REFRESH_TOKEN1={new_refresh_token}\n")
    
    # Записываем обновленный файл
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ Токены сохранены в .env файл!")
    print("\nТеперь протестируйте токены:")
    print("python test_tokens.py")

def main():
    """Основная функция."""
    save_new_tokens()

if __name__ == "__main__":
    main() 