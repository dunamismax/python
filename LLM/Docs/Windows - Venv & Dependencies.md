# **Virtual Environments & Dependencies – Cheat Sheet (Windows)**

## **1. Installing Python on Windows**

1. **Download & Install**
   - Visit [python.org/downloads](https://www.python.org/downloads/)
   - Download the latest stable release (e.g., Python 3.12.x).
   - Run the installer and **check** “Add Python to PATH” to ensure you can use `python` from the command prompt or PowerShell.

2. **Verify Installation**

   ```powershell
   python --version
   pip --version
   ```

   - These commands should confirm your Python and `pip` versions are recognized.

---

## **2. Creating a Virtual Environment (venv)**

1. **Navigate to Your Project Folder**

   ```powershell
   cd C:\path\to\your\project
   ```

2. **Create the venv**

   ```powershell
   python -m venv .venv
   ```

3. **Activate the Environment**

   ```powershell
   .\.venv\Scripts\activate
   ```

   - Notice your prompt now shows `(.venv)` to indicate the environment is active.

4. **Deactivate the Environment**

   ```powershell
   deactivate
   ```

---

## **3. Installing and Managing Dependencies**

1. **Install Dependencies from requirements.txt**

   ```powershell
   pip install -r requirements.txt
   ```

2. **Add or Update a Dependency**

   ```powershell
   pip install requests
   ```

   - After installing/updating, save the new state to `requirements.txt`:

     ```powershell
     pip freeze > requirements.txt
     ```

3. **Reinstall Dependencies**
   - If you need to recreate your `.venv`, just `pip install -r requirements.txt` again to restore all packages.

---

## **4. Best Practices**

1. **Isolation**
   - Always create a **new** virtual environment for each project to avoid conflicting package versions.

2. **Version Control**
   - **Commit** your `requirements.txt` so all team members install the same dependency versions.
   - **Ignore** the `.venv` folder in your version control. Typically, you add `.venv/` to `.gitignore`.

3. **Reproducibility**
   - By using a virtual environment and `requirements.txt`, you ensure consistent environments across various machines and CI/CD pipelines.

4. **Upgrades**
   - Periodically run `pip list --outdated` inside your virtual environment to see which dependencies need updating.

---

### **Use this cheat sheet to maintain clean, isolated Python environments on Windows, ensuring reproducible builds and hassle-free dependency management.**
