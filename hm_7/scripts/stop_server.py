import os
import signal

try:
    with open(".server.pid") as f:
        pid = int(f.read().strip())
    os.kill(pid, signal.SIGTERM)
    print(f"Server with PID {pid} stopped.")
except Exception as e:
    print(f"Failed to stop server: {e}")
