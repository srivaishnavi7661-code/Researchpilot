"""
ResearchPilot - FastAPI REST API Server
Complete REST API for the ResearchPilot application.
"""

import os
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from ..database.manager import DatabaseManager
from ..tools.arxiv_tool import ArXivTool
from ..tools.semantic_scholar_tool import SemanticScholarTool
from ..tools.vector_store import VectorStore
from ..agents.research_agent import ResearchAgent


# ─── Global State ─────────────────────────────────────────────────────────────

db: DatabaseManager = None
vector_store: VectorStore = None
arxiv_tool: ArXivTool = None
ss_tool: SemanticScholarTool = None
agent: ResearchAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, vector_store, arxiv_tool, ss_tool, agent
    
    logger.info("Starting ResearchPilot API...")
    
    db = DatabaseManager(os.getenv("DATABASE_URL", "sqlite:///./researchpilot.db"))
    vector_store = VectorStore(
        store_path=os.getenv("VECTOR_STORE_PATH", "./data/vector_store"),
        model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    arxiv_tool = ArXivTool(max_results=int(os.getenv("ARXIV_MAX_RESULTS", "50")))
    ss_tool = SemanticScholarTool(api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
    agent = ResearchAgent(
        db=db,
        vector_store=vector_store,
        arxiv_tool=arxiv_tool,
        ss_tool=ss_tool,
        model=os.getenv("AGENT_MODEL", "gemini-1.5-pro"),
        max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
    )
    
    logger.info("ResearchPilot API started successfully")
    yield
    logger.info("ResearchPilot API shutting down")


app = FastAPI(
    title="ResearchPilot AI API",
    description="Autonomous Research Intelligence Hub - REST API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[int] = Field(None, description="Existing session ID")
    history: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history")


class ChatResponse(BaseModel):
    response: str
    session_id: int
    tool_calls: List[Dict] = []
    updated_history: List[Dict] = []


class SavePaperRequest(BaseModel):
    paper_data: Dict[str, Any]
    collection_id: Optional[int] = None
    generate_summary: bool = True


class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""
    color: str = "#4A90E2"


class UpdatePaperRequest(BaseModel):
    user_notes: Optional[str] = None
    user_rating: Optional[int] = None
    is_bookmarked: Optional[bool] = None
    is_read: Optional[bool] = None


class SearchRequest(BaseModel):
    query: str
    source: str = "arxiv"  # arxiv, semantic_scholar, library
    max_results: int = 10
    categories: Optional[List[str]] = None
    year_range: Optional[str] = None


# ─── Routes: Chat / Agent ─────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """Send a message to the ResearchPilot AI agent."""
    # Get or create session
    if request.session_id:
        session_data = db.get_research_session(request.session_id)
        history = session_data.get("messages", []) if session_data else []
        session_id = request.session_id
    else:
        session = db.create_research_session()
        history = []
        session_id = session.id
    
    # Use provided history if given
    if request.history is not None:
        history = request.history
    
    result = agent.chat(
        user_message=request.message,
        conversation_history=history,
        session_id=session_id,
    )
    
    # Update session title if first message
    if not history and result.get("response"):
        title = request.message[:100]
        with db.get_session() as s:
            from ..database.models import ResearchSession
            rs = s.query(ResearchSession).filter_by(id=session_id).first()
            if rs:
                rs.title = title
    
    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        tool_calls=result.get("tool_calls", []),
        updated_history=result.get("updated_history", []),
    )


# ─── Routes: Papers ───────────────────────────────────────────────────────────

@app.get("/api/papers")
async def get_papers(
    query: str = Query("", description="Search query"),
    collection_id: Optional[int] = Query(None),
    is_bookmarked: Optional[bool] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """Get papers from the library with optional filters."""
    if query:
        papers = db.search_papers(
            query=query,
            collection_id=collection_id,
            is_bookmarked=is_bookmarked,
            source=source,
            limit=limit,
            offset=offset,
        )
    else:
        papers = db.get_all_papers(limit=limit)
    return {"papers": papers, "count": len(papers)}


@app.get("/api/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get a specific paper by ID."""
    paper = db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper.to_dict() if hasattr(paper, 'to_dict') else paper


@app.post("/api/papers")
async def save_paper(request: SavePaperRequest, background_tasks: BackgroundTasks):
    """Save a paper to the library."""
    paper = db.save_paper(request.paper_data)
    
    # Add to vector store in background
    if vector_store.is_available:
        background_tasks.add_task(
            vector_store.add_paper,
            paper_id=request.paper_data["id"],
            title=request.paper_data.get("title", ""),
            abstract=request.paper_data.get("abstract", ""),
        )
    
    if request.collection_id:
        db.add_paper_to_collection(request.paper_data["id"], request.collection_id)
    
    return {"success": True, "paper_id": request.paper_data["id"]}


@app.patch("/api/papers/{paper_id}")
async def update_paper(paper_id: str, request: UpdatePaperRequest):
    """Update user fields for a paper."""
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    success = db.update_paper_user_fields(paper_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"success": True}


@app.delete("/api/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a paper from the library."""
    success = db.delete_paper(paper_id)
    if success:
        vector_store.remove_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"success": True}


@app.post("/api/papers/{paper_id}/summarize")
async def generate_summary(paper_id: str):
    """Generate or regenerate AI summary for a paper."""
    paper = db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    paper_dict = paper.to_dict() if hasattr(paper, 'to_dict') else paper
    summary_data = agent._generate_paper_summary(paper_dict)
    
    if summary_data:
        db.update_paper_ai_fields(paper_id, summary_data)
        return {"success": True, **summary_data}
    
    raise HTTPException(status_code=500, detail="Failed to generate summary")


# ─── Routes: Search ───────────────────────────────────────────────────────────

@app.post("/api/search/arxiv")
async def search_arxiv(request: SearchRequest):
    """Search arXiv for papers."""
    papers = arxiv_tool.search(
        query=request.query,
        max_results=request.max_results,
        categories=request.categories,
    )
    db.log_search(request.query, "arxiv", len(papers))
    return {"papers": papers, "count": len(papers), "source": "arxiv"}


@app.post("/api/search/semantic-scholar")
async def search_semantic_scholar(request: SearchRequest):
    """Search Semantic Scholar for papers."""
    papers = ss_tool.search(
        query=request.query,
        limit=request.max_results,
        year_range=request.year_range,
    )
    db.log_search(request.query, "semantic_scholar", len(papers))
    return {"papers": papers, "count": len(papers), "source": "semantic_scholar"}


@app.post("/api/search/semantic")
async def semantic_library_search(request: SearchRequest):
    """Semantic similarity search within the library."""
    if vector_store.is_available:
        similar = vector_store.search(request.query, k=request.max_results)
        papers = []
        for paper_id, score in similar:
            p = db.get_paper(paper_id)
            if p:
                pd = p.to_dict() if hasattr(p, 'to_dict') else p
                pd["similarity_score"] = round(score, 3)
                papers.append(pd)
        return {"papers": papers, "count": len(papers), "source": "semantic_library"}
    else:
        # Fallback to text search
        papers = db.search_papers(query=request.query, limit=request.max_results)
        return {"papers": papers, "count": len(papers), "source": "text_library"}


# ─── Routes: Collections ─────────────────────────────────────────────────────

@app.get("/api/collections")
async def get_collections():
    """Get all collections."""
    return {"collections": db.get_collections()}


@app.post("/api/collections")
async def create_collection(request: CreateCollectionRequest):
    """Create a new collection."""
    collection = db.create_collection(
        name=request.name,
        description=request.description,
        color=request.color,
    )
    return {"success": True, "collection": collection.to_dict()}


@app.post("/api/collections/{collection_id}/papers/{paper_id}")
async def add_paper_to_collection(collection_id: int, paper_id: str):
    """Add a paper to a collection."""
    success = db.add_paper_to_collection(paper_id, collection_id)
    return {"success": success}


# ─── Routes: Sessions ─────────────────────────────────────────────────────────

@app.get("/api/sessions")
async def get_sessions():
    """Get all research sessions."""
    return {"sessions": db.get_all_sessions()}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    """Get a specific research session."""
    session = db.get_research_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/sessions")
async def create_session(title: str = "New Research Session"):
    """Create a new research session."""
    session = db.create_research_session(title=title)
    return {"session_id": session.id, "title": session.title}


# ─── Routes: Stats & Utilities ───────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    """Get library statistics."""
    stats = db.get_stats()
    stats["vector_store_available"] = vector_store.is_available
    stats["vector_store_papers"] = vector_store.total_papers
    return stats


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",
        "vector_store": "available" if vector_store.is_available else "unavailable",
    }


# ─── Static Files & Frontend ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend application."""
    ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")
    if os.path.exists(ui_path):
        with open(ui_path) as f:
            return f.read()
    return HTMLResponse("<h1>ResearchPilot API Running</h1><p>Visit /docs for API documentation</p>")
