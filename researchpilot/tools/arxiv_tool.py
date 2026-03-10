"""
ResearchPilot - ArXiv Search Tool
Searches and fetches papers from arXiv.org.
"""

import arxiv
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger


class ArXivTool:
    """Tool for searching and fetching papers from arXiv."""

    def __init__(self, max_results: int = 20):
        self.max_results = max_results
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=3
        )

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        categories: Optional[List[str]] = None,
        sort_by: str = "relevance",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv for papers.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            categories: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
            sort_by: 'relevance', 'lastUpdatedDate', 'submittedDate'
            date_from: ISO date string for start of date range
            date_to: ISO date string for end of date range
        
        Returns:
            List of paper dictionaries
        """
        max_results = max_results or self.max_results
        
        # Build query with category filters
        search_query = query
        if categories:
            cat_filter = " OR ".join([f"cat:{c}" for c in categories])
            search_query = f"({query}) AND ({cat_filter})"

        # Map sort options
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
        }
        sort_criterion = sort_map.get(sort_by, arxiv.SortCriterion.Relevance)

        try:
            search = arxiv.Search(
                query=search_query,
                max_results=max_results,
                sort_by=sort_criterion,
            )
            
            results = []
            for result in self.client.results(search):
                paper = self._result_to_dict(result)
                
                # Filter by date if specified
                if date_from and paper["published_date"]:
                    pub_date = datetime.fromisoformat(paper["published_date"].replace("Z", ""))
                    from_date = datetime.fromisoformat(date_from)
                    if pub_date < from_date:
                        continue
                
                results.append(paper)
            
            logger.info(f"ArXiv search '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return []

    def get_paper(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific paper by arXiv ID."""
        # Clean ID (remove version suffix for search)
        clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        
        try:
            search = arxiv.Search(id_list=[clean_id])
            results = list(self.client.results(search))
            if results:
                return self._result_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Failed to fetch arXiv paper {arxiv_id}: {e}")
            return None

    def _result_to_dict(self, result: arxiv.Result) -> Dict[str, Any]:
        """Convert arxiv.Result to our standard paper dict."""
        arxiv_id = result.get_short_id()
        
        return {
            "id": f"arxiv:{arxiv_id}",
            "arxiv_id": arxiv_id,
            "title": result.title,
            "abstract": result.summary,
            "authors": [str(a) for a in result.authors],
            "published_date": result.published.isoformat() if result.published else None,
            "updated_date": result.updated.isoformat() if result.updated else None,
            "source": "arxiv",
            "source_url": result.entry_id,
            "pdf_url": result.pdf_url,
            "doi": result.doi,
            "categories": result.categories,
            "keywords": [],
            "citation_count": 0,
        }

    def get_recent_papers(self, category: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent papers in a category."""
        return self.search(
            query=f"cat:{category}",
            max_results=max_results,
            sort_by="submittedDate"
        )

    def get_related_papers(self, title: str, abstract: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Find papers related to a given paper based on title and abstract keywords."""
        # Extract key terms from title (simple approach)
        words = title.split()
        key_terms = [w for w in words if len(w) > 4][:5]
        query = " ".join(key_terms)
        return self.search(query=query, max_results=max_results)
