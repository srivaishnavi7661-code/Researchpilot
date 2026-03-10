"""
ResearchPilot - Command Line Interface
Rich terminal UI for interacting with the research agent.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Suppress loguru output in CLI mode
logger.remove()

app_cli = typer.Typer(
    name="researchpilot",
    help="🔬 ResearchPilot AI - Autonomous Research Intelligence Hub",
    rich_markup_mode="rich",
)
console = Console()


def get_agent():
    """Initialize and return the research agent."""
    from .database.manager import DatabaseManager
    from .tools.arxiv_tool import ArXivTool
    from .tools.semantic_scholar_tool import SemanticScholarTool
    from .tools.vector_store import VectorStore
    from .agents.research_agent import ResearchAgent
    
    db = DatabaseManager(os.getenv("DATABASE_URL", "sqlite:///./researchpilot.db"))
    vector_store = VectorStore(os.getenv("VECTOR_STORE_PATH", "./data/vector_store"))
    arxiv_tool = ArXivTool()
    ss_tool = SemanticScholarTool(os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
    
    return ResearchAgent(
        db=db,
        vector_store=vector_store,
        arxiv_tool=arxiv_tool,
        ss_tool=ss_tool,
        model=os.getenv("AGENT_MODEL", "gemini-1.5-pro"),
    ), db


def print_banner():
    """Print the ResearchPilot banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║         🔬 ResearchPilot AI Agent v1.0.0                  ║
║         Autonomous Research Intelligence Hub               ║
╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue", expand=False))


