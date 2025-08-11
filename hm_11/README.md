# Домашнее задание 11: Реализация логистической регрессии

[![CI/CD](https://github.com/yourusername/homework-11/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/homework-11/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 📚 Описание

Реализация логистической регрессии с нуля для классификации текстов (анализ тональности) на датасете отзывов о еде с Amazon. Этот проект является частью домашних заданий курса OTUS Python Pro.

## 🎯 Возможности

- Собственная реализация логистической регрессии со стохастическим градиентным спуском
- Предобработка текста и извлечение признаков с использованием TF-IDF
- Анализ тональности отзывов о еде с Amazon
- Сравнение с реализацией из sklearn
- Комплексное тестирование и валидация

## 🛠️ Технологии

- **Python 3.12**
- **NumPy** - Численные вычисления
- **SciPy** - Операции с разреженными матрицами
- **Pandas** - Работа с данными
- **Scikit-learn** - Сравнение и извлечение признаков
- **Matplotlib/Seaborn** - Визуализация
- **UV** - Быстрый менеджер пакетов Python
- **Poetry** - Управление зависимостями

## 📋 Требования

- Python 3.12 или выше
- UV менеджер пакетов ([руководство по установке](https://github.com/astral-sh/uv))

## 🚀 Установка

### Используя UV (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/homework-11.git
cd homework-11

# Установить UV, если еще не установлен
curl -LsSf https://astral.sh/uv/install.sh | sh

# Синхронизировать зависимости
uv sync

# Активировать виртуальное окружение
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
```

### Используя Poetry

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/homework-11.git
cd homework-11

# Установить зависимости
poetry install

# Активировать виртуальное окружение
poetry shell
```

## 📁 Структура проекта

```
homework-11/
├── dmia/
│   ├── __init__.py
│   ├── gradient_check.py          # Утилиты проверки градиента
│   └── classifiers/
│       ├── __init__.py
│       └── logistic_regression.py # Реализация LogisticRegression
├── data/
│   └── train.csv                  # Обучающие данные (не включены, скачать отдельно)
├── tests/
│   ├── __init__.py
│   ├── test_logistic_regression.py
│   └── test_gradient_check.py
├── pyproject.toml                 # Зависимости проекта (Poetry)
├── uv.lock                        # Файл блокировки UV
├── .gitignore
├── .pre-commit-config.yaml        # Хуки pre-commit
├── README.md

```

## 🎮 Использование

### Запуск Jupyter Notebook

```bash
# Запустить Jupyter Lab
jupyter lab

# Открыть notebooks/homework.ipynb
```

### Использование класса LogisticRegression

```python
from dmia.classifiers import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

# Загрузить данные
df = pd.read_csv('data/train.csv')
reviews = df['Reviews_Summary'].values
labels = df['Prediction'].values

# Предобработка текста
vectorizer = TfidfVectorizer(max_features=3000)
X = vectorizer.fit_transform(reviews)

# Обучить модель
clf = LogisticRegression()
clf.train(X, labels, learning_rate=1.0, num_iters=1000, batch_size=256, reg=1e-3)

# Сделать предсказания
predictions = clf.predict(X_test)
```

## 🧪 Тестирование

```bash
# Запустить все тесты
uv run pytest

# Запустить с покрытием
uv run pytest --cov=dmia --cov-report=html

# Запустить конкретный файл тестов
uv run pytest tests/test_logistic_regression.py -v
```

## 🔧 Разработка

### Настройка pre-commit хуков

```bash
# Установить pre-commit хуки
uv run pre-commit install

# Запустить хуки вручную
uv run pre-commit run --all-files
```

### Форматирование кода и линтинг

```bash
# Форматировать код с помощью black
uv run black .

# Проверить с помощью ruff
uv run ruff check .

# Исправить проблемы линтинга
uv run ruff check --fix .
```

## 📊 Результаты

Собственная реализация достигает сравнимой производительности с LogisticRegression из sklearn:

- **Точность на обучении**: ~53%
- **Точность на тесте**: ~53%
- **Время обучения**: < 30 секунд для 1000 итераций

### Кривые обучения

Модель показывает хорошую сходимость без значительного переобучения:

![Кривые обучения](docs/images/learning_curves.png)

### Топ признаки

**Индикаторы положительной тональности**:
- "excellent", "perfect", "delicious", "love", "great"

**Индикаторы отрицательной тональности**:
- "terrible", "awful", "disappointed", "waste", "horrible"

## 🤝 Вклад в проект

1. Сделайте форк репозитория
2. Создайте ветку для новой функциональности (`git checkout -b feature/AmazingFeature`)
3. Зафиксируйте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте изменения в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под лицензией MIT - подробности см. в файле [LICENSE](LICENSE).

## 🙏 Благодарности

- Курсу OTUS Python Pro за домашнее задание
- Курсу Stanford CS231n за вдохновение по проверке градиентов

## 📚 Ссылки

- [Понимание логистической регрессии](https://www.coursera.org/learn/machine-learning)
- [Объяснение TF-IDF](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)
- [Проверка градиента](http://ufldl.stanford.edu/tutorial/supervised/LogisticRegression/)

## ⚠️ Данные

Обучающие данные (`train.csv`) не включены в репозиторий из-за ограничений по размеру. Вы можете скачать их из материалов курса или связаться с преподавателем.

## 🐛 Известные проблемы

- Модели может потребоваться больше итераций для сходимости на очень больших датасетах
- Операции с разреженными матрицами могут быть дополнительно оптимизированы для производительности

## 📈 Будущие улучшения

- [ ] Реализовать раннюю остановку
- [ ] Добавить опцию L1-регуляризации
- [ ] Реализовать мини-батчевый градиентный спуск с моментумом
- [ ] Добавить больше метрик оценки (precision, recall, F1-score)
- [ ] Реализовать кросс-валидацию
- [ ] Добавить поддержку многоклассовой классификации

## 🚀 Быстрый старт

```bash
# Клонировать и настроить проект
git clone https://github.com/yourusername/homework-11.git
cd homework-11

# Установить UV и зависимости
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Активировать окружение
source .venv/bin/activate

# Запустить тесты
make test

# Запустить Jupyter
make notebook
```

## 📞 Контакты

Если у вас есть вопросы по проекту, создайте [issue](https://github.com/yourusername/homework-11/issues) в репозитории.