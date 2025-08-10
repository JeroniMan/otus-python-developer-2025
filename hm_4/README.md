# 📚 HM_4 — Scoring API

HTTP API сервис для скоринга пользователей с декларативной системой валидации запросов.

## 📋 Описание

Это учебный проект, демонстрирующий применение ООП для создания декларативной системы валидации. API принимает POST-запросы и предоставляет два метода:
- `online_score` - расчет скоринга пользователя
- `clients_interests` - получение интересов клиентов

## 🏗️ Архитектура

### Основные компоненты:

1. **Система полей (Field System)**
   - Базовый класс `Field` - дескриптор для валидации
   - Специализированные поля: `CharField`, `EmailField`, `PhoneField`, `DateField`, etc.
   - Каждое поле знает как себя валидировать

2. **Метакласс RequestMeta**
   - Автоматически собирает все Field-дескрипторы при создании класса
   - Сохраняет их в атрибут `_fields` для последующей валидации

3. **Классы запросов**
   - `MethodRequest` - верхнеуровневый запрос с авторизацией
   - `OnlineScoreRequest` - запрос скоринга
   - `ClientsInterestsRequest` - запрос интересов

4. **Обработчики методов**
   - `online_score_handler` - обработка запроса скоринга
   - `clients_interests_handler` - обработка запроса интересов

## 🚀 Запуск

### Установка зависимостей:
```bash
cd hm_4
uv sync --all-extras
```

### Запуск сервера:
```bash
# Запуск на порту 8080 (по умолчанию)
uv run python api.py

# Запуск с указанием порта и лог-файла
uv run python api.py -p 8080 -l api.log
```

### Запуск тестов:
```bash
uv run python test.py

# или через pytest
uv run pytest test.py -v
```

## 📝 Примеры запросов

### Online Score
```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "account": "horns&hoofs",
  "login": "h&f",
  "method": "online_score",
  "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
  "arguments": {
    "phone": "79175002040",
    "email": "test@example.ru",
    "first_name": "Иван",
    "last_name": "Иванов",
    "birthday": "01.01.1990",
    "gender": 1
  }
}' http://127.0.0.1:8080/method/
```

Ответ:
```json
{"code": 200, "response": {"score": 5.0}}
```

### Clients Interests
```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "account": "horns&hoofs",
  "login": "h&f",
  "method": "clients_interests",
  "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
  "arguments": {
    "client_ids": [1, 2, 3, 4],
    "date": "20.07.2017"
  }
}' http://127.0.0.1:8080/method/
```

Ответ:
```json
{
  "code": 200,
  "response": {
    "1": ["books", "hi-tech"],
    "2": ["pets", "tv"],
    "3": ["travel", "music"],
    "4": ["cinema", "geek"]
  }
}
```

## 🔐 Авторизация

Токен генерируется по формуле:
- Для обычных пользователей: `SHA512(account + login + SALT)`
- Для админа: `SHA512(текущий_час + ADMIN_SALT)`

Пример генерации токена:
```python
import hashlib

# Для обычного пользователя
account = "horns&hoofs"
login = "h&f"
SALT = "Otus"
token = hashlib.sha512((account + login + SALT).encode('utf-8')).hexdigest()

# Для админа
import datetime
ADMIN_SALT = "42"
admin_token = hashlib.sha512(
    (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')
).hexdigest()
```

## 📊 Валидация

### Поля запроса:
- **required** - поле обязательно должно присутствовать
- **nullable** - поле может быть пустой строкой

### Специфичные правила:
- **phone** - 11 цифр, начинается с 7
- **email** - должен содержать @
- **birthday** - формат DD.MM.YYYY, не старше 70 лет
- **gender** - 0, 1 или 2

### Правила для online_score:
Должна быть хотя бы одна непустая пара:
- phone + email
- first_name + last_name
- gender + birthday

## 🧪 Тестирование

Тесты покрывают:
- Невалидные запросы (отсутствующие поля, неправильные типы)
- Неправильную авторизацию
- Корректные запросы для обоих методов
- Особый случай: админ всегда получает score = 42

## 📁 Структура проекта

```
hm_4/
├── api.py          # Основной файл с API и валидацией
├── scoring.py      # Функции расчета скора и интересов
├── test.py         # Unit-тесты
├── pyproject.toml  # Конфигурация проекта
└── README.md       # Документация
```

## ⚙️ Как это работает

1. **HTTP запрос** приходит на `/method`
2. **Парсинг JSON** из тела запроса
3. **Создание MethodRequest** и валидация верхнеуровневых полей
4. **Проверка авторизации** через токен
5. **Роутинг** к нужному обработчику по полю `method`
6. **Создание специфичного Request** (OnlineScore или ClientsInterests)
7. **Валидация аргументов** через Field-дескрипторы
8. **Бизнес-логика** (расчет скора или получение интересов)
9. **Формирование ответа** в JSON

## 🎯 Особенности реализации

- **Метакласс** автоматически собирает поля при создании класса
- **Дескрипторы** инкапсулируют логику валидации
- **DRY принцип** - валидация описывается один раз в Field
- **Расширяемость** - легко добавить новые типы полей или методы API

## 📝 Примечания

Это учебный проект для демонстрации ООП паттернов. В production следует использовать:
- Фреймворки (FastAPI, Django REST)
- Библиотеки валидации (Pydantic, Marshmallow)
- Нормальную БД вместо заглушек в scoring.py
- JWT токены вместо простых хешей