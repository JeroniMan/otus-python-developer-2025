.PHONY: http-test-suite http-test-suite-run stop-server

ROOT_DIR := $(shell pwd)
DOCS_DIR := $(ROOT_DIR)/http-test-suite

PORT := 80

test:
	poetry run pytest tests

server:
	$(PYTHON) $(SERVER) -r $(DOCUMENT_ROOT)

http-test-suite:
	@if [ ! -d http-test-suite ]; then git clone https://github.com/s-stupnikov/http-test-suite.git; fi
	cd http-test-suite && poetry install --no-root

http-test-suite-run:
	poetry run start /B python webserver_src/httpd.py -p 80 -r http-test-suite
	timeout /T 2 > nul
	cd http-test-suite && poetry run python httptest.py

stop-server:
	@echo "Stopping server on port 80..."
ifeq ($(OS),Windows_NT)
	@for /f "tokens=5" %%a in ('netstat -aon ^| findstr :80') do taskkill /F /PID %%a > nul 2>&1 || exit 0
else
	@lsof -ti tcp:80 | xargs -r kill -9
endif


http-test-suite-run-console:
	poetry run python webserver_src/httpd.py -r $(DOCS_DIR) -p $(PORT) & \
	echo $$! > .server.pid; \
	sleep 1; \
	cd http-test-suite && poetry run python httptest.py

stop-server-console:
	-@if [ -f .server.pid ]; then \
		kill `cat .server.pid`; \
		rm .server.pid; \
		echo "Server stopped."; \
	else \
		echo "No server running."; \
	fi

stress:
	@echo Starting HTTP server...
	start /B poetry run python webserver_src/httpd.py -r documents -p 8080
	timeout /T 3 > NUL
	echo Running benchmark...
	ab -n 50000 -c 100 -r http://localhost:8080/ > result.txt
	echo Benchmark complete.
	for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do taskkill /PID %%a /F > NUL
