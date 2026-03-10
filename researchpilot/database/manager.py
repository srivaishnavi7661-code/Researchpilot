"""
ResearchPilot - Database Manager
Handles all database operations with connection pooling and session management.
"""

from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Generator
from sqlalchemy import create_engine, or_, and_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from loguru import logger

from .models import Base, Paper, Collection, Tag, ResearchSession, SearchHistory, init_db


class DatabaseManager:
    """Central database manager for ResearchPilot."""

    def __init__(self, database_url: str = "sqlite:///./researchpilot.db"):
        self.engine = create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        logger.info(f"Database initialized: {database_url}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # ─── Paper Operations ───────────────────────────────────────────────────

    def save_paper(self, paper_data: dict) -> Paper:
        """Save or update a paper."""
        with self.get_session() as session:
            existing = session.query(Paper).filter_by(id=paper_data["id"]).first()
            if existing:
                for key, value in paper_data.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
                paper = existing
            else:
                paper = Paper(**{k: v for k, v in paper_data.items() if hasattr(Paper, k)})
                session.add(paper)
            session.flush()
            session.refresh(paper)
            return paper

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Get a paper by ID."""
        with self.get_session() as session:
            return session.query(Paper).filter_by(id=paper_id).first()

    def search_papers(
        self,
        query: str = "",
        collection_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        is_bookmarked: Optional[bool] = None,
        source: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Search papers with filters."""
        with self.get_session() as session:
            q = session.query(Paper)

            if query:
                search_term = f"%{query}%"
                q = q.filter(
                    or_(
                        Paper.title.ilike(search_term),
                        Paper.abstract.ilike(search_term),
                        Paper.ai_summary.ilike(search_term),
                    )
                )
            if collection_id:
                q = q.join(Paper.collections).filter(Collection.id == collection_id)
            if is_bookmarked is not None:
                q = q.filter(Paper.is_bookmarked == is_bookmarked)
            if source:
                q = q.filter(Paper.source == source)

            q = q.order_by(desc(Paper.created_at))
            papers = q.offset(offset).limit(limit).all()
            return [p.to_dict() for p in papers]

    def get_all_papers(self, limit: int = 100) -> List[dict]:
        """Get all papers."""
        with self.get_session() as session:
            papers = session.query(Paper).order_by(desc(Paper.created_at)).limit(limit).all()
            return [p.to_dict() for p in papers]

    def update_paper_ai_fields(self, paper_id: str, ai_data: dict) -> bool:
        """Update AI-generated fields for a paper."""
        with self.get_session() as session:
            paper = session.query(Paper).filter_by(id=paper_id).first()
            if not paper:
                return False
            for key, value in ai_data.items():
                if hasattr(paper, key):
                    setattr(paper, key, value)
            return True

    def update_paper_user_fields(self, paper_id: str, user_data: dict) -> bool:
        """Update user fields for a paper."""
        with self.get_session() as session:
            paper = session.query(Paper).filter_by(id=paper_id).first()
            if not paper:
                return False
            allowed = {"user_notes", "user_rating", "is_bookmarked", "is_read"}
            for key, value in user_data.items():
                if key in allowed:
                    setattr(paper, key, value)
            return True

    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper."""
        with self.get_session() as session:
            paper = session.query(Paper).filter_by(id=paper_id).first()
            if paper:
                session.delete(paper)
                return True
            return False

    # ─── Collection Operations ──────────────────────────────────────────────

    def create_collection(self, name: str, description: str = "", color: str = "#4A90E2") -> Collection:
        """Create a new collection."""
        with self.get_session() as session:
            collection = Collection(name=name, description=description, color=color)
            session.add(collection)
            session.flush()
            session.refresh(collection)
            return collection

    def get_collections(self) -> List[dict]:
        """Get all collections."""
        with self.get_session() as session:
            collections = session.query(Collection).all()
            return [c.to_dict() for c in collections]

    def add_paper_to_collection(self, paper_id: str, collection_id: int) -> bool:
        """Add a paper to a collection."""
        with self.get_session() as session:
            paper = session.query(Paper).filter_by(id=paper_id).first()
            collection = session.query(Collection).filter_by(id=collection_id).first()
            if paper and collection and collection not in paper.collections:
                paper.collections.append(collection)
                return True
            return False

    # ─── Session Operations ─────────────────────────────────────────────────

    def create_research_session(self, title: str = "New Research Session", collection_id: Optional[int] = None) -> ResearchSession:
        """Create a new research session."""
        with self.get_session() as session:
            rs = ResearchSession(title=title, collection_id=collection_id, messages=[], agent_actions=[])
            session.add(rs)
            session.flush()
            session.refresh(rs)
            return rs

    def get_research_session(self, session_id: int) -> Optional[dict]:
        """Get a research session with messages."""
        with self.get_session() as session:
            rs = session.query(ResearchSession).filter_by(id=session_id).first()
            if not rs:
                return None
            return {
                "id": rs.id,
                "title": rs.title,
                "messages": rs.messages or [],
                "agent_actions": rs.agent_actions or [],
                "context_paper_ids": rs.context_paper_ids or [],
                "created_at": rs.created_at.isoformat() if rs.created_at else None,
            }

    def update_research_session(self, session_id: int, messages: list, agent_actions: list = None) -> bool:
        """Update session messages."""
        with self.get_session() as session:
            rs = session.query(ResearchSession).filter_by(id=session_id).first()
            if not rs:
                return False
            rs.messages = messages
            if agent_actions is not None:
                rs.agent_actions = agent_actions
            return True

    def get_all_sessions(self) -> List[dict]:
        """Get all research sessions."""
        with self.get_session() as session:
            sessions = session.query(ResearchSession).order_by(desc(ResearchSession.updated_at)).all()
            return [s.to_dict() for s in sessions]

    def log_search(self, query: str, source: str, result_count: int, filters: dict = None):
        """Log a search query."""
        with self.get_session() as session:
            history = SearchHistory(
                query=query,
                source=source,
                result_count=result_count,
                filters=filters or {}
            )
            session.add(history)

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.get_session() as session:
            return {
                "total_papers": session.query(Paper).count(),
                "bookmarked_papers": session.query(Paper).filter_by(is_bookmarked=True).count(),
                "read_papers": session.query(Paper).filter_by(is_read=True).count(),
                "total_collections": session.query(Collection).count(),
                "total_sessions": session.query(ResearchSession).count(),
                "papers_with_ai_summary": session.query(Paper).filter(Paper.ai_summary.isnot(None)).count(),
            }
