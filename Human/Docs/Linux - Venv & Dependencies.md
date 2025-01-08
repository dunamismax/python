# **Virtual Environments & Dependencies – Cheat Sheet (Linux)**

## **1. Install and Manage Python with Pyenv**

1. **Install pyenv**
   Follow the official [pyenv GitHub instructions](https://github.com/pyenv/pyenv#installation) to install pyenv on your Linux distribution. Typically, you’ll:
   - Install required dependencies (build tools, libraries, etc.).
   - Clone the pyenv repository.
   - Add pyenv initialization to your shell (`.bashrc`, `.zshrc`, etc.).

2. **Install a specific Python version using pyenv**

   ```bash
   # List all available Python versions
   pyenv install --list

   # Install a specific version (example: 3.13.1)
   pyenv install 3.13.1
   ```

3. **Set global or local Python version**
   - **Global (system-wide default)**

     ```bash
     pyenv global 3.13.1
     ```

   - **Local (per-project)**

     ```bash
     cd /path/to/your/project
     pyenv local 3.13.1
     ```

   - Confirm with:

     ```bash
     python --version
     ```

---

## **2. Create & Activate a Virtual Environment**

> **Tip**: Now that pyenv is managing your Python versions, any `python` or `python3` references below will use the version(s) you set with pyenv.

1. **Go to your project folder:**

   ```bash
   cd /path/to/your/project
   ```

2. **Create the virtual environment:**

   ```bash
   python -m venv .venv
   ```

   > This uses the Python version managed by pyenv (either the local or global one you chose).

3. **Activate the environment:**

   ```bash
   source .venv/bin/activate
   ```

   - Your prompt now shows `(.venv)` to indicate activation.

4. **Deactivate the environment:**

   ```bash
   deactivate
   ```

---

## **3. Manage Dependencies**

1. **Install from requirements.txt:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Add or update a package:**

   ```bash
   pip install requests
   ```

   - Then update your `requirements.txt`:

     ```bash
     pip freeze > requirements.txt
     ```

3. **Recreate dependencies** if you rebuild your `.venv`:

   ```bash
   pip install -r requirements.txt
   ```

---

## **4. Best Practices**

- **Isolation**: Use a fresh virtual environment per project to avoid conflicts.
- **Version Control**:
  - Commit `requirements.txt` for consistent dependencies.
  - Ignore the `.venv` folder (`.venv/` in `.gitignore`).
- **Upgrades**: Check for outdated packages:

  ```bash
  pip list --outdated
  ```

---

**Use this cheat sheet to maintain clean, consistent Python environments on Linux—powered by pyenv for flexible version management.**
