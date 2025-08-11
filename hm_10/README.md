# Homework 10: ML Model Inference REST API

## Описание

REST API для инференса модели машинного обучения, реализованный на FastAPI. Сервис принимает текстовые данные и возвращает предсказание модели (анализ текста с подсчетом относительного количества гласных букв).

## Функциональность

- **GET `/`** - Главная страница API
- **GET `/analysis/{data}`** - Анализ текста (требует аутентификации с ролью admin)
  - Подсчитывает относительное количество английских гласных букв в строке
  - Возвращает результат в формате JSON: `{"result": <float>}`

## Аутентификация

API использует OAuth2 с JWT токенами для аутентификации. В системе есть фейковая база данных пользователей с разными ролями.

## Технологический стек

- Python 3.12+
- FastAPI - веб-фреймворк
- Uvicorn - ASGI сервер
- Pydantic - валидация данных
- PyJWT - работа с JWT токенами
- Passlib - хеширование паролей

## Установка

### Предварительные требования

- Python 3.12 или выше
- uv (установка: `pip install uv`)

### Клонирование репозитория

```bash
git clone <repository-url>
cd hm_10
```

### Установка зависимостей

```bash
uv venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## Запуск

### Локальный запуск

```bash
uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload
```

Сервис будет доступен по адресу: http://localhost:8000

### Документация API

После запуска сервиса документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Разработка

### Запуск линтера

```bash
uv run pylint app/
```

### Структура проекта

```
hm_10/
├── app/
│   ├── __init__.py
│   └── app.py          # Основной код приложения
├── requirements.txt    # Зависимости проекта
├── .python-version     # Версия Python для uv
└── README.md          # Документация
```

## CI/CD

Проект использует GitHub Actions для автоматической проверки кода при каждом push и pull request:
- Проверка кода с помощью pylint
- Тестирование на Python 3.12
- Автоматическая установка зависимостей через uv

## Примеры использования

### Получение главной страницы

```bash
curl http://localhost:8000/
```

### Анализ текста (требует токен аутентификации)

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/analysis/hello%20world
```

Ответ:
```json
{
  "result": 0.27272727272727271
}
```

## Лицензия

MIT