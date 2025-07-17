# Управление токенами HeadHunter API

Этот документ описывает функции для получения и управления токенами доступа к HeadHunter API.

## Обзор

Для работы с HeadHunter API необходимо получить и управлять токенами доступа. Процесс включает:

1. **Получение authorization code** - пользователь авторизуется и получает временный код
2. **Обмен кода на токены** - получение access_token и refresh_token
3. **Обновление токенов** - использование refresh_token для получения нового access_token
4. **Валидация токенов** - проверка актуальности токенов

## Функции

### 1. Генерация URL авторизации

```python
from api.hh.main import get_authorization_url

# Генерируем URL для авторизации пользователя
auth_url = get_authorization_url(
    client_id="your_client_id",
    redirect_uri="https://your-app.com/callback",
    state="random_state_string"  # опционально
)
print(f"Перейдите по ссылке для авторизации: {auth_url}")
```

### 2. Получение токенов по authorization code

```python
from api.hh.main import get_tokens_from_code

# После авторизации пользователь получает authorization_code
token_data = get_tokens_from_code(
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_code="received_auth_code",
    redirect_uri="https://your-app.com/callback"
)

print(f"Access Token: {token_data['access_token']}")
print(f"Refresh Token: {token_data['refresh_token']}")
print(f"Expires In: {token_data['expires_in']} секунд")
```

### 3. Обновление токенов

```python
from api.hh.main import get_tokens_from_refresh_token

# Обновляем access_token используя refresh_token
token_data = get_tokens_from_refresh_token(
    client_id="your_client_id",
    client_secret="your_client_secret",
    refresh_token="your_refresh_token"
)

print(f"New Access Token: {token_data['access_token']}")
# refresh_token может остаться тем же или измениться
```

### 4. Валидация токена

```python
from api.hh.main import validate_token, get_token_info

# Проверяем валидность токена
is_valid = validate_token("your_access_token")
print(f"Токен валиден: {is_valid}")

# Получаем информацию о токене и пользователе
if is_valid:
    token_info = get_token_info("your_access_token")
    print(f"Пользователь: {token_info['first_name']} {token_info['last_name']}")
    print(f"Email: {token_info['email']}")
```

## Использование с HHApiClient

Класс `HHApiClient` предоставляет удобные методы для работы с токенами:

```python
from api.hh.main import HHApiClient

# Создаем клиент
client = HHApiClient()

# Проверяем валидность текущего токена
if not client.validate_current_token():
    print("Токен невалиден, обновляем...")
    client.refresh_access_token()

# Получаем информацию о текущем пользователе
user_info = client.get_current_token_info()
print(f"Текущий пользователь: {user_info['first_name']} {user_info['last_name']}")

# Генерируем URL для получения новых токенов
auth_url = client.get_authorization_url(state="example_state")
print(f"URL для авторизации: {auth_url}")
```

## Полный процесс получения токенов

### Шаг 1: Настройка приложения

1. Создайте приложение на [dev.hh.ru](https://dev.hh.ru/)
2. Получите `CLIENT_ID` и `CLIENT_SECRET`
3. Настройте `REDIRECT_URI`

### Шаг 2: Получение authorization code

```python
from api.hh.main import get_authorization_url

auth_url = get_authorization_url(
    client_id="your_client_id",
    redirect_uri="https://your-app.com/callback"
)
print(f"Перейдите по ссылке: {auth_url}")
```

Пользователь переходит по ссылке, авторизуется и получает `authorization_code` в URL callback'а.

### Шаг 3: Обмен кода на токены

```python
from api.hh.main import get_tokens_from_code

token_data = get_tokens_from_code(
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_code="received_code",
    redirect_uri="https://your-app.com/callback"
)

# Сохраняем токены
access_token = token_data['access_token']
refresh_token = token_data['refresh_token']
```

### Шаг 4: Использование токенов

```python
from api.hh.main import HHApiClient

# Создаем клиент с полученными токенами
client = HHApiClient()
client.access_token = access_token
client.refresh_token = refresh_token

# Используем API
resumes = client.get_all_resumes("Python разработчик")
```

## Обработка ошибок

Все функции могут вызывать исключения:

- `requests.RequestException` - при ошибках HTTP запросов
- `KeyError` - при отсутствии ожидаемых полей в ответе
- `ValueError` - при отсутствии необходимых параметров

```python
try:
    token_data = get_tokens_from_code(client_id, client_secret, code, redirect_uri)
except requests.RequestException as e:
    print(f"Ошибка сети: {e}")
except KeyError as e:
    print(f"Неверный формат ответа: {e}")
except ValueError as e:
    print(f"Неверные параметры: {e}")
```

## Автоматическое обновление токенов

Класс `HHApiClient` автоматически обновляет токены при их истечении:

```python
client = HHApiClient()

# Декоратор @refresh_token_if_needed автоматически проверяет
# и обновляет токен перед выполнением метода
resumes = client.get_all_resumes("Python")  # Токен обновится автоматически
```

## Примеры использования

См. файл `api/hh/example_token_usage.py` для полных примеров использования всех функций.

## Безопасность

- Никогда не храните токены в коде
- Используйте переменные окружения (.env файл)
- Регулярно обновляйте токены
- Проверяйте валидность токенов перед использованием
- Используйте HTTPS для всех запросов 