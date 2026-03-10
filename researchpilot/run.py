#!/usr/bin/env python3
"""
ResearchPilot AI Agent - Launcher
"""

import os
import sys
from pathlib import Path

# Add backend directory to path if running from project root
backend_dir = Path(__file__).parent / "backend"
if backend_dir.exists():
    sys.path.insert(0, str(backend_dir))

# Import and run the Flask app
from app import app

if __name__ == "__main__":
    print("🚀 ResearchPilot AI Agent starting...")
    print("🌐 Open: http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')
