import logging
import os.path
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from urllib.parse import unquote

from protocol.request import HTTPRequest


class FileService:
    def __init__(
        self,
        root_folder: str,
        logger: logging.Logger,
        cache_config: Optional[Dict[str, int]],
    ):
        self.root_folder = root_folder
        self.logger = logger

        self._cache: OrderedDict[str, tuple[datetime, bytes]] = OrderedDict()

        if cache_config:
            self.cache_ttl = timedelta(minutes=int(cache_config.get("cache_ttl", 5)))
            self.max_file_size_in_cache = int(
                cache_config.get("max_file_size_in_cache", 5 * 1024 * 1024)
            )
            self.max_cache_size = int(cache_config.get("max_cache_size", 100))
        else:
            self.cache_ttl = timedelta(0)
            self.max_file_size_in_cache = 0
            self.max_cache_size = 0

    def __call__(self, income: HTTPRequest) -> bytes:
        path = unquote(income.path.lstrip("/"))
        if not path or path.endswith("/"):
            path += "index.html"

        full_path = os.path.join(self.root_folder, path)
        self.logger.debug(f"Try to get file with path {full_path}")

        # if not full_path.startswith(os.path.abspath(self.root_folder)):
        #     self.logger.warning(f"Blocked path traversal attempt: {full_path}")
        #     raise FileNotFoundError(f"Access denied: {path}")

        now = datetime.now()
        if full_path in self._cache:
            cached_time, cached_data = self._cache[full_path]
            if now - cached_time < self.cache_ttl:
                self.logger.debug(f"Cache hit for {full_path}")
                return cached_data

        self.logger.debug(f"Cache miss or expired for {full_path}")

        if not os.path.exists(full_path):
            self.logger.error(f"File not found {full_path}")
            raise FileNotFoundError(f"File {path} doesn't exists")
        elif not os.path.isfile(full_path):
            full_path += "/index.html"
            if not os.path.exists(full_path):
                self.logger.error(f"File not found {full_path}")
                raise FileNotFoundError(f"File {path} doesn't exists")
        if not os.access(full_path, os.R_OK):
            self.logger.error(f"File not readable {full_path}")
            raise FileNotFoundError(f"File not readable {path}")

        try:
            with open(full_path, "rb") as f:
                data = f.read()
                self.logger.info(f"Served file: {full_path} with len {len(data)}")
                self.logger.debug(f"The file: {full_path} data: {data!r}")
                if len(data) < self.max_file_size_in_cache:
                    self._cache[full_path] = (now, data)
                    if len(self._cache) > self.max_cache_size:
                        self._cache.popitem(last=False)
                return data
        except Exception as e:
            self.logger.exception(f"Failed to read file: f{path}")
            raise e


class EmptyHandler:
    def __init__(self, response: Optional[bytes]):
        self.response = response

    def __call__(self, income: HTTPRequest) -> Optional[bytes]:
        return self.response


class HandlersFacade:
    def __init__(self):
        self.rules: list[
            tuple[Callable[[HTTPRequest], bool], Callable[[HTTPRequest], bytes]]
        ] = []

    def when(
        self,
        condition: Callable[[HTTPRequest], bool],
        handler: Callable[[HTTPRequest], bytes],
    ):
        self.rules.append((condition, handler))
        return self

    def __call__(self, income: HTTPRequest) -> bytes:
        for condition, handler in self.rules:
            if condition(income):
                return handler(income)
        raise ValueError("No matching handler found")
