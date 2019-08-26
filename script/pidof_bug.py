import subprocess
import os
os.setgid(1000)
os.setuid(1000)
subprocess.Popen('chromium-browser')