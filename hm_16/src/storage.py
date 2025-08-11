"""
Модуль для работы с базой данных
"""
import logging
from typing import Dict, Any, Optional
import asyncpg

logger = logging.getLogger(__name__)


class PostgresStorage:
    """Класс для работы с PostgreSQL"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.pool = None

    async def init(self):
        """Инициализация подключения и создание таблиц"""
        self.pool = await asyncpg.create_pool(**self.connection_params)
        await self.create_tables()
        logger.info("База данных инициализирована")

    async def create_tables(self):
        """Создает необходимые таблицы"""
        async with self.pool.acquire() as conn:
            # Таблица для новостей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id SERIAL PRIMARY KEY,
                    hn_id INTEGER UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    author VARCHAR(100),
                    score INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Таблица для ссылок из комментариев
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id SERIAL PRIMARY KEY,
                    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(story_id, url)
                )
            """)

            # Создаем индексы
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stories_hn_id ON stories(hn_id);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_links_story_id ON links(story_id);
            """)

    async def save_story(self, story: Dict[str, Any]) -> Optional[int]:
        """Сохраняет новость в БД"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("""
                    INSERT INTO stories (hn_id, title, url, author, score, comments_count)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (hn_id) 
                    DO UPDATE SET 
                        score = EXCLUDED.score,
                        comments_count = EXCLUDED.comments_count
                    RETURNING id
                """,
                                             story['hn_id'],
                                             story['title'],
                                             story.get('url', ''),
                                             story.get('author', ''),
                                             story.get('score', 0),
                                             story.get('comments_count', 0)
                                             )

                logger.debug(f"Сохранена новость: {story['title']}")
                return result['id']

            except Exception as e:
                logger.error(f"Ошибка при сохранении новости: {e}")
                return None

    async def save_link(self, story_id: int, url: str):
        """Сохраняет ссылку из комментариев"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO links (story_id, url)
                    VALUES ($1, $2)
                    ON CONFLICT (story_id, url) DO NOTHING
                """, story_id, url)

                logger.debug(f"Сохранена ссылка: {url}")

            except Exception as e:
                logger.error(f"Ошибка при сохранении ссылки: {e}")

    async def get_stories_count(self) -> int:
        """Возвращает количество сохраненных новостей"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM stories")
            return result

    async def get_links_count(self) -> int:
        """Возвращает количество сохраненных ссылок"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM links")
            return result

    async def close(self):
        """Закрывает соединение с БД"""
        if self.pool:
            await self.pool.close()
            logger.info("Соединение с БД закрыто")