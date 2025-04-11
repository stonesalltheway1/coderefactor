#!/usr/bin/env python
"""Setup script for the CodeRefactor package."""

import os
from setuptools import setup, find_packages

# Read the requirements from each file
def read_requirements(filename):
    """Read requirements from a file and return a list."""
    requirements = []
    if os.path.exists(os.path.join("requirements", filename)):
        with open(os.path.join("requirements", filename), encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)
    return requirements

# Read the README file
with open("README.md", encoding="utf-8") as readme_file:
    readme = readme_file.read()

setup(
    name="coderefactor",
    version="1.0.0",
    description="Advanced code analysis and refactoring tool",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="CodeRefactor Team",
    author_email="info@coderefactor.dev",
    url="https://github.com/Stonesalltheway1/coderefactor",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    package_data={
        "coderefactor": [
            "web/templates/*.html",
            "web/static/css/*.css",
            "web/static/js/*.js",
            "web/static/img/*",
        ],
    },
    entry_points={
        "console_scripts": [
            "coderefactor=coderefactor.cli.commands:main",
        ],
    },
    python_requires=">=3.8",
    install_requires=read_requirements("base.txt"),
    extras_require={
        "dev": read_requirements("dev.txt"),
        "docs": read_requirements("docs.txt"),
        "test": read_requirements("test.txt"),
        "web": ["flask>=2.0.0", "flask-cors>=3.0.10"],
        "csharp": ["pythonnet>=3.0.0"],
        "llm": ["anthropic>=0.8.0", "aiohttp>=3.8.0"],
        "all": read_requirements("base.txt") + 
               read_requirements("dev.txt") + 
               read_requirements("docs.txt") + 
               read_requirements("test.txt") +
               ["flask>=2.0.0", "flask-cors>=3.0.10", 
                "pythonnet>=3.0.0", "anthropic>=0.8.0", "aiohttp>=3.8.0"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    keywords="code, analysis, refactoring, static analysis, linting, fixing, quality",
    project_urls={
        "Bug Reports": "https://github.com/Stonesalltheway1/coderefactor/issues",
        "Source": "https://github.com/Stonesalltheway1/coderefactor",
        "Documentation": "https://coderefactor.readthedocs.io/",
    },
)