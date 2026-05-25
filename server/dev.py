# -*- coding: utf-8 -*-

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WATCHED_FILES = [ROOT / "proxy.py"]


def main():
    process = None
    last_signature = None
    try:
        while True:
            signature = get_signature()
            if process is None:
                process = start_proxy()
                last_signature = signature
            elif signature != last_signature:
                print("Detected server file change, restarting proxy...", flush=True)
                stop_proxy(process)
                process = start_proxy()
                last_signature = signature

            if process.poll() is not None:
                print("Proxy stopped. Restarting in 1s...", flush=True)
                time.sleep(1)
                process = start_proxy()
                last_signature = get_signature()

            time.sleep(0.8)
    except KeyboardInterrupt:
        print("\nStopping dev proxy...", flush=True)
    finally:
        if process is not None:
            stop_proxy(process)


def start_proxy():
    print("Starting proxy with auto-reload on http://127.0.0.1:8787", flush=True)
    return subprocess.Popen([sys.executable, str(ROOT / "proxy.py")], cwd=str(ROOT.parent))


def stop_proxy(process):
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


def get_signature():
    parts = []
    for path in WATCHED_FILES:
        try:
            stat = path.stat()
        except FileNotFoundError:
            parts.append((str(path), 0, 0))
            continue
        parts.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(parts)


if __name__ == "__main__":
    main()
