FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock README.md ./

RUN poetry install --only main --no-root && pip install python-dotenv

COPY src ./webserver_src

CMD ["python", "webserver_src/httpd.py"]