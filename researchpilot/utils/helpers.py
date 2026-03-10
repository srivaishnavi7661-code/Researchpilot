"""
ResearchPilot - Utility Functions
Helper functions used across the application.
"""

import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def truncate_text(text: str, max_length: int = 500, ellipsis: str = "...") -> str:
    """Truncate text to a maximum length."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis


def extract_arxiv_id(url_or_id: str) -> Optional[str]:
    """Extract arXiv ID from a URL or ID string."""
    patterns = [
        r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)',
        r'arxiv\.org/pdf/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)',
        r'^([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)$',
        r'^arxiv:([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


def format_authors(authors: List[str], max_authors: int = 3) -> str:
    """Format author list for display."""
    if not authors:
        return "Unknown Authors"
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + f" et al. (+{len(authors) - max_authors})"


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt)
        except (ValueError, TypeError):
            continue
    return None


def generate_paper_id(title: str, authors: List[str]) -> str:
    """Generate a unique ID for a paper from title and authors."""
    key = f"{title.lower()}{''.join(sorted(authors))}"
    return f"manual:{hashlib.md5(key.encode()).hexdigest()[:12]}"


def estimate_read_time(text: str, wpm: int = 200) -> int:
    """Estimate reading time in minutes."""
    words = len(text.split()) if text else 0
    return max(1, round(words / wpm))


def format_citation_count(count: int) -> str:
    """Format citation count for display."""
    if count >= 1000:
        return f"{count/1000:.1f}k"
    return str(count)


def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate papers based on title similarity."""
    seen_titles = set()
    unique = []
    for paper in papers:
        title_key = re.sub(r'[^a-z0-9]', '', paper.get("title", "").lower())
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(paper)
    return unique


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for processing."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limit."""
        import time
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
