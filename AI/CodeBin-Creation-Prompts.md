# **A Master Prompt Sequence for Building CodeBin**

Here are the step-by-step instructions.

## **Phase 1: Foundation & Data Modeling**

**Objective:** Establish the project's dependencies and define the core data contracts (schemas) that will govern all data exchange within the application.

---

### **Step 1: Create the Project Definition File (`pyproject.toml`)**

**Prompt:**
"You will now create the `pyproject.toml` file. This file will define the project's metadata and its dependencies using the poetry toolchain format.

**Requirements:**

1. **Project Name:** `codebin`
2. **Version:** `1.0.0`
3. **Description:** "A minimalist, modern, and secure web service for sharing code snippets."
4. **Author:** `dunamismax`
5. **License:** `MIT`
6. **Python Version:** `>=3.12`
7. **Main Dependencies:**
    * `fastapi`
    * `uvicorn[standard]`
    * `aiosqlite`
    * `pydantic`
    * `jinja2`
    * `pygments` (for syntax highlighting)
    * `python-multipart` (for form handling)
8. **Development Dependencies (dev-group):**
    * `pytest`
    * `pytest-asyncio`
    * `httpx` (for testing the API)
    * `ruff`
    * `mypy`"

---

### **Step 2: Create the Pydantic Schemas (`src/codebin/schemas/paste.py`)**

**Prompt:**
"You will now create the file `src/codebin/schemas/paste.py`. This module is the single source of truth for our data shapes, using Pydantic for validation. Adhere strictly to the file header and docstring conventions.

**Requirements:**

1. Import `BaseModel` and `Field` from `pydantic`, and `datetime` from `datetime`.
2. Create a `PasteBase` model containing:
    * `content`: `str`, must not be empty. Use `Field(min_length=1)`.
    * `language`: `str`, with a default value of `"plaintext"`.
3. Create a `PasteCreate` model that inherits from `PasteBase`. This will be used for incoming form data.
4. Create a `PasteInDB` model that inherits from `PasteBase`. This represents the data as stored in the database and must include:
    * `slug`: `str`
    * `created_at`: `datetime`
    * `expires_at`: `datetime | None`
5. Create a `PasteRead` model, also inheriting from `PasteBase`. This model is for data returned to the client and must contain:
    * `highlighted_content`: `str`. This field will hold the server-rendered, syntax-highlighted HTML.
    * `created_at`: `datetime`"

---

## **Phase 2: Core Logic & Services**

**Objective:** Build the self-contained business logic and utility functions required by the application, specifically slug generation and syntax highlighting.

---

### **Step 3: Create the Secure Slug Generator (`src/codebin/core/security.py`)**

**Prompt:**
"Create the file `src/codebin/core/security.py`. Its purpose is to generate unique, URL-safe identifiers for our pastes.

**Requirements:**

1. Adhere to the file header and docstring standards.
2. Import the `secrets` module.
3. Create a single function `generate_secure_slug(n_bytes: int = 8) -> str`.
4. This function must use `secrets.token_urlsafe()` to generate a cryptographically secure, URL-safe string.
5. The function must be fully type-hinted and have a clear Google-style docstring."

---

### **Step 4: Create the Syntax Highlighting Service (`src/codebin/services/highlighting.py`)**

**Prompt:**
"Create the file `src/codebin/services/highlighting.py`. This module will be responsible for safely converting raw code into highlighted HTML on the server-side to prevent XSS.

**Requirements:**

1. Adhere to the file header and docstring standards.
2. Import `HtmlFormatter` from `pygments.formatters`, `get_lexer_by_name` and `ClassNotFound` from `pygments.lexers`, and `highlight` from `pygments`.
3. Create a single function `highlight_code(content: str, language: str) -> str`.
4. Inside the function, use a `try...except` block to get the appropriate lexer with `get_lexer_by_name(language)`. If `ClassNotFound` is raised, default to the `plaintext` lexer.
5. Use `HtmlFormatter` with the options `noclasses=True` and `style="dracula"` to generate inline styles, which simplifies our CSS.
6. Use the `highlight` function with the content, lexer, and formatter to generate the final HTML.
7. The function must be fully type-hinted and documented."

---

## **Phase 3: Database & Repository**

**Objective:** Define the database connection, create the schema, and implement the Repository Pattern for all data access logic using raw, asynchronous SQL.

---

### **Step 5: Create the Database Management Module (`src/codebin/db/database.py`)**

