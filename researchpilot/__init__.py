"""
ResearchPilot AI Agent - Autonomous Research Intelligence Hub
"""

__version__ = "1.0.0"
__author__ = "ResearchPilot Team"
__description__ = "Autonomous Research Intelligence Hub powered by Claude AI"

from .database.manager import DatabaseManager
from .tools.arxiv_tool import ArXivTool
from .tools.semantic_scholar_tool import SemanticScholarTool
from .tools.vector_store import VectorStore
from .agents.research_agent import ResearchAgent

__all__ = [
    "DatabaseManager",
    "ArXivTool", 
    "SemanticScholarTool",
    "VectorStore",
    "ResearchAgent",
]
