import os
import json
import logging
from threading import Lock
from typing import Set

logger = logging.getLogger("graphone-pipeline.utils.dedupe_store")

class URLDedupeStore:
    def __init__(self, storage_path: str = "data/output/seen_urls.json"):
        self.storage_path = storage_path
        self._lock = Lock()  # Prevents thread collisions if scrapers run concurrently
        self.seen_urls: Set[str] = self._load_store()

    def _load_store(self) -> Set[str]:
        """Loads historically processed URLs from the disk into memory."""
        if not os.path.exists(self.storage_path):
            return set()
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.error(f"Failed to read deduplication storage file: {e}")
        return set()

    def _save_store(self):
        """Flushes the updated in-memory list of tracked URLs back to disk."""
        try:
            # Ensure the directory structure exists before writing the file
            dir_name = os.path.dirname(self.storage_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_urls), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to flush tracking changes to storage file: {e}")

    def is_new(self, url: str) -> bool:
        """
        Evaluates a URL. If it hasn't been crawled, tracks it and returns True.
        If it has already been processed historically, skips it and returns False.
        """
        if not url:
            return False
            
        url_cleaned = url.strip().lower()
        
        with self._lock:
            if url_cleaned in self.seen_urls:
                logger.debug(f"Target URL already processed. Skipping extraction: {url}")
                return False
                
            self.seen_urls.add(url_cleaned)
            self._save_store()
            logger.info(f"Registered brand new url asset into freshness registry: {url}")
            return True

    def clear(self):
        """Resets the state storage memory block entirely."""
        with self._lock:
            self.seen_urls.clear()
            self._save_store()
            logger.warning("Flushed freshness cache directory cleanly.")
