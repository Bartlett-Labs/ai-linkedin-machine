"""
Content deduplication.

Prevents near-duplicate posts from being queued when multiple RSS sources
cover the same story. Uses simple token overlap similarity.
"""

import logging
import os
import re
from pathlib import Path

from utils import project_path

logger = logging.getLogger(__name__)

POSTS_DIR = project_path("queue", "posts")
SIMILARITY_THRESHOLD = 0.55  # 55% token overlap = likely duplicate


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text (lowercase, no stopwords)."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "must", "can", "could", "in", "on", "at",
        "to", "for", "of", "with", "by", "from", "as", "into", "through",
        "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "this", "that", "these", "those", "it", "its", "i", "we",
        "you", "he", "she", "they", "me", "him", "her", "us", "them", "my",
        "your", "his", "our", "their", "what", "which", "who", "whom",
    }
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return set(words) - stopwords


def _similarity(text_a: str, text_b: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)


def is_duplicate(
    new_content: str,
    existing_dir: str = POSTS_DIR,
    threshold: float = SIMILARITY_THRESHOLD,
) -> bool:
    """Check if new content is too similar to any existing queued post.

    Args:
        new_content: The text of the post to check.
        existing_dir: Directory containing existing post files.
        threshold: Similarity score above which content is considered duplicate.

    Returns:
        True if a near-duplicate exists.
    """
    posts_path = Path(existing_dir)
    if not posts_path.exists():
        return False

    for post_file in posts_path.glob("*_post.txt"):
        try:
            existing = post_file.read_text().strip()
            score = _similarity(new_content, existing)
            if score >= threshold:
                logger.info(
                    "Duplicate detected (%.0f%% similar to %s)",
                    score * 100, post_file.name,
                )
                return True
        except Exception:
            continue

    return False


def deduplicate_queue(directory: str = POSTS_DIR) -> int:
    """Remove duplicate posts from the queue directory.

    Keeps the oldest file when duplicates are found.
    Returns the number of duplicates removed.
    """
    posts_path = Path(directory)
    if not posts_path.exists():
        return 0

    files = sorted(posts_path.glob("*_post.txt"))  # Oldest first
    removed = 0
    kept_texts = []

    for post_file in files:
        try:
            text = post_file.read_text().strip()
            is_dup = False
            for kept in kept_texts:
                if _similarity(text, kept) >= SIMILARITY_THRESHOLD:
                    is_dup = True
                    break

            if is_dup:
                dup_dir = posts_path / "duplicates"
                dup_dir.mkdir(exist_ok=True)
                post_file.rename(dup_dir / post_file.name)
                removed += 1
                logger.info("Moved duplicate to duplicates/: %s", post_file.name)
            else:
                kept_texts.append(text)
        except Exception:
            continue

    if removed:
        logger.info("Deduplication complete: %d duplicates removed", removed)
    return removed
