# 📊 HM_5 — Scoring API Tests & Store

HTTP API сервис для скоринга пользователей с полным покрытием тестами и интеграцией с key-value хранилищем.

## 📋 Описание

Это расширение проекта HM_4, добавляющее:
- ✅ Полное покрытие unit-тестами всех компонентов
- 🗄️ Интеграцию с Redis как key-value хранилищем
- 🔄 Retry-логику для отказоустойчивости
- 🧪 Интеграционные тесты с реальным хранилищем
- 📊 Параметризованные тесты через декораторы

## 🏗️ Архитектура

### Компоненты системы:

1. **Store Layer (`store.py`)**
   - `Store` - реализация с Redis и retry-логикой
   - `MockStore` - мок для тестирования
   - Разделение на cache и persistent storage

2. **API Layer (`api.py`)**
   - Field-дескрипторы для валидации
   - Request-классы с метаклассом
   - Обработчики методов API

3. **Business Logic (`scoring.py`)**
   - `get_score` - расчет скора с кешированием
   - `get_interests` - получение интересов из хранилища

4. **Tests**
   - `test.py` - unit и функциональные тесты
   - `test_integration.py` - интеграционные тесты с Redis

## 🚀 Быстрый старт

### Установка зависимостей:
```bash
cd hm_5
uv sync --all-extras
```

### Запуск Redis (для интеграционных тестов):
```bash
# В Docker
make run-redis

# Или локально
redis-server
```

### Запуск тестов:
```bash
# Все unit-тесты
make test

# Только unit-тесты
make test-unit

# Интеграционные тесты (требуется Redis)
make test-integration

# С покрытием
make test-coverage
```

### Запуск сервера:
```bash
# Запуск API сервера
make run

# С логированием
make run-log
```

## 🧪 Тестирование

### Unit-тесты

#### Тесты полей (`TestFields`):
- Валидация всех типов полей
- Проверка required/nullable логики
- Специфичные правила валидации

#### Тесты запросов (`TestRequests`):
- Валидация OnlineScoreRequest
- Валидация ClientsInterestsRequest
- Проверка обязательных пар полей

#### Тесты хранилища (`TestStore`):
- Mock операции кеша
- Mock операции персистентного хранилища
- Проверка retry-логики
- Обработка ошибок соединения

#### Тесты скоринга (`TestScoring`):
- Расчет скора
- Кеширование результатов
- Работа при недоступном кеше
- Получение интересов

#### Функциональные тесты API (`TestAPI`):
- Проверка авторизации
- Валидация запросов
- Корректные ответы методов
- Обработка ошибок

### Параметризованные тесты

Используется декоратор `@parameterized.expand` для запуска одного теста с разными данными:

```python
@parameterized.expand([
    ({"phone": "79175002040", "email": "test@mail.ru"},),
    ({"first_name": "John", "last_name": "Doe"},),
    ({"gender": 1, "birthday": "01.01.2000"},),
])
def test_ok_score_request(self, arguments):
    # Тест выполнится 3 раза с разными аргументами
    ...
```

При падении теста видно, какой именно кейс упал:
```
test_ok_score_request_1 ({"phone": "79175002040", "email": "test@mail.ru"}) ... ok
test_ok_score_request_2 ({"first_name": "John", "last_name": "Doe"}) ... FAILED
```

### Интеграционные тесты

Тесты с реальным Redis (`test_integration.py`):
- Операции кеша
- Истечение TTL
- Персистентное хранилище
- Конкурентные операции
- Большие значения
- Специальные символы

## 🗄️ Store Interface

### Cache операции (fault-tolerant):
```python
store.cache_get(key) -> Optional[Any]  # Возвращает None при ошибке
store.cache_set(key, value, expire) -> bool  # Возвращает False при ошибке
```

### Persistent операции (must succeed):
```python
store.get(key) -> Optional[str]  # Бросает исключение при недоступности
store.set(key, value) -> None  # Бросает исключение при недоступности
```

### Важные особенности:
- **cache_get/cache_set** - используются в `get_score`, не критичны для работы
- **get/set** - используются в `get_interests`, критичны для работы
- Retry логика: 3 попытки с задержкой 0.1 сек
- Timeout: 3 секунды на операцию

## 📊 Покрытие тестами

```bash
# Запуск с отчетом о покрытии
make test-coverage
```

Покрытие включает:
- ✅ 100% api.py (валидация, обработчики)
- ✅ 100% scoring.py (бизнес-логика)
- ✅ 95%+ store.py (хранилище)
- ✅ Все edge cases и error paths

## 🔧 Конфигурация

### Redis подключение (store.py):
```python
Store(
    host="localhost",
    port=6379,
    db=0,
    socket_timeout=3,
    connect_retries=3,
    retry_delay=0.1
)
```

### API сервер:
```bash
python api.py -p 8080 -l api.log
```

## 📁 Структура проекта

```
hm_5/
├── api.py              # API сервер и валидация
├── scoring.py          # Бизнес-логика скоринга
├── store.py            # Key-value хранилище
├── test.py             # Unit и функциональные тесты
├── test_integration.py # Интеграционные тесты
├── pyproject.toml      # Конфигурация проекта
├── Makefile            # Команды для разработки
└── README.md           # Документация
```

## 🐳 Docker

### Запуск Redis для тестов:
```bash
docker run -d --name redis-test -p 6379:6379 redis:7-alpine
```

### Запуск тестов в Docker:
```bash
docker run --rm -v $(pwd):/app -w /app python:3.12 bash -c "
  pip install uv &&
  uv sync --all-extras &&
  uv run pytest test.py -v
"
```

## 🎯 Примеры использования

### Тестирование с моком:
```python
from store import MockStore

store = MockStore()
store.cache_set("key", "value")
assert store.cache_get("key") == "value"

# Симуляция ошибки
store.fail_cache = True
assert store.cache_get("key") is None
```

### Тестирование с Redis:
```python
from store import Store

store = Store()
store.set("user:1", {"name": "John", "age": 30})
data = store.get("user:1")
```

## 📝 CI/CD

GitHub Actions запускает:
- Форматирование (black, isort)
- Линтинг (flake8, mypy)
- Unit-тесты
- Отчет о покрытии

## 🤝 Вклад

1. Fork репозитория
2. Создайте feature branch
3. Напишите тесты для новой функциональности
4. Убедитесь что все тесты проходят
5. Создайте Pull Request

## 📄 Лицензия

MIT License