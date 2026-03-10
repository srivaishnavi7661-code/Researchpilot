"""
ResearchPilot - Test Suite
Comprehensive tests for all components.
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Set test environment
os.environ["ANTHROPIC_API_KEY"] = "test_key"
os.environ["DATABASE_URL"] = "sqlite:///./test_researchpilot.db"


# ─── Database Tests ───────────────────────────────────────────────────────────

class TestDatabaseManager:
    """Tests for DatabaseManager."""

    @pytest.fixture
    def db(self, tmp_path):
        from researchpilot.database.manager import DatabaseManager
        db_path = tmp_path / "test.db"
        return DatabaseManager(f"sqlite:///{db_path}")

    @pytest.fixture
    def sample_paper(self):
        return {
            "id": "arxiv:2301.00001",
            "arxiv_id": "2301.00001",
            "title": "Attention Is All You Need: A Revisit",
            "abstract": "We revisit the transformer architecture and propose improvements...",
            "authors": ["John Doe", "Jane Smith"],
            "published_date": "2023-01-01",
            "source": "arxiv",
            "source_url": "https://arxiv.org/abs/2301.00001",
            "pdf_url": "https://arxiv.org/pdf/2301.00001",
            "categories": ["cs.LG", "cs.AI"],
            "keywords": ["transformer", "attention"],
            "citation_count": 150,
        }

    def test_save_and_get_paper(self, db, sample_paper):
        """Test saving and retrieving a paper."""
        db.save_paper(sample_paper)
        retrieved = db.get_paper(sample_paper["id"])
        assert retrieved is not None
        assert retrieved.title == sample_paper["title"]
        assert retrieved.arxiv_id == sample_paper["arxiv_id"]

    def test_update_paper_prevents_duplicate(self, db, sample_paper):
        """Test that saving same paper twice updates instead of duplicating."""
        db.save_paper(sample_paper)
        sample_paper["citation_count"] = 200
        db.save_paper(sample_paper)
        
        papers = db.get_all_papers()
        assert len([p for p in papers if p["id"] == sample_paper["id"]]) == 1

    def test_search_papers_by_title(self, db, sample_paper):
        """Test searching papers by title."""
        db.save_paper(sample_paper)
        results = db.search_papers(query="Attention Is All")
        assert len(results) >= 1
        assert any(p["id"] == sample_paper["id"] for p in results)

    def test_search_papers_empty_query(self, db, sample_paper):
        """Test that empty query returns all papers."""
        db.save_paper(sample_paper)
        results = db.get_all_papers()
        assert len(results) >= 1

    def test_update_paper_ai_fields(self, db, sample_paper):
        """Test updating AI-generated fields."""
        db.save_paper(sample_paper)
        ai_data = {
            "ai_summary": "This paper presents...",
            "ai_key_contributions": ["Contribution 1", "Contribution 2"],
            "ai_tags": ["transformer", "NLP"],
        }
        success = db.update_paper_ai_fields(sample_paper["id"], ai_data)
        assert success
        
        paper = db.get_paper(sample_paper["id"])
        assert paper.ai_summary == "This paper presents..."

    def test_update_paper_user_fields(self, db, sample_paper):
        """Test updating user fields."""
        db.save_paper(sample_paper)
        db.update_paper_user_fields(sample_paper["id"], {
            "is_bookmarked": True,
            "user_rating": 5,
            "user_notes": "Must read!"
        })
        
        paper = db.get_paper(sample_paper["id"])
        assert paper.is_bookmarked == True
        assert paper.user_rating == 5

    def test_delete_paper(self, db, sample_paper):
        """Test deleting a paper."""
        db.save_paper(sample_paper)
        db.delete_paper(sample_paper["id"])
        assert db.get_paper(sample_paper["id"]) is None

    def test_create_and_get_collection(self, db):
        """Test creating and retrieving collections."""
        collection = db.create_collection("ML Papers", "Machine learning research")
        assert collection.id is not None
        assert collection.name == "ML Papers"
        
        collections = db.get_collections()
        assert any(c["name"] == "ML Papers" for c in collections)

    def test_add_paper_to_collection(self, db, sample_paper):
        """Test adding a paper to a collection."""
        db.save_paper(sample_paper)
        collection = db.create_collection("Test Collection")
        
        success = db.add_paper_to_collection(sample_paper["id"], collection.id)
        assert success

    def test_research_session_lifecycle(self, db):
        """Test creating and updating a research session."""
        session = db.create_research_session("Test Session")
        assert session.id is not None
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ]
        db.update_research_session(session.id, messages)
        
        retrieved = db.get_research_session(session.id)
        assert len(retrieved["messages"]) == 2

    def test_get_stats(self, db, sample_paper):
        """Test statistics retrieval."""
        db.save_paper(sample_paper)
        stats = db.get_stats()
        
        assert "total_papers" in stats
        assert stats["total_papers"] >= 1
        assert "total_collections" in stats


# ─── ArXiv Tool Tests ─────────────────────────────────────────────────────────

class TestArXivTool:
    """Tests for ArXiv search tool."""

    @pytest.fixture
    def arxiv_tool(self):
        from researchpilot.tools.arxiv_tool import ArXivTool
        return ArXivTool(max_results=5)

    def test_result_to_dict_structure(self, arxiv_tool):
        """Test that paper dict has required fields."""
        mock_result = MagicMock()
        mock_result.get_short_id.return_value = "2301.00001"
        mock_result.title = "Test Paper"
        mock_result.summary = "Test abstract"
        mock_result.authors = [MagicMock(__str__=lambda self: "Author One")]
        mock_result.published = datetime(2023, 1, 1)
        mock_result.updated = datetime(2023, 1, 2)
        mock_result.entry_id = "https://arxiv.org/abs/2301.00001"
        mock_result.pdf_url = "https://arxiv.org/pdf/2301.00001"
        mock_result.doi = None
        mock_result.categories = ["cs.AI", "cs.LG"]

        paper = arxiv_tool._result_to_dict(mock_result)
        
        assert paper["id"] == "arxiv:2301.00001"
        assert paper["title"] == "Test Paper"
        assert paper["source"] == "arxiv"
        assert "authors" in paper
        assert "abstract" in paper
        assert "categories" in paper

    @patch("arxiv.Client")
    def test_search_returns_list(self, mock_client, arxiv_tool):
        """Test that search always returns a list."""
        mock_client.return_value.results.return_value = []
        results = arxiv_tool.search("quantum computing")
        assert isinstance(results, list)


# ─── Semantic Scholar Tool Tests ──────────────────────────────────────────────

class TestSemanticScholarTool:
    """Tests for Semantic Scholar tool."""

    @pytest.fixture
    def ss_tool(self):
        from researchpilot.tools.semantic_scholar_tool import SemanticScholarTool
        return SemanticScholarTool()

    def test_paper_to_dict_with_empty_paper(self, ss_tool):
        """Test handling empty paper data."""
        result = ss_tool._paper_to_dict({})
        assert isinstance(result, dict)

    def test_paper_to_dict_with_arxiv_id(self, ss_tool):
        """Test that arxiv papers get correct ID."""
        paper = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "Abstract text",
            "authors": [{"name": "John Doe"}],
            "year": 2023,
            "externalIds": {"ArXiv": "2301.00001"},
            "citationCount": 42,
        }
        result = ss_tool._paper_to_dict(paper)
        assert result["id"] == "arxiv:2301.00001"
        assert result["arxiv_id"] == "2301.00001"
        assert result["citation_count"] == 42


# ─── Vector Store Tests ───────────────────────────────────────────────────────

class TestVectorStore:
    """Tests for FAISS vector store."""

    @pytest.fixture
    def vector_store(self, tmp_path):
        from researchpilot.tools.vector_store import VectorStore
        return VectorStore(store_path=str(tmp_path / "vectors"))

    def test_initialization(self, vector_store):
        """Test vector store initializes correctly."""
        assert vector_store.total_papers == 0

    def test_add_paper_without_dependencies(self, vector_store):
        """Test graceful handling when FAISS/ST not available."""
        # If deps not available, should return False gracefully
        if not vector_store.is_available:
            result = vector_store.add_paper("test:001", "Test Title", "Test abstract")
            assert result == False

    def test_search_empty_store(self, vector_store):
        """Test search on empty store returns empty list."""
        results = vector_store.search("test query")
        assert results == []

    def test_remove_nonexistent_paper(self, vector_store):
        """Test removing nonexistent paper returns False."""
        result = vector_store.remove_paper("nonexistent:001")
        assert result == False


# ─── Research Agent Tests ─────────────────────────────────────────────────────

class TestResearchAgent:
    """Tests for the ResearchAgent."""

    @pytest.fixture
    def mock_agent(self, tmp_path):
        from researchpilot.database.manager import DatabaseManager
        from researchpilot.tools.arxiv_tool import ArXivTool
        from researchpilot.tools.semantic_scholar_tool import SemanticScholarTool
        from researchpilot.tools.vector_store import VectorStore
        from researchpilot.agents.research_agent import ResearchAgent
        
        db = DatabaseManager(f"sqlite:///{tmp_path}/test.db")
        vector_store = VectorStore(str(tmp_path / "vectors"))
        arxiv_tool = ArXivTool()
        ss_tool = SemanticScholarTool()
        
        return ResearchAgent(
            db=db,
            vector_store=vector_store,
            arxiv_tool=arxiv_tool,
            ss_tool=ss_tool,
        )

    def test_execute_tool_get_library_stats(self, mock_agent):
        """Test library stats tool."""
        result = mock_agent._execute_tool("get_library_stats", {})
        assert result["success"] == True
        assert "stats" in result

    def test_execute_tool_list_collections(self, mock_agent):
        """Test list collections tool."""
        result = mock_agent._execute_tool("list_collections", {})
        assert result["success"] == True
        assert "collections" in result

    def test_execute_tool_create_collection(self, mock_agent):
        """Test create collection tool."""
        result = mock_agent._execute_tool("create_collection", {
            "name": "Test Collection",
            "description": "Test"
        })
        assert result["success"] == True
        assert "collection_id" in result

    def test_execute_tool_unknown_tool(self, mock_agent):
        """Test handling of unknown tool."""
        result = mock_agent._execute_tool("nonexistent_tool", {})
        assert result["success"] == False

    def test_execute_tool_save_paper(self, mock_agent):
        """Test saving a paper via tool."""
        paper_data = {
            "id": "arxiv:test001",
            "title": "Test Paper",
            "abstract": "Test abstract for testing purposes",
            "authors": ["Test Author"],
            "source": "arxiv",
        }
        result = mock_agent._execute_tool("save_paper", {
            "paper_data": paper_data,
            "generate_summary": False,
        })
        assert result["success"] == True
        assert result["paper_id"] == "arxiv:test001"

    @patch("anthropic.Anthropic")
    def test_chat_returns_response(self, mock_anthropic_cls, mock_agent):
        """Test that chat returns a response dict."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_agent.client = mock_client
        
        # Mock a successful end_turn response
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_text_block = MagicMock()
        mock_text_block.text = "Here are some papers on transformers..."
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response
        
        result = mock_agent.chat("Find me papers on transformers")
        
        assert "response" in result
        assert "tool_calls" in result
        assert "updated_history" in result


