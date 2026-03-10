# 🛸 ResearchPilot AI Agent
**Autonomous Research Intelligence Hub**

## ✨ 6 Core Features
| # | Feature | Description |
|---|---------|-------------|
| 1 | **Smart Paper Search** | Semantic search across ArXiv (millions of papers) |
| 2 | **AI Summarizer** | Concise / Detailed / ELI5 summaries via Gemini |
| 3 | **Research Chat** | Ask anything about papers or research topics |
| 4 | **Trend Insights** | Landscape analysis, gaps, emerging directions |
| 5 | **Reading List Manager** | Save, track status, AI study plan generator |
| 6 | **Citation Generator** | APA / MLA / Chicago / BibTeX in one click |

## 🚀 Quick Start

### 1. Get a Google Gemini API Key
Go to https://aistudio.google.com/app/apikey and create a free API key.

### 2. Install & Run
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux

# Add your key to .env
GOOGLE_API_KEY=AIza...your_key_here...

# Run the app
python run.py
```

### 3. Open in Browser
```
http://localhost:5000
```

## 📁 Project Structure
```
researchpilot/
├── backend/
│   └── app.py          # Flask API (6 endpoints)
├── frontend/
│   └── index.html      # Full UI (HTML/CSS/JS)
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

## 🔑 Environment Variables
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## 📡 API Endpoints
| Method | Endpoint | Feature |
|--------|----------|---------|
| POST | `/api/search` | Search ArXiv papers |
| POST | `/api/summarize` | AI paper summarization |
| POST | `/api/chat` | Research chat assistant |
| POST | `/api/insights` | Trend analysis |
| GET/POST/DELETE | `/api/reading-list` | Reading list CRUD |
| POST | `/api/reading-list/organize` | AI study plan |
| POST | `/api/cite` | Citation generation |

## 🛠 Tech Stack
- **Backend**: Python, Flask, Google Gemini API, ArXiv API
- **Frontend**: HTML5, CSS3, Vanilla JS
- **AI Model**: gemini-2.5-flash
