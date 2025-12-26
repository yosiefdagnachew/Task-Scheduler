#!/usr/bin/env python3
"""Start Uvicorn programmatically and log startup/shutdown for diagnosis.

Creates `uvicorn_capture.log` in the project root with INFO/DEBUG output.
"""
from dotenv import load_dotenv
load_dotenv()
import logging
import sys
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("uvicorn_capture.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("uvicorn_capture")

def main():
    try:
        import uvicorn
        logger.info("Starting Uvicorn programmatically...")
        # Use same import path as runserver: task_scheduler.api:app
        uvicorn.run("task_scheduler.api:app", host="127.0.0.1", port=8000, log_level="debug")
    except Exception as e:
        logger.exception("Uvicorn failed to start: %s", e)

if __name__ == '__main__':
    main()
