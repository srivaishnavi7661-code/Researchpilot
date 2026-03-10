# 🔬 ResearchPilot

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Made with Love](https://img.shields.io/badge/made%20with-❤️-red.svg)

> **An AI-powered web app that helps researchers find, summarize, and organize academic papers — faster than ever.**

---

## 📋 Table of Contents

- [About](#about)
- [Installation](#installation)
- [Usage & Examples](#usage--examples)
- [Contributing](#contributing)
- [License](#license)

---

## 🧠 About

**ResearchPilot** is a modern web application designed to supercharge your research workflow. Powered by AI, it helps you:

- 🔍 **Find** relevant academic papers across multiple sources
- 📄 **Summarize** lengthy papers into digestible insights
- 🗂️ **Organize** your research library in one place
- 💡 **Discover** related topics and citation networks

Whether you're a student, academic, or curious mind — ResearchPilot saves you hours of manual searching and reading.

---

## 🚀 Installation

### Prerequisites

Make sure you have the following installed:

- [Node.js](https://nodejs.org/) (v18 or higher)
- [npm](https://www.npmjs.com/) or [yarn](https://yarnpkg.com/)
- A modern web browser

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/researchpilot.git
   cd researchpilot
   ```

2. **Install dependencies**

   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and fill in your API keys:

   ```env
   VITE_API_KEY=your_api_key_here
   VITE_BASE_URL=https://api.researchpilot.com
   ```

4. **Start the development server**

   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. **Open your browser** and navigate to `http://localhost:5173`

---

## 💡 Usage & Examples

### Searching for Papers

Type a topic or research question into the search bar and hit **Enter**:

```
Search: "transformer models in natural language processing"
```

ResearchPilot will return a ranked list of relevant papers with AI-generated summaries.

### Summarizing a Paper

Paste a paper URL or upload a PDF:

```
Input: https://arxiv.org/abs/1706.03762
Output: A concise 3-paragraph summary with key findings highlighted
```

### Organizing Your Library

- Click **Save** on any paper to add it to your personal library
- Use **Tags** to categorize papers by topic, project, or status
- Export your library as a `.bib` or `.csv` file for use in other tools

### Example Workflow

```
1. Enter research topic → "climate change machine learning"
2. Browse AI-ranked results
3. Click a paper → read the AI summary
4. Save relevant papers to your library
5. Export citations for your manuscript
```

---

## 🤝 Contributing

Contributions are welcome and appreciated! Here's how to get started:

1. **Fork** the repository
2. **Create** a new branch for your feature

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make** your changes and commit them

   ```bash
   git commit -m "feat: add your feature description"
   ```

4. **Push** to your fork

   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** on GitHub

### Guidelines

- Follow the existing code style
- Write clear, descriptive commit messages
- Add tests for new features where applicable
- Update documentation as needed

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/your-username/researchpilot/issues) — we'd love to hear from you!

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 ResearchPilot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

See the full [LICENSE](./LICENSE) file for details.

---

<p align="center">Built with ❤️ by the ResearchPilot team · <a href="https://github.com/your-username/researchpilot">GitHub</a></p>
