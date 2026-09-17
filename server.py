# server.py

import subprocess
import sys
import time

def main():
    print("starting backend (fastapi)...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    )

    # give the backend a couple seconds to actually start before the ui tries to call it
    time.sleep(3)

    print("starting frontend (streamlit)...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/ui.py"]
    )

    try:
        # just wait here so the script doesn't exit immediately
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nshutting down...")
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()