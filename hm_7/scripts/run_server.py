import os
import subprocess

with open(".server.pid", "w") as f:
    proc = subprocess.Popen(["python", "src/httpd.py", "-r", "docs"])
    f.write(str(proc.pid))
