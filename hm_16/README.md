# HN Crawler - Асинхронный краулер для Hacker News

[![CI](https://github.com/username/hn-crawler/workflows/CI/badge.svg)](https://github.com/username/hn-crawler/actions)
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)

Асинхронный краулер для парсинга топовых новостей с [Hacker News](https://news.ycombinator.com) и извлечения всех ссылок из комментариев.

## 📋 Описание

Краулер выполняет следующие задачи:
- Каждые N секунд запускается и парсит топ-30 новостей с главной страницы HN
- Для каждой новости сохраняет: ID, заголовок, URL, автора, количество очков и комментариев
- Переходит на страницу обсуждения каждой новости и извлекает все внешние ссылки из комментариев
- Сохраняет данные в PostgreSQL с защитой от дублирования

## 🚀 Быстрый старт

### Используя Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone <repository-url>
cd hm_16

# Запустить через Docker Compose
docker-compose up
```

### Локальная установка

```bash
# 1. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить переменные окружения
cp .env.example .env
# Отредактировать .env файл с параметрами вашей БД

# 4. Запустить PostgreSQL (если не запущен)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hn_crawler \
  -p 5432:5432 \
  postgres:15-alpine

# 5. Запустить краулер
python main.py
```

## ⚙️ Конфигурация

Настройки через переменные окружения в файле `.env`:

```env
# База данных
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hn_crawler
DB_USER=postgres
DB_PASSWORD=postgres

# Краулер
CRAWLER_INTERVAL=300  # Интервал запуска в секундах (по умолчанию 5 минут)
MAX_STORIES=30        # Количество новостей для парсинга
```

## 🗂️ Структура проекта

```
hm_16/
├── src/
│   ├── crawler.py      # Основная логика краулера
│   ├── storage.py      # Работа с БД
│   └── __init__.py
├── tests/
│   └── test_crawler.py # Тесты
├── .github/
│   └── workflows/
│       └── ci.yml      # CI/CD pipeline
├── main.py            # Точка входа
├── requirements.txt   # Зависимости
├── Dockerfile        
├── docker-compose.yml 
└── README.md
```

## 🗄️ Структура базы данных

### Таблица `stories` - новости
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| hn_id | INTEGER | ID новости на HN |
| title | TEXT | Заголовок |
| url | TEXT | Ссылка на источник |
| author | VARCHAR(100) | Автор |
| score | INTEGER | Количество очков |
| comments_count | INTEGER | Количество комментариев |
| created_at | TIMESTAMP | Время добавления |

### Таблица `links` - ссылки из комментариев
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| story_id | INTEGER | ID новости (внешний ключ) |
| url | TEXT | URL ссылки |
| created_at | TIMESTAMP | Время добавления |

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/ -v

# Запуск с покрытием кода
pytest tests/ --cov=src --cov-report=html

# Используя Makefile
make test
```

## 🛠️ Полезные команды

```bash
# Установка зависимостей
make install

# Запуск краулера
make run

# Запуск тестов
make test

# Docker команды
make docker-build   # Собрать образ
make docker-up      # Запустить контейнеры
make docker-down    # Остановить контейнеры

# Очистка временных файлов
make clean
```

## 🔄 CI/CD

Проект использует GitHub Actions для автоматизации:
- Запуск тестов при каждом push
- Проверка кода линтером (flake8)
- Сборка и тестирование Docker образа

## 📊 Мониторинг работы

Краулер логирует свою работу в консоль:
```
2024-01-15 10:00:00 - INFO - Запуск краулера с интервалом 300 секунд
2024-01-15 10:00:01 - INFO - Получено 30 новостей
2024-01-15 10:00:02 - INFO - Обработана новость: Show HN: My Side Project
2024-01-15 10:00:03 - INFO - Найдено 15 ссылок в комментариях
2024-01-15 10:00:10 - INFO - Обработка завершена
2024-01-15 10:00:10 - INFO - Сбор завершен. Ждем 300 секунд...
```

## 🐛 Решение проблем

### Ошибка подключения к БД
```bash
# Проверить, что PostgreSQL запущен
docker ps | grep postgres

# Проверить параметры подключения в .env
cat .env
```

### Ошибка "Too many requests"
Увеличьте интервал между запросами в `.env`:
```env
CRAWLER_INTERVAL=600  # 10 минут вместо 5
```

### Проблемы с Docker
```bash
# Пересобрать образы
docker-compose build --no-cache

# Посмотреть логи
docker-compose logs -f crawler
```

## 📚 Используемые технологии

- **Python 3.11** - основной язык
- **aiohttp** - асинхронные HTTP запросы
- **asyncpg** - асинхронная работа с PostgreSQL
- **BeautifulSoup4** - парсинг HTML
- **Docker** - контейнеризация
- **pytest** - тестирование
- **GitHub Actions** - CI/CD

## 📝 Лицензия

MIT

## 👨‍💻 Автор

Домашнее задание №16 - Асинхронный краулер