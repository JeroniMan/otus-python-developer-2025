import http.client
import multiprocessing
import os
import time
from types import SimpleNamespace

from handler.handler import EmptyHandler
from webserver_src.httpd import start_worker

SERVER_PORT = 8080


def start_server():
    os.environ["DOCUMENT_ROOT"] = os.path.abspath("docs")
    args = SimpleNamespace(upload_timeout=100, host="127.0.0.1", port=SERVER_PORT)
    start_worker(EmptyHandler(b"TEST RESPONSE"), args)


def setup_module(module):
    global server_process
    server_process = multiprocessing.Process(target=start_server)
    server_process.start()
    time.sleep(1)


def teardown_module(module):
    server_process.terminate()
    server_process.join()


def test_server_root_returns_index():
    conn = http.client.HTTPConnection("localhost", SERVER_PORT)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    body = resp.read()
    assert b"TEST RESPONSE" in body
