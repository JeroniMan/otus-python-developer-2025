# Домашнее задание 14: Memcache Loader

[![CI/CD](https://github.com/yourusername/hw-memcache-loader/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/hw-memcache-loader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![codecov](https://codecov.io/gh/yourusername/hw-memcache-loader/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/hw-memcache-loader)

## 📚 Описание

Высокопроизводительный загрузчик данных в Memcached для обработки информации об установленных приложениях на мобильных устройствах. Проект использует многопоточность для параллельной обработки и Protocol Buffers для эффективной сериализации данных.

## 🎯 Основные возможности

- **Многопоточная обработка** - параллельная загрузка данных с использованием пула потоков
- **Protocol Buffers** - эффективная сериализация данных для хранения в Memcached
- **Обработка больших файлов** - поддержка gzip-сжатых TSV файлов
- **Отказоустойчивость** - автоматические повторные попытки при сбоях соединения
- **Мониторинг прогресса** - визуализация процесса обработки с помощью progress bar
- **Гибкая конфигурация** - настройка через командную строку
- **Dry-run режим** - тестовый запуск без записи в Memcached

## 🏗️ Архитектура

### Компоненты системы

1. **Parser** - разбор TSV файлов и валидация данных
2. **Writer Pool** - пул потоков для записи в Memcached
3. **Memcache Pool** - пул соединений с серверами Memcached
4. **Protobuf Serializer** - сериализация данных в Protocol Buffers

### Схема работы

```
TSV файлы → Parser → Queue → Writer Pool → Memcache Pool → Memcached
                        ↓
                  Progress Bar
```

## 🛠️ Технологии

- **Python 3.12** - основной язык разработки
- **pymemcache** - клиент для работы с Memcached
- **Protocol Buffers** - бинарный формат сериализации
- **threading** - многопоточная обработка
- **progressbar2** - визуализация прогресса
- **UV** - современный менеджер пакетов Python

## 📋 Требования

### Системные требования
- Python 3.12 или выше
- Memcached сервер(ы)
- UV package manager ([установка](https://github.com/astral-sh/uv))

### Memcached серверы
По умолчанию используются следующие адреса:
- IDFA: 127.0.0.1:33013
- GAID: 127.0.0.1:33014
- ADID: 127.0.0.1:33015
- DVID: 127.0.0.1:33016

## 🚀 Установка

### Быстрый старт с UV

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/hw-memcache-loader.git
cd hw-memcache-loader

# Установить UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Синхронизировать зависимости
uv sync

# Активировать виртуальное окружение
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
```

### Установка Memcached (для локальной разработки)

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install memcached
```

#### macOS
```bash
brew install memcached
brew services start memcached
```

#### Docker
```bash
docker run -d -p 33013-33016:11211 --name memcached memcached:latest
```

## 📁 Структура проекта

```
hw-memcache-loader/
├── memc_load.py               # Основной скрипт загрузчика
├── appsinstalled.proto        # Protocol Buffers схема
├── appsinstalled_pb2.py       # Сгенерированный код protobuf
├── tests/
│   ├── __init__.py
│   ├── test_all.py            # Тесты
│   └── fixtures/
│       ├── sample.tsv         # Тестовые данные
│       └── sample.tsv.gz      # Сжатые тестовые данные
├── pyproject.toml             # Конфигурация проекта
├── uv.lock                    # Lock файл зависимостей
├── Makefile                   # Команды для разработки
├── .gitignore
├── .pre-commit-config.yaml    # Pre-commit хуки
└── README.md

```

## 🎮 Использование

### Основной запуск

```bash
python memc_load.py --pattern="/data/appsinstalled/*.tsv.gz"
```

### Параметры командной строки

| Параметр | Описание | Значение по умолчанию |
|----------|----------|----------------------|
| `--pattern` | Паттерн для поиска файлов | `/data/appsinstalled/*.tsv.gz` |
| `--maxworkers` | Количество потоков | 5 |
| `--dry` | Режим тестового запуска | False |
| `--idfa` | Адрес Memcached для IDFA | 127.0.0.1:33013 |
| `--gaid` | Адрес Memcached для GAID | 127.0.0.1:33014 |
| `--adid` | Адрес Memcached для ADID | 127.0.0.1:33015 |
| `--dvid` | Адрес Memcached для DVID | 127.0.0.1:33016 |
| `--log` | Файл для логов | None (stdout) |
| `--loginfo` | Уровень логирования INFO | False |
| `--test` | Запустить тесты | False |

### Примеры использования

#### Тестовый запуск (dry-run)
```bash
python memc_load.py --dry --pattern="tests/fixtures/*.tsv.gz"
```

#### Запуск с увеличенным количеством потоков
```bash
python memc_load.py --maxworkers=10 --pattern="/data/*.tsv.gz"
```

#### Запуск с логированием
```bash
python memc_load.py --log=loader.log --loginfo
```

#### Запуск тестов
```bash
python memc_load.py --test
# или
make test
```

## 🧪 Тестирование

```bash
# Запустить все тесты
make test

# Запустить с покрытием
make test-coverage

# Запустить конкретный тест
uv run pytest tests/test_all.py::TestUnits::test_parse_appinstalled_values -v
```

### Структура тестов

- **test_protobaf_serializer** - тестирование сериализации Protocol Buffers
- **test_dot_rename** - тестирование переименования файлов
- **test_parse_appinstalled** - тестирование парсера данных
- **test_insert_appinstalled** - тестирование вставки в Memcached
- **test_main_logic** - интеграционный тест основной логики

## 🔧 Разработка

### Использование Makefile

```bash
# Показать доступные команды
make help

# Установить зависимости
make install

# Запустить тесты
make test

# Проверить код
make lint

# Форматировать код
make format

# Запустить все проверки
make check

# Собрать protobuf
make proto

# Очистить временные файлы
make clean
```

### Генерация Protocol Buffers

```bash
# Установить protoc компилятор
make install-protoc

# Сгенерировать Python код из .proto файла
make proto
```

### Pre-commit хуки

```bash
# Установить хуки
make pre-commit

# Запустить вручную
uv run pre-commit run --all-files
```

## 📊 Производительность

### Характеристики производительности

- **Скорость обработки**: ~100,000 записей/сек (зависит от железа)
- **Использование памяти**: < 100MB для файлов до 1GB
- **Параллелизм**: до 20 потоков эффективно
- **Размер очереди**: 4000 элементов (настраивается)

### Оптимизация

1. **Увеличение потоков**: `--maxworkers=20` для больших файлов
2. **Настройка пула соединений**: изменить `max_pool_size` в коде
3. **Размер очереди**: изменить `maxsize` параметр Queue
4. **Таймауты**: настроить `connect_timeout` и `timeout` для Memcached

## 🔍 Мониторинг

### Логирование

Приложение логирует следующую информацию:
- Начало и конец обработки файлов
- Количество обработанных и ошибочных записей
- Процент ошибок и статус загрузки
- Исключения и ошибки соединения

### Метрики

- **Processed** - количество успешно обработанных записей
- **Errors** - количество ошибок
- **Error Rate** - процент ошибок (должен быть < 1%)

## 🐛 Отладка

### Режим отладки

```bash
# Включить debug логирование
python memc_load.py --dry --log=debug.log
```

### Частые проблемы

1. **Connection refused** - проверьте, что Memcached запущен
2. **High error rate** - проверьте формат данных и доступность серверов
3. **Slow processing** - увеличьте количество потоков

## 🚀 CI/CD

### GitHub Actions

Автоматические проверки при каждом push:
- Линтинг кода (ruff, black)
- Запуск тестов
- Проверка покрытия кода
- Проверка безопасности
- Сборка и публикация артефактов

### Локальный запуск CI

```bash
# Запустить все проверки локально
make ci
```

## 📈 Метрики качества кода

- **Покрытие тестами**: > 80%
- **Соответствие PEP8**: 100%
- **Документация**: все публичные функции
- **Type hints**: частичная типизация

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменений (`git commit -m 'feat: add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Распространяется под лицензией MIT. См. [LICENSE](LICENSE) для подробностей.


## 📚 Полезные ссылки

- [Memcached Documentation](https://memcached.org/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [pymemcache Documentation](https://pymemcache.readthedocs.io/)
- [Python Threading](https://docs.python.org/3/library/threading.html)

## ⚠️ Важные замечания

- Убедитесь, что Memcached серверы доступны перед запуском
- Файлы после обработки переименовываются (добавляется точка в начало)
- При error rate > 1% файл считается необработанным
- Используйте dry-run режим для тестирования