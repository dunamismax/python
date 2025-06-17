# **A Master Prompt Sequence for Building CodeBin (Revised by Maximus)**

This sequence methodically constructs the application, ensuring adherence to the Four Pillars.

## **Phase 1: Project Scaffolding & Environment**

**Objective:** Establish a pristine development environment using `uv`, define the project structure, and lock the precise dependency tree.

---

### **Step 1: Initialize the Environment & Version Control**

**Prompt:**
"You will now initialize the project directory, git repository, and Python environment using the `uv` toolchain.

**Execute the following commands:**

```sh
# 1. Create and enter the project directory
mkdir CodeBin
cd CodeBin

# 2. Initialize a Git repository
git init

# 3. Install and pin the project's Python version
uv python install 3.12
uv python pin 3.12

# 4. Create the virtual environment
uv venv --python 3.12

# 5. Create the source and test directory structure
mkdir -p src/codebin tests
```

Next, create the `pyproject.toml` file. This is the canonical definition of our project."

---

### **Step 2: Define Project Metadata & Dependencies (`pyproject.toml`)**

**Prompt:**
"Create the `pyproject.toml` file in the project root. This file defines the project's metadata and dependencies. It is the single source of truth for the build system.

**Requirements:**

* Populate the `[project]` table with the specified metadata.
* List runtime dependencies in the `dependencies` array.
* List all development and testing tools in `[project.optional-dependencies.test]`. This is non-negotiable.
* Configure the `ruff` linter and formatter, and the `ty` type checker in the `[tool.*]` sections.

**File Content: `pyproject.toml`**

```toml
[project]
name = "codebin"
version = "1.0.0"
description = "A minimalist, modern, and secure web service for sharing code snippets."
authors = [{ name = "dunamismax", email = "your-email@example.com" }]
license = { text = "MIT" }
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "aiosqlite",
    "pydantic",
    "pydantic-settings",
    "jinja2",
    "pygments",
    "python-multipart",
    "structlog"
]

[project.urls]
Homepage = "https://github.com/dunamismax/CodeBin"
Repository = "https://github.com/dunamismax/CodeBin"

[project.optional-dependencies]
test = [
    "pytest",
    "pytest-asyncio",
    "httpx",
    "ruff",
    "ty"
]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "C90", "N", "D"]

[tool.ty]
check_untyped_defs = true
disallow_untyped_defs = true
```"

---

#### **Step 3: The Lock-and-Sync Protocol**

**Prompt:**
"Adhere to the Lock-and-Sync Protocol. We do not install dependencies directly. We compile a lockfile and sync the environment from it to ensure absolute reproducibility.

**Execute the following `uv` commands:**

```sh
# 1. Compile ALL dependencies (base + test) into a lockfile
uv pip compile pyproject.toml --all-extras -o requirements.txt

# 2. Sync the virtual environment from the lockfile
uv pip sync requirements.txt
```

The `requirements.txt` lockfile must be committed to version control. The environment is now pristine and reproducible."

---

## **Phase 2: Schemas & Core Services**

**Objective:** Define the application's data contracts with Pydantic and build the foundational, self-contained business logic for security, configuration, and services.

---

### **Step 4: Create Pydantic Schemas (`src/codebin/schemas/paste.py`)**

**Prompt:**
"Create the file `src/codebin/schemas/paste.py`. This module is the single source of truth for our data shapes, using Pydantic V2 for validation. Adhere strictly to the file header and docstring conventions. All code must pass `ty check`.

**Requirements:**

1. Import necessary types from `pydantic` and `datetime`.
2. `PasteBase`: For shared fields (`content`, `language`). `content` must have a `min_length` of 1.
3. `PasteCreate`: Inherits from `PasteBase`, used for new paste creation.
4. `PasteInDB`: Represents the full record in the database, including `slug`, `created_at`, and an optional `expires_at`.
5. `PasteRead`: The model for data returned to the client, containing `highlighted_content` and `created_at`."

---

### **Step 5: Implement Configuration Management (`src/codebin/core/config.py`)**

**Prompt:**
"Create the file `src/codebin/core/config.py`. All configuration **MUST** be loaded from environment variables into a Pydantic `BaseSettings` model. Hardcoding configuration is a critical failure.

