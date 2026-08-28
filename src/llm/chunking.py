import logging
from typing import List

logger = logging.getLogger("graphone-pipeline.chunking")

def chunk_text_by_words(text: str, max_words: int = 1500, overlap: int = 150) -> List[str]:
    """
    Splits long strings into smaller text blocks based on a strict word count.
    Includes a sliding window overlap to keep context intact across boundaries.
    """
    if not text or max_words <= 0:
        return []

    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    
    while start < len(words):
        end = start + max_words
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        
        # Advance the pointer, adjusting for overlap
        start += (max_words - overlap)
        if start >= len(words) or (end >= len(words)):
            break
            
    logger.info(f"Segmented raw text into {len(chunks)} contextual blocks.")
    return chunks
