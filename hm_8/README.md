# 🗳️ HM_8 — Django Polls Application

[![CI](https://github.com/yourusername/repo/actions/workflows/hm_8.yml/badge.svg)](https://github.com/yourusername/repo/actions/workflows/hm_8.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![Django 5.0](https://img.shields.io/badge/django-5.0-green.svg)](https://docs.djangoproject.com/en/5.0/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://coverage.readthedocs.io/)

Веб-приложение для создания и управления опросами на Django. Реализация официального Django Tutorial с улучшениями в архитектуре, тестировании и развертывании.

## ✨ Возможности

- **Управление опросами** - Создание вопросов с множественными вариантами ответов
- **Голосование** - Пользователи могут голосовать за варианты ответов
- **Результаты** - Просмотр результатов голосования в реальном времени
- **Админ-панель** - Полнофункциональная админка для управления опросами
- **API** (опционально) - REST API для интеграции с внешними системами
- **Тестирование** - Комплексные unit и интеграционные тесты

## 📦 Структура проекта

```
hm_8/
├── mysite/
│   ├── mysite/               # Настройки проекта
│   │   ├── settings.py       # Основные настройки Django
│   │   ├── urls.py           # Главный URL роутер
│   │   ├── wsgi.py           # WSGI точка входа
│   │   └── asgi.py           # ASGI точка входа
│   ├── polls/                # Приложение опросов
│   │   ├── models.py         # Модели данных (Question, Choice)
│   │   ├── views.py          # Представления (CBV и FBV)
│   │   ├── urls.py           # URL маршруты приложения
│   │   ├── admin.py          # Настройки админ-панели
│   │   ├── apps.py           # Конфигурация приложения
│   │   ├── tests.py          # Тесты приложения
│   │   ├── forms.py          # Формы (если есть)
│   │   └── migrations/       # Миграции БД
│   ├── templates/            # HTML шаблоны
│   │   ├── polls/            # Шаблоны приложения
│   │   └── admin/            # Кастомизация админки
│   ├── static/               # Статические файлы
│   ├── manage.py             # Django управляющий скрипт
│   └── db.sqlite3            # База данных SQLite
├── requirements.txt          # Зависимости pip
├── pyproject.toml            # Конфигурация Poetry/проекта
├── Dockerfile                # Контейнеризация
├── docker-compose.yml        # Оркестрация сервисов
├── .env.example              # Пример переменных окружения
├── Makefile                  # Команды разработки
└── README.md                 # Этот файл
```

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.12+
- Poetry или pip
- SQLite (включен в Python)
- Make (опционально)

### Установка

#### Вариант 1: Poetry (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/repo.git
cd repo/hm_8

# Установка зависимостей
poetry install

# Активация виртуального окружения
poetry shell

# Применение миграций
cd mysite
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Запуск сервера разработки
python manage.py runserver
```

#### Вариант 2: pip

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Далее те же шаги с миграциями и запуском
```

#### Вариант 3: Docker

```bash
# Сборка и запуск через docker-compose
docker-compose up --build

# Приложение будет доступно на http://localhost:8000
```

### Использование Makefile

```bash
make install      # Установка зависимостей
make migrate      # Применение миграций
make run          # Запуск сервера разработки
make test         # Запуск тестов
make lint         # Проверка кода
make format       # Форматирование кода
make coverage     # Отчет о покрытии тестами
make clean        # Очистка временных файлов
```

## 🧪 Тестирование

### Запуск всех тестов

```bash
# С использованием Django test runner
python manage.py test

# С использованием pytest (если настроен)
pytest

# Через Makefile
make test
```

### Запуск с покрытием

```bash
# Генерация отчета о покрытии
coverage run --source='.' manage.py test
coverage report
coverage html  # HTML отчет в htmlcov/

# Через Makefile
make coverage
```

### Типы тестов

- **Unit тесты**: Тестирование моделей, форм, утилит
- **View тесты**: Тестирование представлений и шаблонов
- **Integration тесты**: Тестирование полного флоу приложения
- **Admin тесты**: Тестирование админ-панели

## 🔧 Конфигурация

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```bash
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Email (optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Debug toolbar
INTERNAL_IPS=127.0.0.1,localhost
```

### Настройки базы данных

По умолчанию используется SQLite. Для production рекомендуется PostgreSQL:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'polls_db',
        'USER': 'polls_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🐳 Docker

### Сборка образа

```bash
docker build -t django-polls:latest .
```

### Запуск контейнера

```bash
docker run -p 8000:8000 django-polls:latest
```

### Docker Compose

```bash
# Запуск всех сервисов
docker-compose up

# Запуск в фоне
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f
```

## 📊 API Endpoints

### Основные URL

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/polls/` | GET | Список всех опросов |
| `/polls/<id>/` | GET | Детали опроса |
| `/polls/<id>/vote/` | POST | Голосование |
| `/polls/<id>/results/` | GET | Результаты опроса |
| `/admin/` | GET | Админ-панель |

### REST API (если реализован)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/questions/` | GET, POST | Список/создание вопросов |
| `/api/questions/<id>/` | GET, PUT, DELETE | CRUD операции |
| `/api/choices/` | GET, POST | Варианты ответов |
| `/api/vote/` | POST | API для голосования |

## 🛠 Разработка

### Создание миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

### Загрузка тестовых данных

```bash
python manage.py loaddata fixtures/initial_data.json
```

### Запуск Django shell

```bash
python manage.py shell
# или с расширенными возможностями
python manage.py shell_plus
```

### Debug Toolbar

Django Debug Toolbar автоматически доступен в режиме DEBUG по адресу `/__debug__/`

## 🚦 CI/CD

GitHub Actions выполняет следующие проверки:

1. **Линтинг**: Black, isort, flake8
2. **Типизация**: mypy
3. **Тесты**: Django tests с покрытием
4. **Безопасность**: bandit, safety
5. **Миграции**: Проверка на конфликты

Пайплайн запускается при:
- Push в ветку `main`
- Pull request в `main`
- Изменениях в директории `hm_8/`

## 📈 Мониторинг и логирование

### Логирование

Настроено в `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## 🔐 Безопасность

- Используйте сильный `SECRET_KEY`
- Отключите `DEBUG` в production
- Настройте `ALLOWED_HOSTS`
- Используйте HTTPS в production
- Регулярно обновляйте зависимости
- Включите CSRF защиту
- Настройте CORS правильно

## 📚 Полезные ссылки

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Tutorial](https://docs.djangoproject.com/en/5.0/intro/tutorial01/)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей

## 👤 Автор

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

---

*Это домашнее задание является частью курса по Python/Django разработке.*