"""
ResearchPilot AI Agent - Main Entry Point
Run the application in different modes.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def run_cli():
    """Run the CLI interface."""
    from researchpilot.cli import app_cli
    app_cli()


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the API server."""
    import uvicorn
    uvicorn.run(
        "researchpilot.api.server:app",
        host=host,
        port=port,
        reload=reload,
    )


def run_chat():
    """Run a simple interactive chat session."""
    from researchpilot.database.manager import DatabaseManager
    from researchpilot.tools.arxiv_tool import ArXivTool
    from researchpilot.tools.semantic_scholar_tool import SemanticScholarTool
    from researchpilot.tools.vector_store import VectorStore
    from researchpilot.agents.research_agent import ResearchAgent
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not set in environment.")
        print("   Copy .env.example to .env and add your API key.")
        sys.exit(1)
    
    print("🔬 Initializing ResearchPilot AI Agent...")
    
    db = DatabaseManager(os.getenv("DATABASE_URL", "sqlite:///./researchpilot.db"))
    vector_store = VectorStore(os.getenv("VECTOR_STORE_PATH", "./data/vector_store"))
    arxiv_tool = ArXivTool()
    ss_tool = SemanticScholarTool(os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
    agent = ResearchAgent(db=db, vector_store=vector_store, arxiv_tool=arxiv_tool, ss_tool=ss_tool)
    
    print("✅ ResearchPilot ready! Type 'quit' to exit.\n")
    
    history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        
        print("\nResearchPilot: ", end="", flush=True)
        result = agent.chat(user_input, conversation_history=history)
        print(result["response"])
        
        if result.get("tool_calls"):
            tools = [t["tool"] for t in result["tool_calls"]]
            print(f"\n[Tools used: {', '.join(tools)}]")
        
        history = result.get("updated_history", history)
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ResearchPilot AI Agent")
    parser.add_argument(
        "mode",
        nargs="?",
        default="chat",
        choices=["chat", "server", "cli"],
        help="Run mode: chat (default), server, or cli"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host (server mode)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (server mode)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (server mode)")
    
    args = parser.parse_args()
    
    if args.mode == "chat":
        run_chat()
    elif args.mode == "server":
        run_server(args.host, args.port, args.reload)
    elif args.mode == "cli":
        run_cli()
