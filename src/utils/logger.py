import os
import logging
from logging.handlers import RotatingFileHandler

def setup_global_logger(name: str = "graphone-pipeline", log_file: str = "data/output/pipeline.log") -> logging.Logger:
    """
    Initializes a multi-handler root tracking logger.
    Streams debug details to terminal consoles and stores tracking summaries on disk.
    """
    # Safeguard directory path creation before mounting file streams
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicating log handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # 1. Establish common structural layout format
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 2. Configure Stream Handler for real-time terminal evaluation
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 3. Configure Disk Handler with rotating constraints to manage log file size
    try:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5 * 1024 * 1024,  # Roll over file size at 5MB limits
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to establish local file log streams: {e}")

    return logger
