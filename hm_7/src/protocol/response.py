from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HTTPResponse:
    status_code: int
    headers: dict
    body: Optional[bytes]

    def to_bytes(self) -> bytes:
        reason = {
            200: "OK",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
        }.get(self.status_code, "Internal Server Error")

        response_line = f"HTTP/1.1 {self.status_code} {reason}\r\n"
        default_headers = {
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Connection": "close",
            "Server": "OtusPythonHTTP/1.0",
        }
        merged_headers = {**default_headers, **self.headers}
        if self.body is not None:
            merged_headers["Content-Length"] = str(len(self.body))
        elif "Content-Length" not in self.headers.keys():
            merged_headers["Content-Length"] = "0"

        header_lines = "".join(f"{k}: {v}\r\n" for k, v in merged_headers.items())
        return (response_line + header_lines + "\r\n").encode("utf-8") + (
            self.body or b""
        )
