"""
ResearchPilot - Core AI Agent
Autonomous research agent powered by Google Gemini with tool use capabilities.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
import google.generativeai as genai

from ..database.manager import DatabaseManager
from ..tools.arxiv_tool import ArXivTool
from ..tools.semantic_scholar_tool import SemanticScholarTool
from ..tools.vector_store import VectorStore


# ─── Tool Definitions for Gemini ─────────────────────────────────────────────

AGENT_TOOLS_GEMINI = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="search_arxiv",
                description="Search arXiv.org for academic papers. Returns papers with titles, abstracts, authors, and metadata.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="Search query"),
                        "max_results": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Maximum results (1-50)"),
                        "sort_by": genai.protos.Schema(type=genai.protos.Type.STRING, description="Sort by: relevance, lastUpdatedDate, submittedDate"),
                    },
                    required=["query"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="search_semantic_scholar",
                description="Search Semantic Scholar for papers with citation data and cross-domain research.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="Search query"),
                        "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Number of results (1-50)"),
                        "year_range": genai.protos.Schema(type=genai.protos.Type.STRING, description="Year range like 2020-2024"),
                    },
                    required=["query"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="semantic_search_library",
                description="Search the user's saved paper library using semantic similarity.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="Natural language query"),
                        "k": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Number of results (1-20)"),
                    },
                    required=["query"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="save_paper",
                description="Save a paper to the user's research library.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "paper_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="Paper ID"),
                        "title": genai.protos.Schema(type=genai.protos.Type.STRING, description="Paper title"),
                        "abstract": genai.protos.Schema(type=genai.protos.Type.STRING, description="Paper abstract"),
                        "authors": genai.protos.Schema(type=genai.protos.Type.STRING, description="Authors comma separated"),
                        "source": genai.protos.Schema(type=genai.protos.Type.STRING, description="Source: arxiv or semantic_scholar"),
                        "source_url": genai.protos.Schema(type=genai.protos.Type.STRING, description="URL to the paper"),
                        "pdf_url": genai.protos.Schema(type=genai.protos.Type.STRING, description="PDF URL"),
                        "published_date": genai.protos.Schema(type=genai.protos.Type.STRING, description="Published date"),
                        "collection_id": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Optional collection ID"),
                    },
                    required=["paper_id", "title"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_paper_summary",
                description="Get or generate a detailed AI summary for a saved paper.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "paper_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="Paper ID in the library"),
                        "focus": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional focus: methodology, results, limitations"),
                    },
                    required=["paper_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_citations",
                description="Get papers that cite or are cited by a specific paper.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "paper_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="Paper ID"),
                        "direction": genai.protos.Schema(type=genai.protos.Type.STRING, description="citing or references"),
                        "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Number of results"),
                    },
                    required=["paper_id", "direction"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_library_stats",
                description="Get statistics about the user's paper library.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={}
                )
            ),
            genai.protos.FunctionDeclaration(
                name="list_collections",
                description="List all the user's paper collections/folders.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={}
                )
            ),
            genai.protos.FunctionDeclaration(
                name="create_collection",
                description="Create a new collection/folder to organize papers.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Collection name"),
                        "description": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional description"),
                        "color": genai.protos.Schema(type=genai.protos.Type.STRING, description="Hex color like #4A90E2"),
                    },
                    required=["name"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="compare_papers",
                description="Compare multiple papers side by side on methodology, results, and contributions.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "paper_ids": genai.protos.Schema(type=genai.protos.Type.STRING, description="Comma-separated paper IDs to compare"),
                        "aspects": genai.protos.Schema(type=genai.protos.Type.STRING, description="Comma-separated aspects: methodology,results,contributions"),
                    },
                    required=["paper_ids"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="generate_research_report",
                description="Generate a comprehensive research report on a topic based on saved papers.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "topic": genai.protos.Schema(type=genai.protos.Type.STRING, description="Research topic or question"),
                        "report_type": genai.protos.Schema(type=genai.protos.Type.STRING, description="survey, gap_analysis, trend_analysis, or methodology_review"),
                        "paper_ids": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional comma-separated paper IDs"),
                    },
                    required=["topic"]
                )
            ),
        ]
    )
]

SYSTEM_PROMPT = """You are ResearchPilot, an autonomous AI research assistant specializing in academic literature discovery and analysis. You have deep expertise across scientific domains and can:

