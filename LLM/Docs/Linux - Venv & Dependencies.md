# **Virtual Environments & Dependencies – Cheat Sheet (Linux)**

## **1. Check & Install Python**

1. **Check if Python is installed:**

   ```bash
   python3 --version
   ```

2. **If not installed**, use your distro’s package manager (e.g., Ubuntu/Debian):

   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-pip
   ```

---

## **2. Create & Activate a Virtual Environment**

1. **Go to your project folder:**

   ```bash
   cd /path/to/your/project
   ```

2. **Create the virtual environment:**

   ```bash
   python3 -m venv .venv
   ```

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

**Use this cheat sheet to keep Python environments on Linux clean, consistent, and easy to maintain.**