@app_cli.command()
def chat(
    session_id: Optional[int] = typer.Option(None, "--session", "-s", help="Resume an existing session"),
    collection_id: Optional[int] = typer.Option(None, "--collection", "-c", help="Associate with a collection"),
):
    """
    Start an interactive chat with the ResearchPilot AI agent.
    """
    print_banner()
    
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]❌ GOOGLE_API_KEY not set. Please configure your .env file.[/red]")
        raise typer.Exit(1)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("Initializing ResearchPilot...", total=None)
        agent, db = get_agent()
        progress.update(task, completed=True)
    
    history = []
    current_session_id = session_id
    
    if session_id:
        session_data = db.get_research_session(session_id)
        if session_data:
            history = session_data.get("messages", [])
            console.print(f"[green]✓ Resumed session #{session_id}[/green]")
        else:
            console.print(f"[yellow]⚠ Session {session_id} not found. Starting new session.[/yellow]")
    
    console.print("\n[dim]Commands: 'quit' to exit, 'clear' to clear history, 'stats' for library stats[/dim]")
    console.print("[dim]Type your research question or request below:\n[/dim]")
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye! 👋[/yellow]")
            break
        
        if not user_input.strip():
            continue
        
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[yellow]Goodbye! 👋[/yellow]")
            break
        
        if user_input.lower() == "clear":
            history = []
            current_session_id = None
            console.print("[green]✓ Conversation cleared[/green]")
            continue
        
        if user_input.lower() == "stats":
            stats = db.get_stats()
            table = Table(title="📊 Library Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            for k, v in stats.items():
                table.add_row(k.replace("_", " ").title(), str(v))
            console.print(table)
            continue
        
        # Send to agent
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            task = progress.add_task("🤔 ResearchPilot is thinking...", total=None)
            
            result = agent.chat(
                user_message=user_input,
                conversation_history=history,
                session_id=current_session_id,
            )
        
        # Update history
        history = result.get("updated_history", history)
        if not current_session_id:
            # Create a new session entry
            session = db.create_research_session(title=user_input[:100])
            current_session_id = session.id
        
        # Show tool calls if any
        tool_calls = result.get("tool_calls", [])
        if tool_calls:
            tool_names = [t["tool"] for t in tool_calls]
            console.print(f"\n[dim]🔧 Tools used: {', '.join(tool_names)}[/dim]")
        
        # Display response
        console.print(f"\n[bold green]ResearchPilot[/bold green] [dim](Session #{current_session_id})[/dim]")
        console.print(Panel(Markdown(result["response"]), border_style="green"))


@app_cli.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option("arxiv", "--source", "-s", help="Search source: arxiv, semantic_scholar"),
    max_results: int = typer.Option(10, "--max", "-n", help="Maximum results"),
    save: bool = typer.Option(False, "--save", help="Save results to library"),
):
    """Search for papers without starting a full chat session."""
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]❌ GOOGLE_API_KEY not set.[/red]")
        raise typer.Exit(1)
    
    _, db = get_agent()
    
    from .tools.arxiv_tool import ArXivTool
    from .tools.semantic_scholar_tool import SemanticScholarTool
    
    with Progress(SpinnerColumn(), TextColumn(f"Searching {source}..."), transient=True) as progress:
        task = progress.add_task("Searching...", total=None)
        
        if source == "arxiv":
            tool = ArXivTool()
            papers = tool.search(query=query, max_results=max_results)
        else:
            tool = SemanticScholarTool(os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
            papers = tool.search(query=query, limit=max_results)
    
    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        return
    
    table = Table(title=f"🔍 Search Results: '{query}' ({source})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=50)
    table.add_column("Authors", max_width=30)
    table.add_column("Date", max_width=12)
    table.add_column("Citations", justify="right")
    
    for i, paper in enumerate(papers, 1):
        authors = ", ".join(paper.get("authors", [])[:2])
        if len(paper.get("authors", [])) > 2:
            authors += " et al."
        table.add_row(
            str(i),
            paper.get("title", "Unknown")[:50],
            authors,
            str(paper.get("published_date", "")[:10] if paper.get("published_date") else ""),
            str(paper.get("citation_count", 0)),
        )
    
    console.print(table)
    
    if save and Confirm.ask(f"\nSave all {len(papers)} papers to library?"):
        saved = 0
        for paper in papers:
            try:
                db.save_paper(paper)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save paper: {e}")
        console.print(f"[green]✓ Saved {saved}/{len(papers)} papers to library[/green]")


@app_cli.command()
def library(
    query: str = typer.Option("", "--query", "-q", help="Filter papers"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of papers to show"),
    bookmarked: bool = typer.Option(False, "--bookmarked", help="Show only bookmarked papers"),
):
    """View your research library."""
    _, db = get_agent()
    
    papers = db.search_papers(
        query=query,
        is_bookmarked=True if bookmarked else None,
        limit=limit,
    )
    
    if not papers:
        console.print("[yellow]No papers found in library.[/yellow]")
        return
    
    table = Table(title=f"📚 Research Library ({len(papers)} papers)")
    table.add_column("ID", max_width=20, style="dim")
    table.add_column("Title", max_width=45)
    table.add_column("Authors", max_width=25)
    table.add_column("Source", max_width=10)
    table.add_column("★", max_width=5)
    table.add_column("🔖", max_width=4)
    
    for paper in papers:
        authors = ", ".join(paper.get("authors", [])[:2])
        if len(paper.get("authors", [])) > 2:
            authors += "..."
        table.add_row(
            paper.get("id", "")[:20],
            paper.get("title", "")[:45],
            authors,
            paper.get("source", "")[:10],
            str(paper.get("user_rating", "") or ""),
            "✓" if paper.get("is_bookmarked") else "",
        )
    
    console.print(table)


@app_cli.command()
def stats():
    """Show library statistics."""
    _, db = get_agent()
    stats_data = db.get_stats()
    
    table = Table(title="📊 ResearchPilot Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green", justify="right")
    
    labels = {
        "total_papers": "Total Papers",
        "bookmarked_papers": "Bookmarked Papers",
        "read_papers": "Read Papers",
        "total_collections": "Collections",
        "total_sessions": "Research Sessions",
        "papers_with_ai_summary": "Papers with AI Summary",
    }
    
    for key, label in labels.items():
        table.add_row(label, str(stats_data.get(key, 0)))
    
    console.print(table)


@app_cli.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    """Start the ResearchPilot API server."""
    import uvicorn
    
    console.print(f"[green]🚀 Starting ResearchPilot API server on http://{host}:{port}[/green]")
    console.print(f"[dim]API docs: http://{host}:{port}/docs[/dim]")
    
    uvicorn.run(
        "researchpilot.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    app_cli()