1. Search & Discover: Find relevant papers across arXiv and Semantic Scholar
2. Analyze & Summarize: Generate insightful summaries highlighting key contributions, methodology, and limitations
3. Organize: Help users build and manage their research library
4. Compare & Synthesize: Compare papers, identify trends, and find research gaps
5. Generate Reports: Create comprehensive literature reviews and research reports

Your Approach:
- Always be proactive: when users ask broad questions, search multiple sources
- Prioritize the user's saved library first before external searches
- Provide specific, actionable insights rather than generic summaries
- When saving papers, always generate AI summaries automatically
- Format responses clearly with markdown for readability

Today's date: """ + datetime.now().strftime("%B %d, %Y")


class ResearchAgent:
    """Autonomous AI research agent powered by Google Gemini."""

    def __init__(
        self,
        db: DatabaseManager,
        vector_store: VectorStore,
        arxiv_tool: ArXivTool,
        ss_tool: SemanticScholarTool,
        model: str = "gemini-1.5-pro",
        max_iterations: int = 15,
    ):
        self.db = db
        self.vector_store = vector_store
        self.arxiv = arxiv_tool
        self.ss = ss_tool
        self.model_name = model
        self.max_iterations = max_iterations

        # Configure Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=AGENT_TOOLS_GEMINI,
            system_instruction=SYSTEM_PROMPT,
        )
        self.flash_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="You are a helpful academic paper analysis assistant."
        )
        logger.info(f"ResearchAgent initialized with model: {self.model_name}")

    def chat(
        self,
        user_message: str,
        conversation_history: List[Dict] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process a user message and return agent response."""
        history = conversation_history or []
        tool_calls_log = []
        iterations = 0

        # Build Gemini chat history
        gemini_history = self._convert_history_to_gemini(history)

        try:
            chat_session = self.model.start_chat(history=gemini_history)
            response = chat_session.send_message(user_message)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "tool_calls": [],
                "updated_history": history,
                "error": str(e)
            }

        # Agentic loop - handle function calls
        while iterations < self.max_iterations:
            iterations += 1

            fn_calls = []
            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fn_calls.append(part.function_call)

            if not fn_calls:
                break

            fn_responses = []
            for fn_call in fn_calls:
                tool_name = fn_call.name
                tool_input = dict(fn_call.args)

                logger.info(f"Agent calling tool: {tool_name}")
                result = self._execute_tool(tool_name, tool_input)

                tool_calls_log.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "timestamp": datetime.now().isoformat()
                })

                fn_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": json.dumps(result, default=str)}
                        )
                    )
                )

            try:
                response = chat_session.send_message(fn_responses)
            except Exception as e:
                logger.error(f"Error sending tool results: {e}")
                break

        # Extract final text
        final_text = ""
        for part in response.parts:
            if hasattr(part, "text") and part.text:
                final_text += part.text

        updated_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": final_text}
        ]

        if session_id:
            self.db.update_research_session(session_id, updated_history, tool_calls_log)

        return {
            "response": final_text,
            "tool_calls": tool_calls_log,
            "updated_history": updated_history,
        }

    def _convert_history_to_gemini(self, history: List[Dict]) -> List[Dict]:
        """Convert our history format to Gemini format."""
        gemini_history = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                gemini_history.append({"role": role, "parts": [content]})
        return gemini_history

    def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Execute a tool call and return the result."""
        try:
            if tool_name == "search_arxiv":
                results = self.arxiv.search(
                    query=tool_input["query"],
                    max_results=int(tool_input.get("max_results", 10)),
                    sort_by=tool_input.get("sort_by", "relevance"),
                )
                return {"success": True, "count": len(results), "papers": results[:20]}

            elif tool_name == "search_semantic_scholar":
                results = self.ss.search(
                    query=tool_input["query"],
                    limit=int(tool_input.get("limit", 10)),
                    year_range=tool_input.get("year_range"),
                )
                return {"success": True, "count": len(results), "papers": results[:20]}

            elif tool_name == "semantic_search_library":
                if not self.vector_store.is_available:
                    results = self.db.search_papers(
                        query=tool_input["query"],
                        limit=int(tool_input.get("k", 10))
                    )
                    return {"success": True, "method": "text_search", "papers": results}

                similar = self.vector_store.search(
                    query=tool_input["query"],
                    k=int(tool_input.get("k", 10))
                )
                papers = []
                for paper_id, score in similar:
                    paper = self.db.get_paper(paper_id)
                    if paper:
                        pd = paper.to_dict() if hasattr(paper, 'to_dict') else paper
                        pd["similarity_score"] = round(score, 3)
                        papers.append(pd)
                return {"success": True, "method": "semantic_search", "papers": papers}

            elif tool_name == "save_paper":
                authors_raw = tool_input.get("authors", "")
                authors = [a.strip() for a in authors_raw.split(",")] if authors_raw else []
                paper_data = {
                    "id": tool_input["paper_id"],
                    "title": tool_input["title"],
                    "abstract": tool_input.get("abstract", ""),
                    "authors": authors,
                    "source": tool_input.get("source", "unknown"),
                    "source_url": tool_input.get("source_url", ""),
                    "pdf_url": tool_input.get("pdf_url", ""),
                    "published_date": tool_input.get("published_date", ""),
                }
                self.db.save_paper(paper_data)
                if self.vector_store.is_available:
                    self.vector_store.add_paper(
                        paper_id=paper_data["id"],
                        title=paper_data["title"],
                        abstract=paper_data.get("abstract", ""),
                    )
                if collection_id := tool_input.get("collection_id"):
                    self.db.add_paper_to_collection(paper_data["id"], int(collection_id))
                if paper_data.get("abstract"):
                    summary_data = self._generate_paper_summary(paper_data)
                    if summary_data:
                        self.db.update_paper_ai_fields(paper_data["id"], summary_data)
                return {"success": True, "message": f"Paper saved: {tool_input['title']}", "paper_id": tool_input["paper_id"]}

            elif tool_name == "get_paper_summary":
                paper_id = tool_input["paper_id"]
                paper = self.db.get_paper(paper_id)
                if not paper:
                    return {"success": False, "error": "Paper not found in library"}
                paper_dict = paper.to_dict() if hasattr(paper, 'to_dict') else paper
                if paper_dict.get("ai_summary"):
                    return {"success": True, "title": paper_dict["title"], "summary": paper_dict["ai_summary"], "cached": True}
                summary_data = self._generate_paper_summary(paper_dict, focus=tool_input.get("focus"))
                if summary_data:
                    self.db.update_paper_ai_fields(paper_id, summary_data)
                    return {"success": True, "title": paper_dict["title"], "summary": summary_data.get("ai_summary"), "cached": False}
                return {"success": False, "error": "Failed to generate summary"}

            elif tool_name == "get_citations":
                ss_id = tool_input["paper_id"].replace("ss:", "") if tool_input["paper_id"].startswith("ss:") else tool_input["paper_id"]
                if tool_input["direction"] == "citing":
                    papers = self.ss.get_citations(ss_id, limit=int(tool_input.get("limit", 20)))
                else:
                    papers = self.ss.get_references(ss_id, limit=int(tool_input.get("limit", 20)))
                return {"success": True, "direction": tool_input["direction"], "count": len(papers), "papers": papers}

            elif tool_name == "get_library_stats":
                stats = self.db.get_stats()
                stats["vector_store_papers"] = self.vector_store.total_papers
                return {"success": True, "stats": stats}

            elif tool_name == "list_collections":
                return {"success": True, "collections": self.db.get_collections()}

            elif tool_name == "create_collection":
                collection = self.db.create_collection(
                    name=tool_input["name"],
                    description=tool_input.get("description", ""),
                    color=tool_input.get("color", "#4A90E2"),
                )
                return {"success": True, "collection_id": collection.id, "name": collection.name}

            elif tool_name == "compare_papers":
                paper_ids = [p.strip() for p in tool_input["paper_ids"].split(",")]
                aspects = [a.strip() for a in tool_input.get("aspects", "methodology,results,contributions").split(",")]
                papers = []
                for pid in paper_ids:
                    paper = self.db.get_paper(pid)
                    if paper:
                        papers.append(paper.to_dict() if hasattr(paper, 'to_dict') else paper)
                if len(papers) < 2:
                    return {"success": False, "error": "Need at least 2 papers to compare"}
                return {"success": True, "comparison": self._compare_papers_with_ai(papers, aspects)}

            elif tool_name == "generate_research_report":
                topic = tool_input["topic"]
                report_type = tool_input.get("report_type", "survey")
                paper_ids_raw = tool_input.get("paper_ids", "")
                paper_ids = [p.strip() for p in paper_ids_raw.split(",")] if paper_ids_raw else []
                papers = []
                for pid in paper_ids:
                    p = self.db.get_paper(pid)
                    if p:
                        papers.append(p.to_dict() if hasattr(p, 'to_dict') else p)
                if not papers:
                    similar = self.vector_store.search(topic, k=10)
                    for pid, _ in similar:
                        p = self.db.get_paper(pid)
                        if p:
                            papers.append(p.to_dict() if hasattr(p, 'to_dict') else p)
                report = self._generate_research_report(topic, papers, report_type)
                return {"success": True, "report": report, "papers_analyzed": len(papers)}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {"success": False, "error": str(e)}

    def _generate_paper_summary(self, paper_data: dict, focus: str = None) -> Optional[dict]:
        """Generate AI summary for a paper using Gemini Flash."""
        abstract = paper_data.get("abstract", "")
        title = paper_data.get("title", "")
        if not abstract:
            return None

        focus_instruction = f"\nFocus particularly on: {focus}" if focus else ""
        prompt = f"""Analyze this academic paper:

Title: {title}
Authors: {', '.join(paper_data.get('authors', [])[:5])}
Abstract: {abstract}
{focus_instruction}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "ai_summary": "2-3 paragraph comprehensive summary",
  "ai_key_contributions": ["contribution 1", "contribution 2", "contribution 3"],
  "ai_methodology": "Description of the methodology",
  "ai_limitations": "Key limitations",
  "ai_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""

        try:
            response = self.flash_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=1500)
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None

    def _compare_papers_with_ai(self, papers: list, aspects: list) -> str:
        """Compare papers using Gemini Flash."""
        papers_text = "\n\n".join([
            f"Paper {i+1}: {p['title']}\nAbstract: {p.get('abstract', '')[:400]}"
            for i, p in enumerate(papers)
        ])
        prompt = f"""Compare these {len(papers)} papers on: {', '.join(aspects)}

{papers_text}

Cover: similarities, differences, methodology comparison, results, best use cases."""

        try:
            response = self.flash_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=2000)
            )
            return response.text
        except Exception as e:
            return f"Comparison failed: {e}"

    def _generate_research_report(self, topic: str, papers: list, report_type: str) -> str:
        """Generate a research report using Gemini Pro."""
        papers_text = "\n".join([
            f"- {p['title']}: {p.get('abstract', '')[:200]}..."
            for p in papers[:15]
        ]) if papers else "No papers found."

        prompt = f"""Generate a {report_type.replace('_', ' ')} research report on: {topic}

Papers:
{papers_text}

Include: Executive Summary, Background, Key Findings, Analysis, Recommendations, Conclusion."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=3000)
            )
            return response.text
        except Exception as e:
            return f"Report generation failed: {e}"
