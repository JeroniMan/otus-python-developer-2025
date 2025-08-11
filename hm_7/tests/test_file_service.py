import logging
import tempfile
from pathlib import Path

from webserver_src.handler.handler import FileService
from webserver_src.protocol.request import HTTPRequest


def test_file_service_serves_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "index.html"
        content = b"<html>test</html>"
        file_path.write_bytes(content)

        service = FileService(
            tmpdir, logger=logging.getLogger("test"), cache_config=None
        )
        req = HTTPRequest(
            src="test",
            method="GET",
            path="/index.html",
            version="HTTP/1.1",
            headers={},
            body=None,
        )

        result = service(req)
        assert result == content
