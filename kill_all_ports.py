import subprocess

# List of ports to free
ports = [8000, 8001, 8002, 8003, 8004]

for port in ports:
    try:
        # Find the process ID using the port
        pid_output = subprocess.check_output(f"lsof -ti:{port}", shell=True).decode().strip()
        if pid_output:
            print(f"Killing process on port {port}: PID {pid_output}")
            subprocess.call(f"kill -9 {pid_output}", shell=True)
        else:
            print(f"No process found on port {port}")
    except subprocess.CalledProcessError:
        print(f"Error checking port {port} (likely no process running).")