# Now please review my project info and take it all into context:

## 1. Project: "CodeBin" - A Modern, HTMX-Powered Pastebin

* **Core Concept:** A minimalist and secure web service for sharing code snippets, built with a FastAPI backend and a hyper-dynamic HTMX frontend. It will prioritize simplicity, performance, and security.

* **Key Learning Opportunities:**
  * **FastAPI:** Building a robust, asynchronous API with path parameters (for paste retrieval) and Pydantic-based request bodies (for paste submission).
  * **HTMX:** Mastering zero-javascript frontend development. The form submission, "copy to clipboard" functionality, and display of new pastes will all be handled via HTMX attributes.
  * **Raw SQL & Repository Pattern:** Implementing a repository to handle the `CREATE` and `READ` operations for pastes using `aiosqlite` (for simplicity) or `asyncpg` (for production-grade performance). You will handle generating unique, short URLs for each paste and manage automatic expiration.
  * **Security:** Using Pydantic for strict input validation on the paste content and settings. Implementing server-side syntax highlighting to avoid XSS vulnerabilities common in client-side highlighters.
  * **Testing:** Writing `pytest` unit tests for the API endpoints and repository logic, ensuring paste creation and retrieval work as expected.

* **Architectural Blueprint:**
  * **Backend:** FastAPI application.
  * **Schemas:** Pydantic models for `PasteCreate` (content, language, expiration) and `PasteRead` (content, language, creation\_date).
  * **Repository:** An `AsyncPasteRepository` class with methods like `create_paste` and `get_paste_by_slug`, using parameterized, raw SQL queries.
  * **Frontend:** A single HTML file with templates for the main page and the "paste view" fragment, dynamically updated by HTMX.

---

<div align="center">
<pre>
______          __     ____  _
  / ____/___  ____/ /__  / __ )(_)___
 / /   / __ \/ __  / _ \/ __  / / __ \
/ /___/ /_/ / /_/ /  __/ /_/ / / / / /
\____/\____/\__,_/\___/_____/_/_/ /_/
</pre>
</div>

<p align="center">
  CodeBin is a minimalist, modern, and secure web service for sharing code snippets.
  <br />
  It is built with a high-performance FastAPI backend and a dynamic, zero-JavaScript HTMX frontend.
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Language-Python_3.12+-blue.svg" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/Backend-FastAPI-009688.svg" alt="FastAPI"></a>
    <a href="https://htmx.org/"><img src="https://img.shields.io/badge/Frontend-HTMX-3498DB.svg" alt="HTMX"></a>
  <a href="https://github.com/dunamismax/CodeBin/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/dunamismax/CodeBin/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square" alt="PRs Welcome"></a>
  <a href="https://github.com/dunamismax/CodeBin/stargazers"><img src="https://img.shields.io/github/stars/dunamismax/CodeBin?style=social" alt="GitHub Stars"></a>
</p>

---

## ✨ Guiding Philosophy

CodeBin is built on a few core principles:

* **Simplicity by Design**: We prioritize a clean, uncluttered user experience. The goal is to make sharing code instantaneous and effortless, without unnecessary features.
* **Modern & Performant Backend**: We leverage the full power of the modern Python ecosystem. The asynchronous FastAPI framework, combined with raw `asyncpg` or `aiosqlite` queries, ensures a non-blocking and highly efficient backend.
* **Zero-JavaScript Frontend**: We believe in the power of hypermedia. The entire user interface is rendered on the server and made dynamic with **HTMX**, resulting in a lightweight, fast, and accessible frontend without a single line of client-side JavaScript.
* **Security First**: All user input is treated as untrusted. We use Pydantic for rigorous data validation and raw, parameterized SQL queries to eliminate the risk of SQL injection. Syntax highlighting is performed securely on the server to prevent XSS vulnerabilities.

---

## 🚀 Getting Started

You will need Python 3.12+ and a C compiler for some of the dependencies.

### 1. Environment Setup

It is highly recommended to use a virtual environment.

```sh
# Clone the repository
git clone https://github.com/dunamismax/CodeBin.git
cd CodeBin

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

# Install project dependencies
pip install -e .
```

### 2. Database Initialization

The application uses an SQLite database by default, which will be created automatically. For production use, you would configure a PostgreSQL database.

### 3. Run the Development Server

With your virtual environment activated, run the application using `uvicorn`.

```sh
# The --reload flag enables hot-reloading for development
uvicorn codebin.main:app --reload
```

Navigate to `http://127.0.0.1:8000` in your browser. You should see the CodeBin interface, ready to accept new pastes.

---

## 🏗️ Project Structure

CodeBin is organized using a clean, scalable structure that separates concerns.

```sh
codebin/
├── .gitignore
├── pyproject.toml
├── README.md
├── src/
│   └── codebin/
│       ├── __init__.py
│       ├── api/
│       │   └── router.py           # FastAPI router for all paste-related endpoints.
│       ├── core/
│       │   └── security.py         # Utility functions for generating secure slugs.
add config.py here!
│       ├── db/
│       │   ├── database.py         # Database connection management and schema initialization.
│       │   └── repository.py       # The AsyncPasteRepository for all database operations.
│       ├── main.py                 # Main application entry point.
│       ├── schemas/
│       │   └── paste.py            # Pydantic models for paste data.
│       ├── services/
│       │   └── highlighting.py     # Server-side syntax highlighting logic.
│       ├── static/
│       │   └── style.css           # Vanilla CSS for styling.
│       └── templates/
│           ├── index.html          # Main HTML template with the submission form.
│           └── paste_view.html     # HTML fragment for displaying a paste.
└── tests/
    ├── conftest.py             # Pytest fixtures, e.g., for a test database.
    ├── test_api.py             # Integration tests for the FastAPI endpoints.
    └── test_repository.py      # Unit tests for the database repository logic.
```

---

## 🤝 Contribute

**CodeBin is built by the community, for the community. We need your help!**

Whether you're a seasoned Python developer or a web enthusiast looking for an exciting open-source project, there are many ways to contribute:

* **Report Bugs:** Find something broken? [Open an issue](https://github.com/dunamismax/CodeBin/issues) and provide as much detail as possible.
* **Suggest Features:** Have a great idea for a new feature or a better API? [Start a discussion](https://github.com/dunamismax/CodeBin/discussions) or open a feature request issue.
* **Write Code:** Grab an open issue, a bug, or implement a new feature. [Submit a Pull Request](https://github.com/dunamismax/CodeBin/pulls) and we'll review it together.
* **Improve Documentation:** Great documentation is as important as great code. Help us make our guides and examples clearer and more comprehensive.

If this project excites you, please **give it a star!** ⭐ It helps us gain visibility and attract more talented contributors like you.

### Connect

Connect with the author, **dunamismax**, on:

* **Twitter:** [@dunamismax](https://twitter.com/dunamismax)
* **Bluesky:** [@dunamismax.bsky.social](https://bsky.app/profile/dunamismax.bsky.social)
* **Reddit:** [u/dunamismax](https://www.reddit.com/user/dunamismax)
* **Discord:** `dunamismax`
* **Signal:** `dunamismax.66`

## 📜 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

The project structure and actual file names and locations can be changed if needed during the process of creating this project.

Do not generate any code or files yet simply ask for direction.
