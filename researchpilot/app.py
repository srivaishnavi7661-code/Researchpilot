"""
ResearchPilot AI Agent - Backend Server
Uses Google Gemini API for AI-powered research assistance
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import requests
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyASrrtociRXWsFJcaFDlhWMGtKymgCbJiY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None

# ─────────────────────────────────────────────
# FEATURE 1: Semantic Paper Search (ArXiv + AI ranking)
# ─────────────────────────────────────────────
@app.route('/api/search', methods=['POST'])
def search_papers():
    data = request.json
    query = data.get('query', '').strip()
    max_results = data.get('max_results', 10)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

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

        return jsonify({'papers': papers, 'total': len(papers), 'query': query})

    except Exception as e:
        return jsonify({'error': str(e), 'papers': []}), 500


# ─────────────────────────────────────────────
# FEATURE 2: AI Paper Summarization (Gemini)
# ─────────────────────────────────────────────
@app.route('/api/summarize', methods=['POST'])
def summarize_paper():
    data = request.json
    title = data.get('title', '')
    abstract = data.get('abstract', '')
    summary_type = data.get('type', 'concise')  # concise / detailed / eli5

    if not abstract:
        return jsonify({'error': 'Abstract is required'}), 400

    if not model:
        return jsonify({'error': 'Google API key not configured'}), 500

    prompts = {
        'concise': f"Summarize this research paper in 3 bullet points. Be clear and precise.\n\nTitle: {title}\nAbstract: {abstract}",
        'detailed': f"Provide a detailed analysis of this research paper including: key contributions, methodology, results, and implications.\n\nTitle: {title}\nAbstract: {abstract}",
        'eli5': f"Explain this research paper like I'm 5 years old, using simple analogies.\n\nTitle: {title}\nAbstract: {abstract}"
    }

    try:
        response = model.generate_content(prompts.get(summary_type, prompts['concise']))
        return jsonify({'summary': response.text, 'type': summary_type})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# FEATURE 3: AI Research Chat Assistant
# ─────────────────────────────────────────────
chat_sessions = {}

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')
    context = data.get('context', '')  # optional paper context

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    if not model:
        return jsonify({'error': 'Google API key not configured'}), 500

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

        # Maintain conversation history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []

        chat_sessions[session_id].append({'role': 'user', 'content': message})

        response = model.generate_content(full_message)
        reply = response.text

        chat_sessions[session_id].append({'role': 'assistant', 'content': reply})

        # Keep only last 20 messages
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]

        return jsonify({'reply': reply, 'session_id': session_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# FEATURE 4: Research Insights & Trend Analysis
# ─────────────────────────────────────────────
@app.route('/api/insights', methods=['POST'])
def get_insights():
    data = request.json
    papers = data.get('papers', [])
    topic = data.get('topic', '')

    if not papers and not topic:
        return jsonify({'error': 'Papers or topic required'}), 400

    if not model:
        return jsonify({'error': 'Google API key not configured'}), 500

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
        return jsonify({'insights': response.text, 'generated_at': datetime.now().isoformat()})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# FEATURE 5: Smart Reading List Manager
# ─────────────────────────────────────────────
reading_lists = {}

@app.route('/api/reading-list', methods=['GET', 'POST', 'DELETE'])
def reading_list():
    user_id = request.args.get('user_id', 'default')

    if request.method == 'GET':
        papers = reading_lists.get(user_id, [])
        return jsonify({'papers': papers, 'count': len(papers)})

    elif request.method == 'POST':
        paper = request.json
        if user_id not in reading_lists:
            reading_lists[user_id] = []

        # Avoid duplicates
        existing_ids = [p.get('id') for p in reading_lists[user_id]]
        if paper.get('id') not in existing_ids:
            paper['added_at'] = datetime.now().isoformat()
            paper['status'] = 'unread'
            reading_lists[user_id].append(paper)

        return jsonify({'success': True, 'count': len(reading_lists[user_id])})

    elif request.method == 'DELETE':
        paper_id = request.args.get('paper_id')
        if user_id in reading_lists:
            reading_lists[user_id] = [p for p in reading_lists[user_id] if p.get('id') != paper_id]
        return jsonify({'success': True})


@app.route('/api/reading-list/organize', methods=['POST'])
def organize_reading_list():
    data = request.json
    papers = data.get('papers', [])

    if not papers or not model:
        return jsonify({'error': 'Papers and API key required'}), 400

    try:
        titles = "\n".join([f"- {p.get('title', '')}" for p in papers])
        prompt = f"""Given these research papers in a reading list, suggest an optimal reading order and grouping by topic:

{titles}

Provide:
1. **Suggested Reading Order** with brief reason for each
2. **Topic Clusters**: Group papers by related themes
3. **Study Plan**: How to approach these papers efficiently (e.g., 30-min daily sessions)"""

        response = model.generate_content(prompt)
        return jsonify({'plan': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# FEATURE 6: Citation & Reference Generator
# ─────────────────────────────────────────────
@app.route('/api/cite', methods=['POST'])
def generate_citation():
    data = request.json
    paper = data.get('paper', {})
    style = data.get('style', 'apa')  # apa / mla / chicago / bibtex

    if not paper:
        return jsonify({'error': 'Paper data required'}), 400

    if not model:
        return jsonify({'error': 'Google API key not configured'}), 500

    try:
        prompt = f"""Generate a proper {style.upper()} citation for this paper:

Title: {paper.get('title', '')}
Authors: {', '.join(paper.get('authors', []))}
Published: {paper.get('published', '')}
URL: {paper.get('url', '')}
Source: ArXiv

Return ONLY the formatted citation string, nothing else."""

        response = model.generate_content(prompt)
        return jsonify({'citation': response.text.strip(), 'style': style})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Runtime API Key Config
# ─────────────────────────────────────────────
@app.route('/config', methods=['POST'])
def set_config():
    global model, GOOGLE_API_KEY
    data = request.json
    key = data.get('api_key', '').strip()
    if key:
        GOOGLE_API_KEY = key
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        return jsonify({'status': 'configured'})
    return jsonify({'status': 'no key provided'}), 400

# ─────────────────────────────────────────────
# Serve Frontend
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'api_configured': bool(GOOGLE_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 ResearchPilot AI Agent starting...")
    print(f"🔑 Google API: {'✅ Configured' if GOOGLE_API_KEY else '❌ Not configured (add to .env)'}")
    print("🌐 Open: http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')
