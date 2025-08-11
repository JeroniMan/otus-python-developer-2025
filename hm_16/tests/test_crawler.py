"""
Тесты для краулера
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.crawler import HNCrawler
from src.storage import PostgresStorage


@pytest.fixture
async def mock_storage():
    """Мок для хранилища"""
    storage = AsyncMock(spec=PostgresStorage)
    storage.save_story = AsyncMock(return_value=1)
    storage.save_link = AsyncMock()
    return storage


@pytest.fixture
def sample_html():
    """Пример HTML страницы HN"""
    return """
    <html>
        <tr class="athing" id="123">
            <td class="title">
                <span class="titleline">
                    <a href="https://example.com">Test Story</a>
                </span>
            </td>
        </tr>
        <tr>
            <td class="subtext">
                <span class="score">100 points</span>
                by <a class="hnuser">testuser</a>
                <a href="item?id=123">50 comments</a>
            </td>
        </tr>
    </html>
    """


@pytest.mark.asyncio
async def test_parse_front_page(mock_storage, sample_html):
    """Тест парсинга главной страницы"""
    crawler = HNCrawler(mock_storage, max_stories=1)

    with patch.object(crawler, 'fetch_page', return_value=sample_html):
        async with crawler:
            stories = await crawler.parse_front_page()

    assert len(stories) == 1
    assert stories[0]['title'] == 'Test Story'
    assert stories[0]['url'] == 'https://example.com'
    assert stories[0]['score'] == 100
    assert stories[0]['author'] == 'testuser'
    assert stories[0]['comments_count'] == 50


@pytest.mark.asyncio
async def test_parse_comments_page(mock_storage):
    """Тест парсинга страницы с комментариями"""
    html = """
    <html>
        <div class="comment">
            <span>Check out <a href="https://link1.com">this link</a></span>
            <span>And <a href="https://link2.com">another one</a></span>
        </div>
    </html>
    """

    crawler = HNCrawler(mock_storage)

    with patch.object(crawler, 'fetch_page', return_value=html):
        async with crawler:
            links = await crawler.parse_comments_page("https://news.ycombinator.com/item?id=123")

    assert len(links) == 2
    assert "https://link1.com" in links
    assert "https://link2.com" in links


@pytest.mark.asyncio
async def test_process_story(mock_storage):
    """Тест обработки одной новости"""
    story = {
        'hn_id': 123,
        'title': 'Test Story',
        'url': 'https://example.com',
        'score': 100,
        'author': 'testuser',
        'comments_count': 5,
        'comments_url': 'https://news.ycombinator.com/item?id=123'
    }

    crawler = HNCrawler(mock_storage)

    with patch.object(crawler, 'parse_comments_page', return_value=['https://link1.com']):
        async with crawler:
            await crawler.process_story(story)

    mock_storage.save_story.assert_called_once_with(story)
    mock_storage.save_link.assert_called_once_with(1, 'https://link1.com')


@pytest.mark.asyncio
async def test_extract_comments_count():
    """Тест извлечения количества комментариев"""
    crawler = HNCrawler(AsyncMock())

    # Создаем мок элемента
    elem = MagicMock()
    elem.text = "123 comments"

    count = crawler._extract_comments_count(elem)
    assert count == 123

    # Тест с пустым элементом
    count = crawler._extract_comments_count(None)
    assert count == 0