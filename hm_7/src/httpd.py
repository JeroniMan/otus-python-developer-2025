import argparse
import logging
import os
import sys
from multiprocessing import Process
from typing import Callable, Optional

from dotenv import load_dotenv
from handler.handler import FileService, HandlersFacade
from protocol.request import HTTPRequest
from server.server import HTTPServer

logger = logging.getLogger("httpserver")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Simple HTTP server")
    parser.add_argument(
        "-r", "--root", help="Document root directory to serve files from"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Port to listen on (default: 8080)"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=1, help="Number of worker processes"
    )
    parser.add_argument(
        "-u",
        "--upload_timeout",
        type=int,
        default=100,
        help="Timeout of request data uploading",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument("--cache_ttl", default="5", help="File cache minutes ttl")
    parser.add_argument(
        "--max_file_size_in_cache", default="5242880", help="Max file size in cache"
    )
    parser.add_argument(
        "--max_cache_size", default="100", help="Max files number in cache"
    )
    return parser.parse_args()


def empty_headers(_):
    return {}


def always_true(_: HTTPRequest) -> bool:
    return True


def start_worker(handler: Callable[[HTTPRequest], Optional[bytes]], args):
    server = HTTPServer(
        connect_timeout_ms=args.upload_timeout,
        server_address=(args.host, args.port),
        base_headers={},
        external_handler=handler,
        headers_binding=empty_headers,
        logger=logger,
    )
    server.server_start()


def main():
    load_dotenv()
    args = parse_args()

    root = args.root or os.getenv("DOCUMENT_ROOT")
    if not os.path.isdir(root):
        logger.error(f"Error: document root '{root}' does not exist.")
        sys.exit(1)

    cache_cfg = {
        "cache_ttl": args.cache_ttl,
        "max_file_size_in_cache": args.max_file_size_in_cache,
        "max_cache_size": args.max_cache_size,
    }

    file_service = FileService(root, logger, cache_cfg)
    handler = HandlersFacade().when(always_true, file_service)

    for _ in range(args.workers):
        Process(target=start_worker, args=(handler, args)).start()


if __name__ == "__main__":
    main()
