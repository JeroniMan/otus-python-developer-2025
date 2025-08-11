from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class HTTPRequest:
    src: str
    method: str
    path: str
    params: Dict[str, str]
    version: str
    headers: Dict[str, str]
    body: Optional[bytes]
