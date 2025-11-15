import subprocess
import time
import os

def run_in_terminal(title, command):
    if os.name == 'nt':  # Windows
        full_cmd = f'start "{title}" cmd /k "{command}"'
        subprocess.Popen(full_cmd, shell=True)
    else:  # Linux/Mac
        subprocess.Popen(['xterm', '-T', title, '-e', command])

services = [
    ("App", "python run.py"),
    ("Auth_Service", "python auth_service.py"),
    ("Orders_Service", "python orders_service.py"),
    ("Gateway_Service", "python gateway.py"),
]

print("Lancement des services...")

for name, cmd in services:
    run_in_terminal(name, cmd)
    time.sleep(0.3)

print("Tous les microservices sont lancés.")
