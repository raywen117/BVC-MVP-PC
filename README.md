# BVC-MVP-PC with Ollama+VSCode

## 🛠️ System Architecture Stack
* **Frontend UI:** Streamlit (Python rapid prototyping framework)
* **Database Layer:** SQLite3 (Embedded local relational database)
* **Local AI Engine:** Ollama running Llama 3.2 (3-Billion parameter lightweight model)

---

## 1. Ensure Local Model is Downloaded
Run in standard Windows Command Prompt or PowerShell:
```ollama run llama3.2```
(Once the download finishes and ">>>" prompt is shown, close with /bye)
Then drop app.py file into the (new) project folder.

## 2. Setup & Execution Sequence in VSCode terminal
# Initialize fresh environment
```python -m venv venv```

### Activate it (If you get a script execution error, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process)
```.\venv\Scripts\Activate.ps1```
If restriction error occurs run this then re-try: 
```Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process```

### Install requirements
```pip install streamlit requests```

### Start MVP
```streamlit run app.py```