**Requirements:**

1. Import `BaseSettings` from `pydantic_settings`.
2. Create a `Settings` class inheriting from `BaseSettings`.
3. Define settings with type hints and default values:
    * `DATABASE_URL`: `str`, e.g., `"sqlite+aiosqlite:///codebin.db"`.
    * `LOG_LEVEL`: `str`, default `"INFO"`.
    * `APP_TITLE`: `str`, default `"CodeBin"`.
4. Instantiate a single, exported `settings` object: `settings = Settings()`."

---

### **Step 6: Implement Secure Slug Generation (`src/codebin/core/security.py`)**

**Prompt:**
"Create the file `src/codebin/core/security.py`. Its purpose is to generate unique, URL-safe identifiers for our pastes using cryptographically secure methods.

**Requirements:**

1. Import the `secrets` module.
2. Create a function `generate_secure_slug(n_bytes: int = 8) -> str`.
3. The function must use `secrets.token_urlsafe()` to generate the identifier.
4. The function must be fully type-hinted and have a Google-style docstring."

---

### **Step 7: Implement Syntax Highlighting Service (`src/codebin/services/highlighting.py`)**

**Prompt:**
"Create the file `src/codebin/services/highlighting.py`. This module will safely convert raw code into highlighted HTML on the server to prevent XSS.

**Requirements:**

1. Import necessary modules from `pygments`.
2. Create a function `highlight_code(content: str, language: str) -> str`.
3. Use a `try...except ClassNotFound` block to safely get a lexer, defaulting to `"plaintext"`.
4. Use `HtmlFormatter` with `noclasses=True` to generate inline styles, simplifying the frontend.
5. The function must be fully type-hinted and documented."

---

## **Phase 3: Data Persistence Layer**

**Objective:** Define the database schema and implement the Repository Pattern for all data access logic using raw, asynchronous SQL queries.

---

### **Step 8: Create the Database Management Module (`src/codebin/db/database.py`)**

**Prompt:**
"Create `src/codebin/db/database.py` to manage the database connection and schema initialization.

**Requirements:**

1. Import `aiosqlite` and the `settings` object from `src.codebin.core.config`.
2. The database path must come from `settings.DATABASE_URL`, not a hardcoded constant.
3. Create an async function `get_db_connection()` that returns an `aiosqlite.Connection`.
4. Create an async function `initialize_database()` that connects and executes a `CREATE TABLE IF NOT EXISTS pastes` query.
5. The table schema must be: `slug` (TEXT, PRIMARY KEY), `content` (TEXT NOT NULL), `language` (TEXT NOT NULL), `created_at` (TIMESTAMP NOT NULL), `expires_at` (TIMESTAMP).
6. This function is critical for application startup."

---

### **Step 9: Create the Asynchronous Paste Repository (`src/codebin/db/repository.py`)**

**Prompt:**
"Create the file `src/codebin/db/repository.py`. This module implements the Repository Pattern and is the *only* part of the application that executes SQL queries.

**Requirements:**

1. Import `aiosqlite`, `datetime`, all Pydantic schemas, and the `generate_secure_slug` function.
2. Create a class `AsyncPasteRepository`.
3. Implement `async def create(self, db: aiosqlite.Connection, paste: PasteCreate) -> PasteInDB`:
    * Generates a slug, `created_at` timestamp, and `expires_at` (can be null).
    * Executes a raw, parameterized `INSERT` query.
    * Commits the transaction.
    * Returns the full `PasteInDB` object.
4. Implement `async def get_by_slug(self, db: aiosqlite.Connection, slug: str) -> PasteInDB | None`:
    * Executes a raw, parameterized `SELECT` query for the given slug.
    * The query **MUST** filter out expired pastes (`WHERE slug = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)`).
    * If a row is found, map it to a `PasteInDB` model and return it. Otherwise, return `None`.
5. Implement `async def delete_expired(self, db: aiosqlite.Connection) -> int`:
    * Executes a raw `DELETE` query to remove all pastes where `expires_at` is in the past.
    * Returns the number of rows affected."

---

## **Phase 4: Frontend & API Assembly**

**Objective:** Construct the user interface using pure HTML/HTMX/CSS, build the FastAPI router to serve the application, and assemble the final service.

