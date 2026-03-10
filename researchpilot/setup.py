"""
ResearchPilot AI Agent - Package Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    requirements = [l.strip() for l in f if l.strip() and not l.startswith("#")]

setup(
    name="researchpilot",
    version="1.0.0",
    author="ResearchPilot Team",
    description="Autonomous Research Intelligence Hub powered by Claude AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "researchpilot=researchpilot.cli:app_cli",
            "rp=researchpilot.cli:app_cli",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_data={
        "researchpilot": ["ui/**/*", "*.md"],
    },
    keywords="research, papers, AI, arxiv, academic, LLM, Claude, Anthropic",
)
