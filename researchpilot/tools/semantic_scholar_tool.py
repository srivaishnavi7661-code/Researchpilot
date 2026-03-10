"""
ResearchPilot - Semantic Scholar Tool
Fetches papers and citation data from Semantic Scholar API.
"""

import httpx
import time
from typing import List, Optional, Dict, Any
from loguru import logger


SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"

PAPER_FIELDS = (
    "paperId,title,abstract,authors,year,publicationDate,"
    "externalIds,url,openAccessPdf,fieldsOfStudy,"
    "citationCount,influentialCitationCount,references,citations,"
    "publicationTypes,journal"
)


class SemanticScholarTool:
    """Tool for searching papers and fetching citation data from Semantic Scholar."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key
        self.client = httpx.Client(timeout=30, headers=self.headers)

    def search(
        self,
        query: str,
        limit: int = 20,
        fields_of_study: Optional[List[str]] = None,
        year_range: Optional[str] = None,  # e.g., "2020-2024"
        open_access_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for papers."""
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": PAPER_FIELDS,
        }
        
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        if year_range:
            params["year"] = year_range
        if open_access_only:
            params["openAccessPdf"] = ""

        try:
            response = self.client.get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            papers = [self._paper_to_dict(p) for p in data.get("data", [])]
            logger.info(f"Semantic Scholar search '{query}' returned {len(papers)} results")
            return papers
        except httpx.HTTPError as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific paper by Semantic Scholar ID, DOI, or arXiv ID."""
        try:
            response = self.client.get(
                f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}",
                params={"fields": PAPER_FIELDS}
            )
            response.raise_for_status()
            return self._paper_to_dict(response.json())
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch paper {paper_id}: {e}")
            return None

    def get_citations(self, paper_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get papers that cite a given paper."""
        try:
            response = self.client.get(
                f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}/citations",
                params={"fields": "paperId,title,authors,year,citationCount", "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return [self._paper_to_dict(item.get("citingPaper", {})) for item in data.get("data", [])]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch citations for {paper_id}: {e}")
            return []

    def get_references(self, paper_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get papers referenced by a given paper."""
        try:
            response = self.client.get(
                f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}/references",
                params={"fields": "paperId,title,authors,year,citationCount", "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return [self._paper_to_dict(item.get("citedPaper", {})) for item in data.get("data", [])]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch references for {paper_id}: {e}")
            return []

    def get_author_papers(self, author_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get papers by a specific author."""
        try:
            response = self.client.get(
                f"{SEMANTIC_SCHOLAR_BASE}/author/{author_id}/papers",
                params={"fields": PAPER_FIELDS, "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return [self._paper_to_dict(p) for p in data.get("data", [])]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch author papers: {e}")
            return []

    def _paper_to_dict(self, paper: dict) -> Dict[str, Any]:
        """Convert Semantic Scholar paper to standard format."""
        if not paper:
            return {}
        
        # Extract IDs
        external_ids = paper.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv")
        doi = external_ids.get("DOI")
        
        paper_id = paper.get("paperId", "")
        
        # Use arxiv ID if available for consistency
        our_id = f"arxiv:{arxiv_id}" if arxiv_id else f"ss:{paper_id}"
        
        # Extract PDF URL
        pdf_info = paper.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url")
        
        # Extract authors
        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        
        # Parse date
        pub_date = paper.get("publicationDate")
        if not pub_date and paper.get("year"):
            pub_date = f"{paper['year']}-01-01"
        
        return {
            "id": our_id,
            "arxiv_id": arxiv_id,
            "doi": doi,
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "authors": authors,
            "published_date": pub_date,
            "source": "semantic_scholar",
            "source_url": paper.get("url", ""),
            "pdf_url": pdf_url,
            "categories": paper.get("fieldsOfStudy") or [],
            "keywords": [],
            "citation_count": paper.get("citationCount", 0),
            "semantic_scholar_id": paper_id,
        }

    def __del__(self):
        try:
            self.client.close()
        except Exception:
            pass
