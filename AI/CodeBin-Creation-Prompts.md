# **A Master Prompt Sequence for Building CodeBin**

**Author:** dunamismax
**Version:** 2.0.0
**Date:** 2025-06-17

---

## **Phase 1: Project Initialization & Configuration**

**Objective:** Atomically generate the complete project skeleton, environment configuration, and dependency definitions.

---

### **Prompt 1: Generate Foundational Project Files**

**Directive:**
Generate the foundational files for the CodeBin project. Create the directory structure and the following files with the specified content. These files define the project's metadata, dependencies, license, and version control ignores.

**1. Directory Structure:**

```sh
CodeBin/
├── .gitignore
├── LICENSE
├── pyproject.toml
└── src/
    └── codebin/
        ├── api/
        ├── core/
        ├── db/
        ├── schemas/
        ├── services/
        ├── static/
        └── templates/
```

**2. File: `pyproject.toml`**

```toml
# pyproject.toml
[project]
name = "codebin"
version = "1.0.0"
description = "A minimalist, modern, and secure web service for sharing code snippets."
authors = [{ name = "dunamismax", email = "dunamismax@users.noreply.github.com" }]
license = { text = "MIT" }
readme = "README.md"
requires-python = ">=3.12"
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: FastAPI",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

# Core runtime dependencies
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "aiosqlite",
    "pydantic",
    "pydantic-settings",
    "jinja2",
    "pygments",
    "python-multipart",
    "structlog",
    "fastapi-htmx",
]

[project.urls]
Homepage = "https://github.com/dunamismax/CodeBin"
Repository = "https://github.com/dunamismax/CodeBin"
Issues = "https://github.com/dunamismax/CodeBin/issues"

# Tool configuration for the UV ecosystem
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [ "E", "W", "F", "I", "D", "UP", "B", "A", "C4", "SIM", "RUF" ]
ignore = ["D100", "D104", "D107"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "lf"
```

**3. File: `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.venv/
venv/

# Database
*.db
*.db-journal
*.sqlite
*.sqlite3

# Build artifacts
build/
dist/
*.egg-info/
*.egg

# Caches
.pytest_cache/
.ruff_cache/
.ty-cache/

# IDE
.idea/
.vscode/
```

**4. File: `LICENSE`**

```text
MIT License

Copyright (c) 2025 dunamismax

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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## **Phase 2: Core Services & Data Schemas**

**Objective:** Define data contracts using Pydantic and implement self-contained business logic.

---

### **Prompt 2: Generate Pydantic Schemas**

**Directive:**
Create the file `src/codebin/schemas/paste.py`. This module defines all data models for the application, enforcing strict validation and immutability. Adhere to all file header and docstring conventions.

---

### **Prompt 3: Generate Configuration Management**

**Directive:**
Create the file `src/codebin/core/config.py`. Configuration must be loaded from environment variables via `pydantic-settings`. Hardcoded secrets or configurations are forbidden.

---

### **Prompt 4: Generate Security Utilities**

**Directive:**
Create the file `src/codebin/core/security.py`. This module provides cryptographically secure functions for generating unique identifiers.

---

### **Prompt 5: Generate Syntax Highlighting Service**

**Directive:**
Create the file `src/codebin/services/highlighting.py`. This service performs secure, server-side syntax highlighting to prevent Cross-Site Scripting (XSS) vulnerabilities.

---

## **Phase 3: Data Persistence Layer**

**Objective:** Implement the database schema and the asynchronous Repository Pattern for all data access.

---

### **Prompt 6: Generate Database Management Module**

**Directive:**
Create the file `src/codebin/db/database.py`. It will manage the database connection pool and handle initial schema creation based on the application's configuration.

---

### **Prompt 7: Generate Asynchronous Repository**

**Directive:**
Create the file `src/codebin/db/repository.py`. This is the sole module responsible for database interaction, using raw, parameterized SQL queries to ensure security and performance.

---

## **Phase 4: API, Frontend, & Assembly**

**Objective:** Construct the user interface, build the API router, and assemble the final application.

---

### **Prompt 8: Generate Frontend Artifacts (HTML/CSS)**

**Directive:**
Create the frontend files. The HTML templates use Jinja2 and HTMX for a dynamic, zero-JavaScript interface. The CSS provides a clean, modern aesthetic.

1. **Create `src/codebin/templates/index.html`**: The main application shell and paste submission form.
2. **Create `src/codebin/templates/paste_view.html`**: The HTMX fragment for displaying a rendered paste.
3. **Create `src/codebin/static/style.css`**: The vanilla CSS stylesheet.

---

### **Prompt 9: Generate FastAPI Router**

**Directive:**
Create the file `src/codebin/api/router.py`. This module defines all API endpoints, handling both initial page loads and HTMX-driven partial page updates.

---

### **Prompt 10: Generate Main Application Entrypoint**

**Directive:**
Create the file `src/codebin/main.py`. This file assembles the FastAPI application, configures structured logging with `structlog`, mounts static files, includes the API router, and manages application lifecycle events.

---

## **Phase 5: Final Verification**

**Objective:** Ensure the generated codebase complies with all quality standards defined in the Four Pillars.

---

### **Prompt 11: Execute Quality Assurance Protocol**

**Directive:**
The final action is to verify project integrity. The following commands must be executed from the project root. The project is complete only when all commands pass without error.

**Execution Commands:**

```sh
# 1. Lock production dependencies from pyproject.toml
uv pip compile pyproject.toml -o requirements.lock

# 2. Sync the virtual environment from the lockfile
uv pip sync requirements.lock

# 3. Format all code with Ruff
uvx ruff format .

# 4. Lint and auto-fix all code with Ruff
uvx ruff check --fix .

# 5. Perform strict static type analysis with Ty
uvx ty .
```

This sequence is now complete and optimized. Awaiting next directive.
