import json
import os
import logging
from typing import List, Dict, Optional, Set

logger = logging.getLogger("graphone-pipeline.entity_resolution")

class EntityResolver:
    def __init__(self, seed_path: str = "src/entity_resolution/canonical_seed.json"):
        self.seed_path = seed_path
        self.canonical_companies = self._load_canonical_seed()

    def _load_canonical_seed(self) -> List[str]:
        """Loads the baseline dictionary matrix of company names."""
        if not os.path.exists(self.seed_path):
            logger.warning(f"Seed matrix not found at {self.seed_path}. Initializing with empty baseline.")
            return []
        try:
            with open(self.seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Assumes JSON structure is a list of strings or an object with a 'startups' list
                if isinstance(data, list):
                    return [str(item).strip() for item in data]
                elif isinstance(data, dict) and "startups" in data:
                    return [str(item).strip() for item in data["startups"]]
                return []
        except Exception as e:
            logger.error(f"Failed to read canonical seed matrix file: {e}")
            return []

    def _tokenize_and_normalize(self, text: str) -> Set[str]:
        """Cleans text into uniform lowercase alphanumeric token parts."""
        clean_text = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in text)
        # Skip noise words commonly found in corporate scraping records
        noise_words = {"inc", "corp", "llc", "co", "ltd", "gmbh", "incorporated", "limited", "the", "and"}
        return {word for word in clean_text.split() if word and word not in noise_words}

    def calculate_jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Computes the Jaccard intersecting token overlap between two strings."""
        tokens_a = self._tokenize_and_normalize(text_a)
        tokens_b = self._tokenize_and_normalize(text_b)
        
        if not tokens_a or not tokens_b:
            return 0.0
            
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union)

    def resolve_company(self, scraped_name: str, threshold: float = 0.6) -> str:
        """
        Maps a scraped identity text to the best matching canonical baseline matrix string.
        If no match passes the similarity threshold metric, returns the original string.
        """
        if not scraped_name:
            return ""

        best_match: Optional[str] = None
        highest_score = 0.0

        for canonical_name in self.canonical_companies:
            # Direct exact match check after basic whitespace cleaning
            if scraped_name.strip().lower() == canonical_name.lower():
                return canonical_name

            # Calculate token intersection score
            score = self.calculate_jaccard_similarity(scraped_name, canonical_name)
            if score > highest_score:
                highest_score = score
                best_match = canonical_name

        if highest_score >= threshold and best_match:
            logger.info(f"Resolved entity: '{scraped_name}' -> '{best_match}' (Score: {highest_score:.2f})")
            return best_match

        logger.debug(f"No match for entity '{scraped_name}'. Retaining original name.")
        return scraped_name.strip()
