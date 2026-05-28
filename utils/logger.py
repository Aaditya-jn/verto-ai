# utils/logger.py
import os
import logging

os.makedirs("logs", exist_ok=True)

# Configure the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Avoid adding duplicate handlers if the logger is imported/loaded multiple times
if not root_logger.handlers:
    # File handler
    file_handler = logging.FileHandler("logs/activity.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Console/Terminal handler with exactly the requested format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

# Export standard logger
logger = logging.getLogger("__main__")

def log(event: str, phone: str, data: str = ""):
    logger.info(f"[{phone}] {event} | {data[:200]}")
