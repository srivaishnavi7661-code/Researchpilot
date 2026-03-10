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
from researchpilot import search_papers, summarize_paper, chat_message, get_insights, generate_citation

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configure Gemini (for backward compatibility, but logic moved to researchpilot.py)
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
def search_papers_route():
    data = request.json
    query = data.get('query', '').strip()
    max_results = data.get('max_results', 10)

    result = search_papers(query, max_results)
    if 'error' in result:
        return jsonify(result), 400 if result['error'] == 'Query is required' else 500
    return jsonify(result)


# ─────────────────────────────────────────────
# FEATURE 2: AI Paper Summarization (Gemini)
# ─────────────────────────────────────────────
@app.route('/api/summarize', methods=['POST'])
def summarize_paper_route():
    data = request.json
    title = data.get('title', '')
    abstract = data.get('abstract', '')
    summary_type = data.get('type', 'concise')  # concise / detailed / eli5

    result = summarize_paper(title, abstract, summary_type)
    if 'error' in result:
        return jsonify(result), 400 if result['error'] == 'Abstract is required' else 500
    return jsonify(result)


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

    result = chat_message(message, session_id, context)
    if 'error' in result:
        return jsonify(result), 400 if result['error'] == 'Message is required' else 500

    # Maintain conversation history
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append({'role': 'user', 'content': message})
    chat_sessions[session_id].append({'role': 'assistant', 'content': result['reply']})

    # Keep only last 20 messages
    if len(chat_sessions[session_id]) > 20:
        chat_sessions[session_id] = chat_sessions[session_id][-20:]

    return jsonify(result)


# ─────────────────────────────────────────────
# FEATURE 4: Research Insights & Trend Analysis
# ─────────────────────────────────────────────
@app.route('/api/insights', methods=['POST'])
def get_insights_route():
    data = request.json
    papers = data.get('papers', [])
    topic = data.get('topic', '')

    result = get_insights(papers, topic)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


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

    if not papers:
        return jsonify({'error': 'Papers required'}), 400

    if not model:
        return jsonify({'error': 'Google API key not configured'}), 500

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
def generate_citation_route():
    data = request.json
    paper = data.get('paper', {})
    style = data.get('style', 'apa')  # apa / mla / chicago / bibtex

    result = generate_citation(paper, style)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


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
