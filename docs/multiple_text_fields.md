# Множественные текстовые поля в форме поиска

## Обзор

Добавлена возможность создания сложных поисковых запросов с использованием множественных текстовых полей. Пользователи могут добавлять несколько полей поиска с разными параметрами логики и области поиска.

## Возможности

### 🎯 **Множественные поля поиска**
- Добавление неограниченного количества текстовых полей
- Индивидуальная настройка логики поиска для каждого поля
- Выбор области поиска для каждого поля
- Динамическое добавление/удаление полей

### 🔧 **Логика поиска**
- **all** - Все слова встречаются
- **any** - Любое из слов встречается  
- **phrase** - Точная фраза встречается
- **except** - Не встречаются

### 📍 **Области поиска**
- **everywhere** - Везде
- **title** - В названии резюме
- **education** - В образовании
- **skills** - В ключевых навыках
- **experience** - В опыте работы
- **experience_company** - В компаниях и отраслях
- **experience_position** - В должностях
- **experience_description** - В обязанностях

## Использование

### 1. Базовое использование

По умолчанию форма содержит одно текстовое поле:

```
┌─────────────────────────────────────────────────────────────┐
│ Текстовые поля поиска *                                     │
├─────────────────────────────────────────────────────────────┤
│ [python разработчик] [Логика: Все слова] [Поле: Везде]     │
│                                                             │
│ [+] Добавить поле                                           │
└─────────────────────────────────────────────────────────────┘
```

### 2. Добавление дополнительных полей

Нажмите кнопку **"Добавить поле"** для создания нового поля:

```
┌─────────────────────────────────────────────────────────────┐
│ Текстовые поля поиска *                                     │
├─────────────────────────────────────────────────────────────┤
│ [python] [Логика: Все слова] [Поле: Навыки]                │
│ [middle разработчик] [Логика: Фраза] [Поле: Название] [✕]  │
│ [django] [Логика: Любое] [Поле: Опыт] [✕]                  │
│                                                             │
│ [+] Добавить поле                                           │
└─────────────────────────────────────────────────────────────┘
```

### 3. Примеры сложных запросов

#### Поиск Python разработчиков с опытом Django
```
Поле 1: "python" (Логика: all, Поле: skills)
Поле 2: "middle разработчик" (Логика: phrase, Поле: title)
Поле 3: "django" (Логика: any, Поле: experience)
```

#### Поиск Senior разработчиков без Junior
```
Поле 1: "python" (Логика: all, Поле: everywhere)
Поле 2: "senior" (Логика: all, Поле: title)
Поле 3: "junior" (Логика: except, Поле: everywhere)
```

#### Поиск Team Lead с опытом управления
```
Поле 1: "team lead" (Логика: phrase, Поле: title)
Поле 2: "управление командой" (Логика: any, Поле: experience)
Поле 3: "agile" (Логика: any, Поле: skills)
```

## Техническая реализация

### Frontend (JavaScript)

```javascript
// Добавление нового поля
function addTextField() {
    const fieldGroup = document.createElement('div');
    fieldGroup.className = 'text-field-group mb-3';
    
    fieldGroup.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <input type="text" class="form-control" name="keywords[]" 
                       placeholder="python middle разработчик" required>
            </div>
            <div class="col-md-3">
                <select name="text_logic[]" class="form-control">
                    <option value="all">Все слова встречаются</option>
                    <option value="any">Любое из слов встречается</option>
                    <option value="phrase">Точная фраза встречается</option>
                    <option value="except">Не встречаются</option>
                </select>
            </div>
            <div class="col-md-3">
                <select name="text_field[]" class="form-control">
                    <option value="everywhere">Везде</option>
                    <option value="title">В названии резюме</option>
                    <!-- ... другие опции ... -->
                </select>
            </div>
            <div class="col-md-2">
                <button type="button" class="btn btn-outline-danger btn-sm remove-text-field">
                    <i class="fas fa-minus"></i> Удалить
                </button>
            </div>
        </div>
    `;
    
    container.appendChild(fieldGroup);
}
```

### Backend (Python)

```python
# Обработка множественных полей в app.py
keywords_list = request.args.getlist("keywords[]")
text_logic_list = request.args.getlist("text_logic[]")
text_field_list = request.args.getlist("text_field[]")

