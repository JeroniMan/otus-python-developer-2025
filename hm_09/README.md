# Домашнее задание №9 - REST API для ML модели

REST API для инференса модели машинного обучения, реализованный на FastAPI.

## 📋 Описание

API принимает текстовую строку и возвращает результат анализа - относительное количество гласных букв в тексте. Это учебный проект, демонстрирующий базовую структуру ML-сервиса.

## 🚀 Быстрый старт

### Установка с UV (рекомендуется)

```bash
# Установка uv (если еще не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh
# или
pip install uv

# Синхронизация зависимостей
uv sync

# Запуск сервера
uv run uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload
```

### Установка с Poetry

```bash
# Установка зависимостей
poetry install --no-root

# Запуск сервера
poetry run uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload
```

### Docker

```bash
# Сборка образа
docker build -t hm9-api .

# Запуск контейнера
docker run -p 8000:8000 hm9-api
```

## 📝 API Endpoints

### `GET /`
Главная страница API

**Response:**
```json
{
  "text": "ML model inference"
}
```

### `GET /analysis/{data}`
Анализ текста - подсчет относительного количества гласных букв

**Parameters:**
- `data` (string, path) - текст для анализа

**Response:**
```json
{
  "result": 0.42
}
```

**Пример запроса:**
```bash
curl http://localhost:8000/analysis/hello%20world
```

## 📚 Swagger документация

После запуска сервера документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Тестирование

```bash
# С UV
uv run pytest

# С Poetry
poetry run pytest

# Без виртуального окружения
pytest
```

## 🛠️ Структура проекта

```
hm_9/
├── app/
│   ├── __init__.py
│   └── app.py          # Основное приложение
├── tests/
│   ├── __init__.py
│   └── test_app.py     # Тесты
├── .github/
│   └── workflows/
│       └── ci.yml      # CI/CD
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml      # Poetry конфигурация
├── requirements.txt    # Зависимости для pip
└── README.md
```

## 🔧 Конфигурация

Приложение использует следующие настройки по умолчанию:
- Host: `127.0.0.1`
- Port: `8000`

Для изменения используйте параметры uvicorn:
```bash
uvicorn app.app:app --host 0.0.0.0 --port 8080
```

## 📊 Примеры использования

### Python
```python
import requests

response = requests.get("http://localhost:8000/analysis/Hello World")
print(response.json())  # {"result": 0.27272727272727271}
```

### JavaScript
```javascript
fetch('http://localhost:8000/analysis/Hello World')
  .then(response => response.json())
  .then(data => console.log(data));
```

### curl
```bash
curl -X GET "http://localhost:8000/analysis/test%20string"
```

## 🚀 Развертывание

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

### AWS Lambda
Используйте Mangum для адаптации FastAPI:
```python
from mangum import Mangum
handler = Mangum(app)
```

## 👤 Автор

Vladislav Kozlov <vlad.kv.2002@gmail.com>