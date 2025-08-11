import errno
import mimetypes
import re
import select
import socket
import threading
from datetime import datetime, timedelta
from logging import Logger
from typing import Callable, Dict
from urllib.parse import parse_qs, urlparse

from protocol.request import HTTPRequest
from protocol.response import HTTPResponse

HTTP_PROTOCOL = b"HTTP/"


def _eintr_retry(func, *args):
    """restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise


class BaseServer:
    timeout = None

    def __init__(self, server_address, server_request_handler):
        """Constructor.  May be extended, do not override."""
        self.server_address = server_address
        self.server_request_handler = server_request_handler
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.
        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                # XXX: Consider using another file descriptor or
                # connecting to the socket to wake this up instead of
                # polling. Polling reduces our responsiveness to a
                #                 shutdown request and wastes cpu at all other times.
                #                 r, w, e = select.select([self], [], [], poll_interval)
                r, w, e = _eintr_retry(select.select, [self], [], [], poll_interval)
                if self in r:
                    self._handle_request_noblock()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        """Stops the serve_forever loop.
        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.
        Select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
        else:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Call finish_request."""
        self.finish_request(request, client_address)
        self.shutdown_request(request)

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        self.server_request_handler(request, client_address, self)


class TCPServer(BaseServer):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    MAX_RECV_SIZE = 4096
    max_initial_read = 8192
    request_queue_size = 5
    allow_reuse_address = False

    def __init__(self, server_address, connect_timeout_ms: int, logger: Logger):
        """Constructor. May be extended, do not override."""
        BaseServer.__init__(self, server_address, TCPServer.handle_received_data)
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.logger = logger
        self.connect_timeout_ms = connect_timeout_ms

    def server_bind(self):
        """Called by constructor to bind the socket."""
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        """Called by constructor to activate the server."""
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        """Called to clean-up the server."""
        self.socket.close()

    def fileno(self):
        """Return socket file number."""
        return self.socket.fileno()

    def get_request(self):
        """Get the request and client address from the socket."""
        return self.socket.accept()

    def shutdown_request(self, request):
        """Called to shutdown and close an individual request."""
        try:
            request.shutdown(socket.SHUT_WR)
        except socket.error as e:
            self.logger.error(f"Socket error during get_request(): {e}")
        self.close_request(request)

    def close_request(self, request):
        """Called to clean up and individual request."""
        request.close()

    def finish_request(self, request, client_address):
        self.handle_received_data(request, client_address, self)

    def handle_received_data(self, request: socket.socket, client_address, server):
        """TCP Socket handle"""
        try:
            buffer = b""
            start_time = datetime.now()
            while b"\r\n\r\n" not in buffer:
                chunk = request.recv(self.MAX_RECV_SIZE)
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > self.max_initial_read and HTTP_PROTOCOL not in buffer:
                    raise ValueError("Too much data without valid HTTP header")
            if HTTP_PROTOCOL in buffer:
                header_part, body_part = buffer.split(b"\r\n\r\n", 1)
                content_length = 0
                cl_re = re.search(
                    rb"Content-Length:\s*(\d+)", header_part, re.IGNORECASE
                )
                if cl_re:
                    content_length = int(cl_re.group(1))
                while not self._timeout(start_time) and len(buffer) < content_length:
                    chunk = request.recv(self.MAX_RECV_SIZE)
                    if not chunk:
                        break
                    body_part += chunk
                if len(body_part) != content_length:
                    raise ValueError(
                        f"Incomplete request body: expected {content_length}, got {len(body_part)}"
                    )
                buffer = header_part + b"\r\n\r\n" + body_part
            response = server.handle_data(client_address, buffer)
            request.sendall(response.to_bytes())
            self.logger.info(f"Response sent to {client_address}")
        except Exception as e:
            self.logger.exception(
                f"Error while handling request from {client_address}: {e}"
            )
        # finally:
        #     request.close()

    def _timeout(self, start_time):
        return datetime.now() - start_time > timedelta(
            milliseconds=self.connect_timeout_ms
        )


class HTTPServer(TCPServer):
    def __init__(
        self,
        connect_timeout_ms: int,
        server_address: tuple[str, int],
        base_headers: Dict[str, str],
        external_handler: Callable[[HTTPRequest], bytes],
        headers_binding: Callable[[Dict], Dict],
        logger: Logger,
    ):
        super().__init__(server_address, connect_timeout_ms, logger)
        self.base_headers = base_headers | {"Server": socket.gethostname()}
        self.handler = external_handler
        self.headers_binding = headers_binding
        self.logger = logger

        self.server_bind()
        self.server_activate()

    def server_start(self):
        self.logger.info(f"HTTP server started at {self.server_address}")
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()

    def verify_request(self, request, client_address):
        return True

    def handle_error(self, request, client_address):
        self.logger.exception(f"Unhandled error from {client_address}")

    def handle_data(self, client_address, data) -> HTTPResponse:
        self.logger.debug(f"Parsing request from {client_address}")
        request: HTTPRequest = self.parse_request(client_address, data)
        self.logger.info(f"{request.method} {request.path} from {client_address}")
        response: HTTPResponse = self.generate_response(request)
        self.logger.debug(f"Responding with {response.status_code} to {client_address}")
        return response

    def parse_request(self, client_address, data: bytes) -> HTTPRequest:
        """Handle request on http part of server"""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Invalid encoding in request")

        parts = text.split("\r\n\r\n", 1)
        header_part = parts[0]
        body_part = parts[1] if len(parts) > 1 else ""

        lines = header_part.split("\r\n")
        request_line = lines[0]
        header_lines = lines[1:]

        method, raw_path, version = request_line.strip().split()

        parsed_url = urlparse(raw_path)
        path = parsed_url.path
        params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

        headers = {}
        for line in header_lines:
            if not line.strip():
                continue
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

        body_bytes = body_part.encode("utf-8") if body_part else None

        return HTTPRequest(
            src=client_address,
            method=method,
            path=path,
            params=params,
            version=version,
            headers=headers,
            body=body_bytes,
        )

    def generate_response(self, request: HTTPRequest) -> HTTPResponse:
        if request.method not in ("GET", "HEAD"):
            self.logger.warning(f"Unsupported method: {request.method}")
            return HTTPResponse(status_code=405, headers=self.base_headers, body=None)
        try:
            reverse_headers = self.headers_binding(request.headers)
        except FileNotFoundError:
            return HTTPResponse(status_code=403, headers=self.base_headers, body=None)
        try:
            response_body = self.handler(request)
            content_type = (
                mimetypes.guess_type(request.path)[0] or "application/octet-stream"
            )
            headers = (
                self.base_headers | reverse_headers | {"Content-Type": content_type}
            )

            headers["Content-Length"] = (
                str(len(response_body)) if response_body else "0"
            )

            return HTTPResponse(
                status_code=200,
                headers=headers,
                body=None if request.method == "HEAD" else response_body,
            )
        except PermissionError:
            self.logger.warning(f"Permission denied for {request.path}")
            return HTTPResponse(
                status_code=403, headers=self.base_headers | reverse_headers, body=None
            )
        except FileNotFoundError as e:
            self.logger.exception(
                f"Failed to get file with HTTPRequest {request} error: {e}"
            )
            return HTTPResponse(
                status_code=404, headers=self.base_headers | reverse_headers, body=None
            )