if keywords_list and len(keywords_list) > 1:
    # Объединяем все ключевые слова в один запрос
    keywords = " ".join(keywords_list)
    text_logic = text_logic_list[0] if text_logic_list else "all"
    text_field = text_field_list[0] if text_field_list else "everywhere"
    
    # Логируем информацию о множественных полях
    logger.info(f"Множественные текстовые поля: {len(keywords_list)} полей")
    for i, (kw, logic, field) in enumerate(zip(keywords_list, text_logic_list, text_field_list)):
        logger.info(f"  Поле {i+1}: '{kw}' (логика: {logic}, поле: {field})")
else:
    # Обратная совместимость с одним полем
    keywords = keywords_list[0] if keywords_list else ""
    text_logic = text_logic_list[0] if text_logic_list else None
    text_field = text_field_list[0] if text_field_list else None
```

## Логирование

Система логирует подробную информацию о множественных полях:

```
2025-07-17 10:53:58,385 - app - INFO - Множественные текстовые поля: 3 полей
2025-07-17 10:53:58,386 - app - INFO -   Поле 1: 'python' (логика: all, поле: skills)
2025-07-17 10:53:58,387 - app - INFO -   Поле 2: 'middle разработчик' (логика: phrase, поле: title)
2025-07-17 10:53:58,388 - app - INFO -   Поле 3: 'django' (логика: any, поле: experience)
```

## Ограничения

### Текущие ограничения
- Все поля объединяются в один запрос к HH API
- Используется логика и поле поиска первого поля
- Максимум 2000 резюме в результате
- Максимум 100 резюме на страницу

### Планы развития
- Поддержка сложной логики между полями (AND/OR)
- Индивидуальные запросы для каждого поля
- Расширенные операторы поиска
- Сохранение сложных запросов как шаблонов

## Примеры использования

### Сценарий 1: Поиск Full-stack разработчика

```
Поле 1: "full stack" (Логика: phrase, Поле: title)
Поле 2: "javascript" (Логика: any, Поле: skills)
Поле 3: "python" (Логика: any, Поле: skills)
Поле 4: "react" (Логика: any, Поле: skills)
```

### Сценарий 2: Поиск DevOps инженера

```
Поле 1: "devops" (Логика: all, Поле: title)
Поле 2: "docker" (Логика: any, Поле: skills)
Поле 3: "kubernetes" (Логика: any, Поле: skills)
Поле 4: "ci/cd" (Логика: any, Поле: experience)
```

### Сценарий 3: Поиск с исключениями

```
Поле 1: "python" (Логика: all, Поле: everywhere)
Поле 2: "junior" (Логика: except, Поле: title)
Поле 3: "стажер" (Логика: except, Поле: title)
Поле 4: "senior" (Логика: any, Поле: title)
```

## Тестирование

Для тестирования множественных полей создан скрипт `test_multiple_text_fields.py`:

```bash
# Активировать виртуальное окружение
.venv\Scripts\activate

# Запустить тест
python test_multiple_text_fields.py
```

Скрипт тестирует:
- Обработку данных формы
- Простой поиск с одним полем
- Поиск с множественными полями
- Сложный поиск с фильтрами
- Поиск с исключениями

## Совместимость

### ✅ Обратная совместимость
- Старые формы с одним полем продолжают работать
- Параметры `keywords`, `text_logic`, `text_field` поддерживаются
- Все существующие фильтры работают без изменений

### 🔄 Миграция
- Автоматическое определение множественных полей
- Плавный переход от старого формата к новому
- Сохранение всех существующих функций

## Устранение неполадок

### Проблема: Поля не добавляются
**Решение:** Проверьте JavaScript консоль на ошибки, убедитесь что Font Awesome подключен для иконок.

### Проблема: Форма не отправляется
**Решение:** Убедитесь что все обязательные поля заполнены, проверьте валидацию на стороне сервера.

### Проблема: Неожиданные результаты поиска
**Решение:** Проверьте логи в `logs/app.log`, убедитесь что параметры передаются корректно.

## Дополнительные ресурсы

- [Документация по логированию](logging.md)
- [Расширенный поиск](extended_search.md)
- [API HeadHunter](https://github.com/hhru/api/blob/master/docs/resumes.md)
- [Тестовые скрипты](../test_multiple_text_fields.py) 