**Prompt:**
"You will now create `src/codebin/db/database.py` to manage the database connection and initial schema setup.

**Requirements:**

1. Adhere to the file header and docstring standards.
2. Import `aiosqlite`.
3. Define a constant `DATABASE_URL = "codebin.db"`.
4. Create an async function `get_db_connection() -> aiosqlite.Connection` that connects to the database and returns the connection object.
5. Create an async function `initialize_database()`. This function will:
    * Connect to the database using `get_db_connection`.
    * Execute a raw SQL query: `CREATE TABLE IF NOT EXISTS pastes (...)`.
    * The table schema must include: `slug` (TEXT, PRIMARY KEY), `content` (TEXT), `language` (TEXT), `created_at` (TIMESTAMP), `expires_at` (TIMESTAMP, NULLABLE).
    * Commit the transaction and close the connection.
    * This function is crucial for application startup."

---

### **Step 6: Create the Asynchronous Paste Repository (`src/codebin/db/repository.py`)**

**Prompt:**
"Create the file `src/codebin/db/repository.py`. This implements the Repository Pattern and will be the *only* module that interacts directly with the database.

**Requirements:**

1. Adhere to the file header and docstring standards.
2. Import `aiosqlite`, `datetime`, and the Pydantic models from `src.codebin.schemas.paste`. Also import `generate_secure_slug` from `src.codebin.core.security`.
3. Create a class `AsyncPasteRepository`.
4. Implement the `async def create_paste(self, db: aiosqlite.Connection, paste: PasteCreate) -> str` method:
    * Generate a new slug using `generate_secure_slug`.
    * Calculate `created_at` and `expires_at` (for now, you can set expiration to a fixed time, like 1 day, or None).
    * Use a raw, parameterized `INSERT` SQL query to insert the new paste.
    * Commit the transaction.
    * Return the generated slug.
5. Implement the `async def get_paste_by_slug(self, db: aiosqlite.Connection, slug: str) -> PasteInDB | None` method:
    * Use a raw, parameterized `SELECT` query to fetch a paste by its slug.
    * The query must also filter out expired pastes (`expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP`).
    * If a row is found, map it to the `PasteInDB` schema and return it. Otherwise, return `None`.
6. Implement the `async def delete_expired_pastes(self, db: aiosqlite.Connection) -> int` method:
    * Use a raw `DELETE` SQL query to remove all pastes where `expires_at` is not null and is in the past.
    * Return the number of rows deleted."

---

## **Phase 4: Frontend & API Assembly**

**Objective:** Create the HTML templates and CSS, build the FastAPI router to serve them, and assemble the final application in `main.py`.

---

### **Step 7: Create the HTML Templates (`index.html`, `paste_view.html`)**

**Prompt:**
"Now, create two HTML files in the `src/codebin/templates/` directory.

**1. `index.html`:**

* This is the main page.
* It must contain a `<form>` for submitting a new paste.
* The form `action` should be `/create` and the `method` should be `POST`.
* Crucially, add the HTMX attributes: `hx-post="/create"`, `hx-target="#paste-result"`, `hx-swap="innerHTML"`.
* The form should have a `<textarea name="content">` and an `<input type="text" name="language">`.
* Include a `div` with `id="paste-result"` where the new paste view will be loaded.

**2. `paste_view.html`:**

* This is an HTML *fragment*, not a full page.
* It should take a `paste` object as context.
* Display the syntax-highlighted code inside `<pre><code>...</code></pre>` tags. Use `{{ paste.highlighted_content | safe }}` to render the HTML.
* Include a simple header showing the language and creation time."

---

### **Step 8: Create the Stylesheet (`src/codebin/static/style.css`)**

**Prompt:**
"Create a simple stylesheet at `src/codebin/static/style.css`. Provide some clean, minimalist styling for a modern dark theme. Style the `body`, `form`, `textarea`, `input`, `button`, and the `pre`/`code` blocks for displaying the paste."

---

### **Step 9: Create the API Router (`src/codebin/api/router.py`)**

**Prompt:**
"Create the API router at `src/codebin/api/router.py`. This file will define all HTTP endpoints for the application.

**Requirements:**

