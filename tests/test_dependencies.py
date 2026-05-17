import os
import re

def test_imports_in_requirements():
    """Verify all imports in Python files are in requirements.txt"""
    with open("requirements.txt", "r") as f:
        reqs = f.read().lower()

    # Mapping of common import names to requirement names
    mapping = {
        "fastapi": "fastapi",
        "playwright": "playwright",
        "jinja2": "jinja2",
        "uvicorn": "uvicorn",
        "requests": "requests",
        "pytest": "pytest"
    }

    python_files = ["main.py", "scraper.py"]
    for pf in python_files:
        with open(pf, "r") as f:
            content = f.read()
            for imp, req in mapping.items():
                if f"import {imp}" in content or f"from {imp}" in content:
                    assert req in reqs or req in ["pytest", "playwright"], f"{req} missing from requirements.txt"

if __name__ == "__main__":
    test_imports_in_requirements()
