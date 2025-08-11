"""
Основной модуль краулера для Hacker News
"""
import asyncio
import logging
from typing import List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HNCrawler:
    """Асинхронный краулер для Hacker News"""

    BASE_URL = "https://news.ycombinator.com"

    def __init__(self, storage, max_stories: int = 30):
        self.storage = storage
        self.max_stories = max_stories
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> str:
        """Получает HTML страницы"""
        async with self.session.get(url) as response:
            return await response.text()

    async def parse_front_page(self) -> List[Dict[str, Any]]:
        """Парсит главную страницу HN"""
        html = await self.fetch_page(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')

        stories = []
        items = soup.select('.athing')[:self.max_stories]

        for item in items:
            story_id = item.get('id')
            title_elem = item.select_one('.titleline > a')

            if not title_elem:
                continue

            # Получаем метаданные из следующего элемента
            meta = item.find_next_sibling('tr')
            score_elem = meta.select_one('.score') if meta else None
            user_elem = meta.select_one('.hnuser') if meta else None
            comments_elem = meta.select_one('a[href*="item?id="]') if meta else None

            story = {
                'hn_id': int(story_id),
                'title': title_elem.text.strip(),
                'url': title_elem.get('href', ''),
                'score': int(score_elem.text.split()[0]) if score_elem else 0,
                'author': user_elem.text if user_elem else '',
                'comments_count': self._extract_comments_count(comments_elem),
                'comments_url': f"{self.BASE_URL}/item?id={story_id}"
            }

            stories.append(story)
            logger.info(f"Обработана новость: {story['title']}")

        return stories

    def _extract_comments_count(self, elem) -> int:
        """Извлекает количество комментариев"""
        if not elem:
            return 0
        text = elem.text.strip()
        if 'comment' in text:
            return int(text.split()[0])
        return 0

    async def parse_comments_page(self, url: str) -> List[str]:
        """Парсит страницу с комментариями и извлекает все ссылки"""
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            links = set()
            # Ищем все ссылки в комментариях
            for comment in soup.select('.comment'):
                for link in comment.find_all('a', href=True):
                    href = link['href']
                    # Фильтруем относительные ссылки и ссылки на HN
                    if href.startswith('http') and 'ycombinator.com' not in href:
                        links.add(href)

            logger.info(f"Найдено {len(links)} ссылок в комментариях")
            return list(links)
        except Exception as e:
            logger.error(f"Ошибка при парсинге комментариев {url}: {e}")
            return []

    async def process_story(self, story: Dict[str, Any]):
        """Обрабатывает одну новость"""
        # Сохраняем новость
        story_id = await self.storage.save_story(story)

        if story_id and story['comments_count'] > 0:
            # Парсим ссылки из комментариев
            links = await self.parse_comments_page(story['comments_url'])

            # Сохраняем ссылки
            for link in links:
                await self.storage.save_link(story_id, link)

    async def run(self):
        """Основной метод запуска краулера"""
        async with aiohttp.ClientSession() as session:
            self.session = session

            try:
                # Получаем список новостей
                stories = await self.parse_front_page()
                logger.info(f"Получено {len(stories)} новостей")

                # Обрабатываем каждую новость параллельно
                tasks = [self.process_story(story) for story in stories]
                await asyncio.gather(*tasks, return_exceptions=True)

                logger.info("Обработка завершена")

            except Exception as e:
                logger.error(f"Ошибка в процессе краулинга: {e}")
            finally:
                self.session = None