---

### **Step 10: Create the HTMX Frontend Templates**

**Prompt:**
"You will now create the two required HTML files in the `src/codebin/templates/` directory. These templates, powered by Jinja2, will render the entire user interface.

**1. Create the main application shell: `src/codebin/templates/index.html`**

* This is the master template. It must include the basic HTML5 document structure.
* In the `<head>`, link to the `style.css` file and include the HTMX library script directly from its official CDN (`<script src="https://unpkg.com/htmx.org@1.9.12"></script>`).
* The `<body>` must contain a `<header>`, a `<main>` area, and a `<footer>`.
* The `<main>` section must contain the `<form>` for submitting new pastes.
  * The form's `action` and `method` attributes are irrelevant for HTMX; remove them.
  * Add the following HTMX attributes to the `<form>` tag: `hx-post="/"` `hx-target="#paste-container"` `hx-swap="innerHTML"`.
  * The form must have a `<textarea name="content">` and an `<input type="text" name="language">`.
* Below the form, create a `div` with `id="paste-container"`. This is the target for HTMX swaps.
* This template must conditionally render a paste. Use a Jinja2 `{% if paste %}` block. If a `paste` object is passed in the context, `{% include 'paste_view.html' %}` inside the `#paste-container` div.

**2. Create the paste display fragment: `src/codebin/templates/paste_view.html`**

* This is an HTML *fragment*, not a full document. It is designed to be injected by HTMX or included by Jinja2.
* It must accept a `paste` object from the template context.
* It must display the syntax-highlighted code. Use `<pre><code>{{ paste.highlighted_content | safe }}</code></pre>` to render the pre-formatted HTML without escaping.
* Include metadata such as the language used and the creation date (`{{ paste.created_at.strftime('%Y-%m-%d %H:%M:%S') }} UTC`)."

---

### **Step 11: Create the Minimalist Stylesheet**

**Prompt:**
"Create the application's stylesheet at `src/codebin/static/style.css`. Implement a clean, modern, dark-themed design. The styling should be minimal and focus on readability.

**Requirements:**

1. Set a dark background color and light text color on the `body`.
2. Use a system font stack for performance and a native feel.
3. Style the `form`, `textarea`, `input`, and `button` elements for a consistent look.
4. Ensure the `<pre>` and `<code>` blocks used for displaying code are styled for maximum readability, with appropriate padding and font settings. The colors for syntax highlighting are handled by inline styles from Pygments, so no specific theme classes are needed."

---

### **Step 12: Create the FastAPI API Router**

**Prompt:**
"Create the API router at `src/codebin/api/router.py`. This module defines all HTTP endpoints and handles the core application logic of request and response.

**Requirements:**

1. Import `APIRouter`, `Request`, `Depends`, `Form`, and `HTTPException` from `fastapi`, and `HTMLResponse` from `fastapi.responses`. Import `Jinja2Templates`.
2. Import the `AsyncPasteRepository`, `get_db_connection`, all Pydantic schemas, and the `highlight_code` service.
3. Instantiate an `APIRouter`, `Jinja2Templates`, and the `AsyncPasteRepository`.
4. Create a `GET /{slug}` endpoint for viewing a specific paste via its permalink.
    * It must accept a `slug: str` path parameter.
    * It will fetch the paste using `repository.get_by_slug`. If not found, raise a 404 `HTTPException`.
    * If found, it will highlight the code and create a `PasteRead` model.
    * It must render the full `index.html` template, passing the `paste` object to the context. This allows a shared URL to render the complete page with the paste pre-loaded.
5. Create a combined `GET /` and `POST /` endpoint. This single endpoint will handle both initial page loads and HTMX form submissions.
    * Use the `@router.api_route("/", methods=["GET", "POST"])` decorator.
    * **For a POST request (the HTMX submission):**
        * Accept `content: str = Form()` and `language: str = Form()`.
        * Create a `PasteCreate` object and save it using the repository.
        * Highlight the new paste's content.
        * Create a `PasteRead` model.
        * Return an `HTMLResponse` containing only the rendered `paste_view.html` fragment. This response will be swapped into the `#paste-container` div by HTMX.
    * **For a GET request (the initial page load):**
        * Render the `index.html` template without any paste data.
