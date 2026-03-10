"""
ResearchPilot - Database Models
SQLAlchemy ORM models for papers, collections, and research sessions.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime,
    Boolean, ForeignKey, Table, JSON, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from sqlalchemy.sql import func
import json


class Base(DeclarativeBase):
    pass


# Association table for paper-collection many-to-many
paper_collection = Table(
    "paper_collection",
    Base.metadata,
    Column("paper_id", String, ForeignKey("papers.id"), primary_key=True),
    Column("collection_id", Integer, ForeignKey("collections.id"), primary_key=True),
)

# Association table for paper tags
paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", String, ForeignKey("papers.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Paper(Base):
    """Academic paper model."""
    __tablename__ = "papers"

    id = Column(String, primary_key=True)  # arxiv_id or doi
    title = Column(String(500), nullable=False)
    abstract = Column(Text)
    authors = Column(JSON)  # List of author names
    published_date = Column(DateTime)
    updated_date = Column(DateTime)
    source = Column(String(50))  # 'arxiv', 'semantic_scholar', 'crossref', 'manual'
    source_url = Column(String(500))
    pdf_url = Column(String(500))
    doi = Column(String(200))
    arxiv_id = Column(String(50))
    categories = Column(JSON)  # List of categories/subjects
    keywords = Column(JSON)  # Extracted keywords
    citation_count = Column(Integer, default=0)
    
    # AI-generated fields
    ai_summary = Column(Text)  # Claude-generated summary
    ai_key_contributions = Column(JSON)  # List of key contributions
    ai_methodology = Column(Text)  # Methodology summary
    ai_limitations = Column(Text)  # Limitations identified
    ai_relevance_score = Column(Float)  # 0-1 relevance score
    ai_tags = Column(JSON)  # AI-generated tags
    
    # User fields
    user_notes = Column(Text)
    user_rating = Column(Integer)  # 1-5
    is_bookmarked = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    
    # Vector embedding stored externally (FAISS)
    embedding_id = Column(Integer)  # Index in FAISS store
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    collections = relationship("Collection", secondary=paper_collection, back_populates="papers")
    tags = relationship("Tag", secondary=paper_tags, back_populates="papers")
    citations = relationship("Citation", foreign_keys="Citation.citing_paper_id", back_populates="citing_paper")
    cited_by = relationship("Citation", foreign_keys="Citation.cited_paper_id", back_populates="cited_paper")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors or [],
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "source": self.source,
            "source_url": self.source_url,
            "pdf_url": self.pdf_url,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "categories": self.categories or [],
            "keywords": self.keywords or [],
            "citation_count": self.citation_count,
            "ai_summary": self.ai_summary,
            "ai_key_contributions": self.ai_key_contributions or [],
            "ai_tags": self.ai_tags or [],
            "user_rating": self.user_rating,
            "is_bookmarked": self.is_bookmarked,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Collection(Base):
    """Research collection/folder model."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    color = Column(String(20), default="#4A90E2")
    icon = Column(String(50), default="folder")
    is_public = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    papers = relationship("Paper", secondary=paper_collection, back_populates="collections")
    research_sessions = relationship("ResearchSession", back_populates="collection")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "paper_count": len(self.papers),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Tag(Base):
    """Tag model for organizing papers."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(20), default="#6B7280")
    
    papers = relationship("Paper", secondary=paper_tags, back_populates="tags")


class Citation(Base):
    """Citation relationship between papers."""
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    citing_paper_id = Column(String, ForeignKey("papers.id"))
    cited_paper_id = Column(String, ForeignKey("papers.id"))
    
    citing_paper = relationship("Paper", foreign_keys=[citing_paper_id], back_populates="citations")
    cited_paper = relationship("Paper", foreign_keys=[cited_paper_id], back_populates="cited_by")


class ResearchSession(Base):
    """AI research conversation session."""
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300))
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    
    messages = Column(JSON, default=list)  # List of {role, content, timestamp}
    context_paper_ids = Column(JSON, default=list)  # Papers referenced in session
    agent_actions = Column(JSON, default=list)  # Tool calls made by agent
    
    total_tokens_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    collection = relationship("Collection", back_populates="research_sessions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message_count": len(self.messages or []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SearchHistory(Base):
    """Search query history."""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500))
    source = Column(String(50))
    result_count = Column(Integer)
    filters = Column(JSON)
    
    created_at = Column(DateTime, default=func.now())


def init_db(database_url: str = "sqlite:///./researchpilot.db") -> None:
    """Initialize the database and create all tables."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine
