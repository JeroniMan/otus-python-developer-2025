"""
Тесты для FastAPI приложения
"""
import pytest
from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)


def test_index():
    """Тест главной страницы"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"text": "ML model inference"}


def test_analysis_hello():
    """Тест анализа слова 'hello'"""
    response = client.get("/analysis/hello")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # В слове "hello" 2 гласные (e, o) из 5 букв = 0.4
    assert abs(data["result"] - 0.4) < 0.01


def test_analysis_world():
    """Тест анализа слова 'world'"""
    response = client.get("/analysis/world")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # В слове "world" 1 гласная (o) из 5 букв = 0.2
    assert abs(data["result"] - 0.2) < 0.01


def test_analysis_empty():
    """Тест анализа пустой строки"""
    # FastAPI не позволит передать пустую строку в path параметр
    response = client.get("/analysis/")
    assert response.status_code == 404


def test_analysis_numbers():
    """Тест анализа строки с цифрами"""
    response = client.get("/analysis/12345")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # В строке "12345" нет гласных
    assert data["result"] == 0.0


def test_analysis_mixed():
    """Тест анализа смешанной строки"""
    response = client.get("/analysis/Hello123World")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # "Hello123World" - 3 гласные (e,o,o) из 13 символов
    expected = 3 / 13
    assert abs(data["result"] - expected) < 0.01


def test_analysis_all_vowels():
    """Тест строки из одних гласных"""
    response = client.get("/analysis/aeiou")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"] == 1.0


def test_analysis_no_vowels():
    """Тест строки без гласных"""
    response = client.get("/analysis/bcdfg")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"] == 0.0


def test_analysis_uppercase():
    """Тест с заглавными буквами"""
    response = client.get("/analysis/HELLO")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # Должно работать независимо от регистра
    assert abs(data["result"] - 0.4) < 0.01


def test_analysis_special_chars():
    """Тест со специальными символами"""
    response = client.get("/analysis/hello!")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # "hello!" - 2 гласные из 6 символов
    expected = 2 / 6
    assert abs(data["result"] - expected) < 0.01


def test_analysis_url_encoded():
    """Тест с URL-encoded пробелом"""
    response = client.get("/analysis/hello%20world")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    # "hello world" - 3 гласные (e,o,o) из 11 символов (включая пробел)
    expected = 3 / 11
    assert abs(data["result"] - expected) < 0.01