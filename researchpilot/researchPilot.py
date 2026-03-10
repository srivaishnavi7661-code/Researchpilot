"""
ResearchPilot Core Logic
Shared functions for Flask backend and Streamlit frontend
"""

import google.generativeai as genai
import requests
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyASrrtociRXWsFJcaFDlhWMGtKymgCbJiY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None

def search_papers(query, max_results=10):
    """Search papers from ArXiv API"""
    if not query:
        return {'error': 'Query is required'}

    try:
        # Fetch from ArXiv API
        arxiv_url = f"http://export.arxiv.org/api/query?search_query=all:{requests.utils.quote(query)}&start=0&max_results={max_results}&sortBy=relevance"
        response = requests.get(arxiv_url, timeout=15)
        root = ET.fromstring(response.content)

        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        papers = []

        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            published = entry.find('atom:published', ns)
            link = entry.find('atom:id', ns)
            authors = entry.findall('atom:author', ns)

            author_names = [a.find('atom:name', ns).text for a in authors[:3] if a.find('atom:name', ns) is not None]

            categories = entry.findall('atom:category', ns)
            tags = [c.get('term', '') for c in categories[:3]]

            papers.append({
                'id': link.text if link is not None else '',
                'title': title.text.strip().replace('\n', ' ') if title is not None else 'Unknown',
                'abstract': summary.text.strip().replace('\n', ' ')[:400] + '...' if summary is not None else '',
                'authors': author_names,
                'published': published.text[:10] if published is not None else '',
                'url': link.text if link is not None else '#',
                'tags': tags,
                'source': 'arxiv'
            })

        return {'papers': papers, 'total': len(papers), 'query': query}

    except Exception as e:
        return {'error': str(e), 'papers': []}

def summarize_paper(title, abstract, summary_type='concise'):
    """AI Paper Summarization using Gemini"""
    if not abstract:
        return {'error': 'Abstract is required'}

    if not model:
        return {'error': 'Google API key not configured'}

    prompts = {
        'concise': f"Summarize this research paper in 3 bullet points. Be clear and precise.\n\nTitle: {title}\nAbstract: {abstract}",
        'detailed': f"Provide a detailed analysis of this research paper including: key contributions, methodology, results, and implications.\n\nTitle: {title}\nAbstract: {abstract}",
        'eli5': f"Explain this research paper like I'm 5 years old, using simple analogies.\n\nTitle: {title}\nAbstract: {abstract}"
    }

    try:
        response = model.generate_content(prompts.get(summary_type, prompts['concise']))
        return {'summary': response.text, 'type': summary_type}
    except Exception as e:
        return {'error': str(e)}

def chat_message(message, session_id='default', context=''):
    """AI Research Chat Assistant"""
    if not message:
        return {'error': 'Message is required'}

    if not model:
        return {'error': 'Google API key not configured'}

    try:
        system_prompt = """You are ResearchPilot, an expert AI research assistant. You help researchers:
- Understand complex academic papers
- Find connections between research topics
- Suggest research directions and gaps
- Explain technical concepts clearly
- Provide critical analysis of methodologies

Be concise, accurate, and cite reasoning. If asked about a specific paper, focus on that context."""

        if context:
            full_message = f"{system_prompt}\n\nPaper Context:\n{context}\n\nResearcher Question: {message}"
        else:
            full_message = f"{system_prompt}\n\nResearcher Question: {message}"

        response = model.generate_content(full_message)
        reply = response.text

        return {'reply': reply, 'session_id': session_id}

    except Exception as e:
        return {'error': str(e)}

def get_insights(papers=None, topic=''):
    """Research Insights & Trend Analysis"""
    if not papers and not topic:
        return {'error': 'Papers or topic required'}

    if not model:
        return {'error': 'Google API key not configured'}

    try:
        if papers:
            paper_summaries = "\n\n".join([
                f"Title: {p.get('title', '')}\nAbstract: {p.get('abstract', '')[:200]}"
                for p in papers[:8]
            ])
            prompt = f"""Analyze these research papers and provide:
1. **Key Themes**: Main recurring themes across papers
2. **Research Gaps**: Unexplored areas you notice
3. **Emerging Trends**: What directions seem to be emerging
4. **Key Findings**: Most significant insights
5. **Recommended Reading Order**: For a new researcher

Papers:\n{paper_summaries}"""
        else:
            prompt = f"""Provide a comprehensive research landscape analysis for the topic: "{topic}"
Include:
1. **Current State**: Where the field stands today
2. **Key Challenges**: Main open problems
3. **Promising Directions**: Hot research areas
4. **Key Researchers/Labs**: Notable contributors
5. **Essential Papers**: Must-read works in this area"""

        response = model.generate_content(prompt)
        return {'insights': response.text, 'generated_at': datetime.now().isoformat()}

    except Exception as e:
        return {'error': str(e)}

def generate_citation(paper, style='apa'):
    """Citation & Reference Generator"""
    if not paper:
        return {'error': 'Paper data required'}

    if not model:
        return {'error': 'Google API key not configured'}

    try:
        prompt = f"""Generate a proper {style.upper()} citation for this paper:

Title: {paper.get('title', '')}
Authors: {', '.join(paper.get('authors', []))}
Published: {paper.get('published', '')}
URL: {paper.get('url', '')}
Source: ArXiv

Return ONLY the formatted citation string, nothing else."""

        response = model.generate_content(prompt)
        return {'citation': response.text.strip(), 'style': style}
    except Exception as e:
        return {'error': str(e)}