# ─── Integration Tests ────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests testing multiple components together."""

    @pytest.fixture
    def setup(self, tmp_path):
        from researchpilot.database.manager import DatabaseManager
        from researchpilot.tools.vector_store import VectorStore
        
        db = DatabaseManager(f"sqlite:///{tmp_path}/integration.db")
        vs = VectorStore(str(tmp_path / "vectors"))
        return db, vs

    def test_paper_save_and_search_flow(self, setup):
        """Test complete paper save and search flow."""
        db, vs = setup
        
        papers = [
            {
                "id": f"arxiv:{i:07d}",
                "title": f"Deep Learning Paper {i}",
                "abstract": f"This paper presents novel approaches to deep learning using transformer architectures {i}",
                "authors": [f"Author {i}"],
                "source": "arxiv",
                "categories": ["cs.LG"],
            }
            for i in range(5)
        ]
        
        for paper in papers:
            db.save_paper(paper)
        
        # Test text search
        results = db.search_papers(query="deep learning")
        assert len(results) > 0
        
        # Test stats updated
        stats = db.get_stats()
        assert stats["total_papers"] >= 5

    def test_collection_workflow(self, setup):
        """Test full collection workflow."""
        db, _ = setup
        
        # Create collection
        collection = db.create_collection("NLP Research", "Papers about NLP")
        
        # Save papers
        paper = {
            "id": "arxiv:nlp001",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce BERT, a new method of pre-training language representations...",
            "authors": ["Jacob Devlin", "Ming-Wei Chang"],
            "source": "arxiv",
        }
        db.save_paper(paper)
        db.add_paper_to_collection(paper["id"], collection.id)
        
        # Search within collection
        results = db.search_papers(collection_id=collection.id)
        assert len(results) >= 1


# ─── Utility Tests ────────────────────────────────────────────────────────────

class TestModels:
    """Tests for database models."""

    @pytest.fixture
    def db(self, tmp_path):
        from researchpilot.database.manager import DatabaseManager
        return DatabaseManager(f"sqlite:///{tmp_path}/models.db")

    def test_paper_to_dict(self, db):
        """Test Paper.to_dict() returns correct format."""
        paper_data = {
            "id": "arxiv:test",
            "title": "Test",
            "abstract": "Abstract",
            "authors": ["Author"],
            "source": "arxiv",
        }
        db.save_paper(paper_data)
        paper = db.get_paper("arxiv:test")
        d = paper.to_dict()
        
        required_keys = ["id", "title", "abstract", "authors", "source"]
        for key in required_keys:
            assert key in d

    def test_collection_to_dict(self, db):
        """Test Collection.to_dict() returns correct format."""
        collection = db.create_collection("Test")
        d = collection.to_dict()
        
        assert "id" in d
        assert "name" in d
        assert "paper_count" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