1. Import `APIRouter`, `Request`, `Depends`, `Form`, `HTTPException` from `fastapi`, and `HTMLResponse`, `RedirectResponse` from `fastapi.responses`. Import `Jinja2Templates`.
2. Import the repository and schemas. Import the `highlight_code` service. Import `get_db_connection`.
3. Instantiate an `APIRouter()` and `Jinja2Templates(directory="src/codebin/templates")`.
4. Create a `GET /` endpoint that renders `index.html`.
5. Create a `POST /create` endpoint for the HTMX form submission:
    * It must take `content: str = Form(...)` and `language: str = Form(...)`.
    * It will create a `PasteCreate` schema from the form data.
    * Use a `Depends` on `get_db_connection` to get a database connection.
    * Use the `AsyncPasteRepository` to save the new paste.
    * After saving, it must immediately redirect the browser to the new paste's URL (`/{slug}`). Use `RedirectResponse` with status code 303 and set an `HX-Redirect` header to the new URL.
6. Create a `GET /{slug}` endpoint:
    * It will fetch the paste using the repository.
    * If the paste is not found, raise a 404 `HTTPException`.
    * If found, use the `highlight_code` service to get the highlighted HTML.
    * Create a `PasteRead` model with the data.
    * Render the `paste_view.html` template fragment, passing the `PasteRead` model as context.
    * **This endpoint will render the *full page view* now.** Modify this endpoint to render `index.html`, but also pass the paste data to it. `index.html` will then conditionally render the `paste_view.html` fragment within itself.
    "

---

### **Step 10: Revision - Update `index.html` for Viewing Pastes**

**Prompt:**
"We need to revise `src/codebin/templates/index.html`. The `GET /{slug}` endpoint will now render the full `index.html` page and pass paste data to it.

**Requirements:**

1. Modify `index.html` to accept an optional `paste` object.
2. Use a Jinja2 `if paste:` block.
3. If `paste` exists, `include 'paste_view.html'` in the `#paste-result` div."

---

### **Step 11: Create the Main Application (`src/codebin/main.py`)**

**Prompt:**
"Finally, create the main application entry point at `src/codebin/main.py`.

**Requirements:**

1. Adhere to all file standards.
2. Import `FastAPI` and other necessary components.
3. Import the API router from `api.router`.
4. Import `initialize_database`, `get_db_connection` and the `AsyncPasteRepository`.
5. Create the `FastAPI` app instance.
6. Mount the static files directory.
7. Include the API router.
8. Create an `@app.on_event("startup")` event handler that calls `await initialize_database()`.
9. (Advanced) Set up a background task using `fastapi.BackgroundTasks` or a library like `apscheduler` to periodically call the `delete_expired_pastes` repository method. For simplicity in this prompt, you can skip the scheduler and just add a comment placeholder for where it would go."

---

## **Phase 5: Testing & Finalization**

**Objective:** Write comprehensive tests for our core logic and finalize the project with standard repository files.

---

### **Step 12: Write Repository Unit Tests (`tests/test_repository.py`)**

**Prompt:**
"Create the test file `tests/test_repository.py`. We will write unit tests for our data layer against an in-memory SQLite database.

**Requirements:**

1. Use `pytest` and `pytest-asyncio`.
2. Create a test fixture to provide a fresh, in-memory `aiosqlite` connection for each test.
3. Write a test `test_create_and_get_paste` that:
    * Creates a `PasteCreate` object.
    * Calls `repository.create_paste`.
    * Calls `repository.get_paste_by_slug` with the returned slug.
    * Asserts that the retrieved paste is not `None` and its content matches the original."

---

### **Step 13: Write API Integration Tests (`tests/test_api.py`)**

**Prompt:**
"Create the integration test file `tests/test_api.py`. We will test the live API endpoints using `httpx`.

**Requirements:**

1. Use `pytest` and `httpx.AsyncClient`.
2. Write a test `test_get_root` that sends a GET to `/` and asserts a 200 status code and that the response contains `<form>`.
3. Write a test `test_create_and_view_paste` that:
    * Sends a POST to `/create` with valid form data.
    * Asserts the response is a 303 redirect.
    * Follows the redirect URL from the `HX-Redirect` header.
    * Asserts the final response is 200 and contains the pasted code inside a `<pre>` block."

---

### **Step 14: Final Project Files (`.gitignore`, `LICENSE`)**

**Prompt:**
"Create the final project files:

1. A comprehensive Python `.gitignore` file. Include common entries for `.venv`, `__pycache__`, `*.db`, `mypy_cache`, and `.pytest_cache`.
2. A `LICENSE` file containing the full text of the MIT License, with the copyright year and `dunamismax` as the copyright holder."

---

This sequence of prompts will methodically construct the entire application, ensuring quality, consistency, and adherence to the architectural vision. I am ready to begin execution at your command.
