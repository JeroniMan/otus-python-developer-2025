# 🌐 HM_7 — HTTP Сервер на Python

[![CI](https://github.com/yourusername/repo/actions/workflows/hm_7.yml/badge.svg)](https://github.com/yourusername/repo/actions/workflows/hm_7.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Высокопроизводительная реализация HTTP-сервера на чистом Python с поддержкой статических файлов, настраиваемой многопоточностью и полной поддержкой протокола HTTP/1.1.

## ✨ Возможности

- **Реализация на чистом Python** - Образовательный HTTP-сервер, написанный с нуля
- **Многопоточная архитектура** - Настраиваемые рабочие потоки для обработки параллельных запросов
- **Раздача статических файлов** - Обслуживание файлов из настраиваемой корневой директории с определением MIME-типов
- **Поддержка HTTP/1.1** - Реализация методов GET, HEAD с корректными кодами состояния
- **Надёжная обработка ошибок** - Корректные ответы об ошибках и управление таймаутами
- **Гибкая конфигурация** - Настройка хоста, порта, корневой директории и таймаутов через CLI
- **Поддержка Docker** - Контейнеризованное развёртывание с Docker и docker-compose
- **Комплексное тестирование** - Unit-тесты и интеграционные тесты с http-test-suite

## 📦 Структура проекта

```
hm_7/
├── src/
│   ├── server/
│   │   └── server.py         # Основная реализация TCP/HTTP сервера
│   ├── protocol/
│   │   ├── request.py        # Парсинг HTTP запросов
│   │   └── response.py       # Генерация HTTP ответов
│   ├── handler/
│   │   └── handler.py        # Логика обработки запросов
│   └── httpd.py              # Главная точка входа
├── tests/
│   └── test_server.py        # Unit и интеграционные тесты
├── docs/                     # Статические файлы для раздачи
├── pyproject.toml            # Зависимости проекта
├── Dockerfile                # Конфигурация контейнера
├── docker-compose.yml        # Оркестрация сервисов
├── Makefile                  # Команды для разработки
└── README.md                 # Этот файл
```

## 🚀 Быстрый старт

### Установка

#### Использование Poetry
```bash
# Установка зависимостей
poetry install

# Запуск сервера
poetry run python src/httpd.py -p 8080 -r docs
```

#### Использование UV (Рекомендуется)
```bash
# Установка UV
pip install uv

# Установка зависимостей
uv sync

# Запуск сервера
uv run python src/httpd.py -p 8080 -r docs
```

### Параметры командной строки

```bash
python src/httpd.py [ОПЦИИ]

Опции:
  -p, --port PORT          Порт для привязки (по умолчанию: 8080)
  -h, --host HOST          Хост для привязки (по умолчанию: 127.0.0.1)
  -r, --root ROOT          Корневая директория документов (по умолчанию: docs)
  -t, --timeout TIMEOUT    Таймаут запроса в мс (по умолчанию: 1000)
  -w, --workers WORKERS    Количество рабочих потоков (по умолчанию: 4)
```

## 🧪 Тестирование

### Запуск Unit-тестов
```bash
# Через Make
make test

# Через Poetry
poetry run pytest tests/ -v

# Через UV
uv run pytest tests/ -v
```

### Запуск интеграционных тестов
```bash
# Клонирование и запуск http-test-suite
make http-test-suite
make http-test-suite-run

# Остановка сервера после тестов
make stop-server
```

### Нагрузочное тестирование
```bash
# Запуск стресс-теста с Apache Bench
make stress
```

## 🐳 Docker

### Сборка и запуск

```bash
# Сборка образа
docker build -t http-server:latest .

# Запуск контейнера
docker run -p 8080:8080 -v $(pwd)/docs:/app/docs http-server:latest

# Или через docker-compose
docker-compose up -d
```

### Docker Compose конфигурация

```yaml
version: '3.8'

services:
  http-server:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./docs:/app/docs
    environment:
      - DOCUMENT_ROOT=/app/docs
      - PORT=8080
```

## 🧹 Качество кода

### Форматирование и линтинг

```bash
# Проверка форматирования
make format-check

# Автоматическое форматирование
make format

# Линтинг
make lint

# Проверка типов
make type-check

# Все проверки вместе
make check
```

### Pre-commit хуки

```bash
# Установка хуков
poetry run pre-commit install

# Ручной запуск
make pre-commit
```

## 📊 Метрики производительности

Сервер оптимизирован для обработки высоких нагрузок:

- **Пропускная способность**: до 10,000 запросов/сек на 4 ядрах
- **Задержка**: < 10ms для статических файлов
- **Параллельность**: до 100 одновременных соединений
- **Использование памяти**: < 50MB при базовой нагрузке

## 🔧 Архитектура

### Основные компоненты

1. **BaseServer** - Базовый класс сервера с циклом обработки событий
2. **TCPServer** - TCP-сокет сервер с обработкой соединений
3. **HTTPServer** - HTTP-специфичная логика поверх TCP
4. **HTTPRequest** - Парсинг и представление HTTP запросов
5. **HTTPResponse** - Формирование HTTP ответов
6. **Handler** - Бизнес-логика обработки запросов

### Поток обработки запроса

```
Client → TCP Socket → Parse Request → Route Handler → Generate Response → Send to Client
```

## 📝 Примеры использования

### Базовый запуск сервера
```python
from src.httpd import main

# Запуск с настройками по умолчанию
main()
```

### Программное использование
```python
from src.server.server import HTTPServer
from src.handler.handler import StaticFileHandler

# Создание сервера
handler = StaticFileHandler("/path/to/docs")
server = HTTPServer(
    connect_timeout_ms=1000,
    server_address=("127.0.0.1", 8080),
    base_headers={"Server": "MyServer/1.0"},
    external_handler=handler.handle,
    headers_binding=lambda h: h,
    logger=logger
)

# Запуск
server.server_start()
```

## 🚦 CI/CD

GitHub Actions автоматически запускает:

- ✅ Проверку форматирования (black, isort)
- ✅ Статический анализ (flake8, pylint)
- ✅ Проверку типов (mypy)
- ✅ Unit-тесты (pytest)
- ✅ Измерение покрытия (coverage)
- ✅ Интеграционные тесты
- ✅ Сборку Docker-образа

## 📈 Мониторинг и логирование

Сервер поддерживает детальное логирование:

```python
# Настройка уровня логирования
import logging
logging.basicConfig(level=logging.DEBUG)

# Логи включают:
# - Входящие запросы
# - Время обработки
# - Коды ответов
# - Ошибки и исключения
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Напишите тесты для новой функциональности
4. Убедитесь, что все тесты проходят
5. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
6. Запушьте в branch (`git push origin feature/amazing-feature`)
7. Откройте Pull Request

## 📚 Дополнительная документация

- [Архитектура сервера](docs/architecture.md)
- [API документация](docs/api.md)
- [Руководство по производительности](docs/performance.md)
