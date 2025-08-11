FROM python:3.12-slim

WORKDIR /app

# Установка uv
RUN pip install uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock* ./

# Устанавливаем зависимости через uv
RUN uv sync --frozen --no-dev

# Копируем код приложения
COPY app ./app

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uv", "run", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]