6. Ensure all database operations use a connection from the `get_db_connection` dependency."

---

### **Step 13: Assemble the Main Application**

**Prompt:**
"Create the main application entry point at `src/codebin/main.py`. This file ties all components together, configures logging, and manages the application lifecycle.

**Requirements:**

1. Adhere to all file header and docstring standards.
2. Import `FastAPI`, `Request`, `StaticFiles`, and `structlog`.
3. Import the API router, `initialize_database`, and `settings`.
4. Configure `structlog` for structured JSON logging. This is a non-negotiable requirement for observability.
5. Create the `FastAPI` app instance.
6. Mount the `static` directory to serve `style.css`.
7. Include the API router using `app.include_router()`.
8. Create an `@app.on_event("startup")` asynchronous function that calls `await initialize_database()`.
9. Add a comment placeholder for a future background task to run `repository.delete_expired()` periodically.

    ```python
    # TODO: Implement a background task scheduler (e.g., Apscheduler)
    # to periodically call repository.delete_expired().
    ```

---

## **Phase 5: Verification & Finalization**

**Objective:** Write comprehensive tests for the core logic and API endpoints. Finalize the project with standard repository files and perform a final quality check.

---

### **Step 14: Write Repository Unit Tests**

**Prompt:**
"Create the test file `tests/test_repository.py` to unit-test the data access layer in complete isolation.

**Requirements:**

1. Create `tests/conftest.py` first. Define a `pytest` fixture named `db_connection` that yields a fresh, in-memory `aiosqlite` connection and runs `initialize_database()` on it for each test function.
2. In `tests/test_repository.py`, use the `db_connection` fixture. Mark tests with `@pytest.mark.asyncio`.
3. Write `test_create_and_get_paste`: Creates a `PasteCreate` object, calls `repository.create`, then calls `repository.get_by_slug` and asserts the retrieved data is correct.
4. Write `test_get_nonexistent_paste`: Asserts that `repository.get_by_slug` returns `None` for a slug that does not exist.
5. Write `test_expired_paste_is_not_retrieved`: Creates a paste with an expiration date in the past, and asserts that `repository.get_by_slug` returns `None`."

---

### **Step 15: Write API Integration Tests**

**Prompt:**
"Create the integration test file `tests/test_api.py`. Test the live API endpoints using `httpx`.

**Requirements:**

1. Use `pytest` and `httpx.AsyncClient` against the main `app` instance.
2. Write `test_get_root_page`: Sends a GET to `/` and asserts a 200 status code and that the response HTML contains the submission form.
3. Write `test_create_paste_htmx`:
    * Sends a POST to `/` with form data (`content`, `language`).
    * Asserts a 200 status code.
    * Asserts that the response body is an HTML fragment containing the submitted code within `<pre><code>` tags.
4. Write `test_get_paste_by_permalink`:
    * First, programmatically create a paste using the repository to have a known slug.
    * Send a GET to `/{slug}` using the known slug.
    * Assert a 200 status code and that the full response HTML contains the pasted code."

---

### **Step 16: Create Final Project Files**

**Prompt:**
"Create the final administrative files for the repository.

1. **`.gitignore`**: Create a comprehensive Python `.gitignore` file. It must include entries for `.venv`, `__pycache__`, `*.db`, `*.db-journal`, `dist`, `build`, `*.egg-info`, `.pytest_cache`, `.ruff_cache`, and `.ty-cache`.
2. **`LICENSE`**: Create a `LICENSE` file containing the full text of the MIT License. The copyright year must be current, and `dunamismax` must be the copyright holder."

---

### **Step 17: Final Quality Assurance Check**

**Prompt:**
"The project is now structurally complete. The final step is to verify its integrity against our quality pillars. Execute the following commands from the project root. The project is not considered complete until all commands pass with zero errors.

**Execute the following commands:**

```sh
# 1. Format all code with Ruff
uvx ruff format .

# 2. Lint all code with Ruff and apply automatic fixes
uvx ruff check --fix .

# 3. Perform strict static type checking with ty
uvx ty

# 4. Run the entire test suite with pytest
uvx pytest
```

If any of these commands fail, the corresponding issue must be resolved before proceeding. There is no compromise on code quality."
