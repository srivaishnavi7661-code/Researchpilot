# 🔬 ResearchPilot AI Agent
### Autonomous Research Intelligence Hub

ResearchPilot is a powerful AI agent powered by Anthropic's Claude that autonomously helps researchers discover, organize, analyze, and interact with academic papers. It combines multi-source search, semantic similarity, persistent storage, and an intelligent conversational agent to supercharge research productivity.

---

## ✨ Features

### 🤖 Autonomous AI Agent
- **Multi-step reasoning** - Claude autonomously decides which tools to use and in what order
- **11 specialized tools** - Search, save, summarize, compare, citation analysis, report generation
- **Conversation memory** - Maintains context across a research session
- **Smart tool selection** - Chooses between arXiv, Semantic Scholar, and local library based on context

### 📚 Multi-Source Paper Search
- **arXiv** - Full-text search with category filtering and date ranges
- **Semantic Scholar** - Citation data, influential papers, field filtering
- **Semantic Library Search** - FAISS-powered similarity search across saved papers

### 🧠 AI-Powered Analysis
- **Contextual Summaries** - 2-3 paragraph summaries explaining purpose, approach, and findings
- **Key Contributions** - Structured extraction of paper contributions
- **Methodology Analysis** - Detailed breakdown of experimental approach
- **Limitation Detection** - Identifies weaknesses and assumptions
- **Auto-tagging** - AI-generated topic tags

### 📊 Research Management
- **Collections** - Organize papers into named, colored folders
- **Bookmarks & Ratings** - Personal paper tracking
- **Research Sessions** - Persistent conversation history
- **Statistics Dashboard** - Library analytics

### 🔌 Multiple Interfaces
- **Interactive CLI** - Rich terminal UI with colorful output
- **REST API** - Full FastAPI server with auto-generated docs
- **Python API** - Direct integration into research workflows

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/researchpilot
cd researchpilot
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run

**Interactive Chat (simplest):**
```bash
python -m researchpilot.main chat
```

**Rich CLI:**
```bash
researchpilot chat
```

**API Server:**
```bash
researchpilot serve --port 8000
# Visit http://localhost:8000/docs for Swagger UI
```

---

## 📖 Usage Examples

### CLI Chat

```bash
$ researchpilot chat

You: Find me the top 5 papers on vision transformers from 2023

ResearchPilot: 🔧 Tools used: search_arxiv, search_semantic_scholar
[Searches and returns curated list with summaries]

You: Save the top 3 to my "Vision Research" collection

ResearchPilot: 🔧 Tools used: create_collection, save_paper (×3)
[Creates collection and saves papers with AI summaries]

You: Compare these 3 papers on methodology

ResearchPilot: 🔧 Tools used: compare_papers
[Generates structured comparison table]

You: Generate a trend analysis report on vision transformers

ResearchPilot: 🔧 Tools used: generate_research_report
[Produces comprehensive literature review]
```

### Command Line Tools

```bash
# Search without chat
researchpilot search "diffusion models image generation" --source arxiv --max 20 --save

# View your library
researchpilot library --query "attention mechanism" --limit 10

# View statistics
researchpilot stats
```

### Python API

```python
from researchpilot import ResearchAgent, DatabaseManager, ArXivTool, VectorStore
from researchpilot.tools import SemanticScholarTool

# Initialize components
db = DatabaseManager("sqlite:///research.db")
vector_store = VectorStore("./vectors")
agent = ResearchAgent(
    db=db,
    vector_store=vector_store,
    arxiv_tool=ArXivTool(),
    ss_tool=SemanticScholarTool(),
)

# Single-turn query
result = agent.chat("What are the latest breakthroughs in protein folding?")
print(result["response"])

# Multi-turn conversation
history = []
for query in ["Find papers on RLHF", "Summarize the top result", "Save it to my library"]:
    result = agent.chat(query, conversation_history=history)
    history = result["updated_history"]
    print(f"Agent: {result['response']}\n")
```

### REST API

```bash
# Start server
researchpilot serve

# Chat with agent
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find papers on LLM reasoning"}'

# Search arXiv
curl -X POST http://localhost:8000/api/search/arxiv \
  -H "Content-Type: application/json" \
  -d '{"query": "chain of thought prompting", "max_results": 10}'

# Get library stats  
curl http://localhost:8000/api/stats

# List collections
curl http://localhost:8000/api/collections
```

---

## 🏗️ Architecture

```
researchpilot/
├── agents/
│   └── research_agent.py    # Core AI agent with Claude + 11 tools
├── api/
│   └── server.py            # FastAPI REST API server
├── database/
│   ├── models.py            # SQLAlchemy ORM models
│   └── manager.py           # Database operations manager
├── tools/
│   ├── arxiv_tool.py        # arXiv search integration
│   ├── semantic_scholar_tool.py  # Semantic Scholar API
│   └── vector_store.py      # FAISS semantic similarity search
├── tests/
│   └── test_researchpilot.py  # Comprehensive test suite
├── cli.py                   # Rich CLI interface
├── main.py                  # Entry point
└── requirements.txt
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| AI Agent | Anthropic Claude (claude-opus-4-5) |
| API Framework | FastAPI + Uvicorn |
| Database | SQLAlchemy + SQLite/PostgreSQL |
| Vector Store | FAISS + sentence-transformers |
| Paper Sources | arXiv API, Semantic Scholar API |
| CLI | Typer + Rich |
| Summaries | Claude Haiku (fast, efficient) |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Required | Your Anthropic API key |
| `DATABASE_URL` | `sqlite:///./researchpilot.db` | Database connection string |
| `AGENT_MODEL` | `claude-opus-4-5` | Claude model for agent |
| `VECTOR_STORE_PATH` | `./data/vector_store` | Path for FAISS index |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `ARXIV_MAX_RESULTS` | `50` | Max arXiv results per search |
| `AGENT_MAX_ITERATIONS` | `15` | Max agent reasoning steps |

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio
pytest researchpilot/tests/ -v --tb=short
```

---

## 📡 API Reference

Full Swagger documentation available at `http://localhost:8000/docs` when running the server.

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send message to AI agent |
| `GET` | `/api/papers` | List library papers |
| `POST` | `/api/papers` | Save paper to library |
| `GET` | `/api/papers/{id}` | Get specific paper |
| `PATCH` | `/api/papers/{id}` | Update paper fields |
| `DELETE` | `/api/papers/{id}` | Remove from library |
| `POST` | `/api/papers/{id}/summarize` | Generate AI summary |
| `POST` | `/api/search/arxiv` | Search arXiv |
| `POST` | `/api/search/semantic-scholar` | Search Semantic Scholar |
| `POST` | `/api/search/semantic` | Semantic library search |
| `GET` | `/api/collections` | List collections |
| `POST` | `/api/collections` | Create collection |
| `GET` | `/api/sessions` | List research sessions |
| `GET` | `/api/stats` | Library statistics |

---

## 🤝 Extending ResearchPilot

### Adding New Search Sources

Implement the interface:
```python
class MyNewSourceTool:
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        # Returns list of paper dicts with standard fields
        ...
```

### Adding New Agent Tools

Add to `AGENT_TOOLS` in `agents/research_agent.py` and implement in `_execute_tool()`.

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Anthropic** - Claude AI powering the agent reasoning
- **arXiv** - Open access to research papers  
- **Semantic Scholar** - Citation graph and paper metadata
- **FAISS** - Efficient similarity search
- **sentence-transformers** - Text embeddings
