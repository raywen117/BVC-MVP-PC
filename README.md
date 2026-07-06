# BVC-MVP-PC with Ollama+VSCode

## 🛠️ System Architecture Stack
* **Frontend UI:** Streamlit
* **Database Layer:** SQLite3
* **Local AI Engine:** Ollama running Llama 3.2

---

## 1. Install and Run Llama 3.2 then Ensure Local Model is Downloaded
Run in standard Windows Command Prompt or PowerShell:
```ollama run llama3.2```
(Once the download finishes and ">>>" prompt is shown, close with /bye)
Then drop app.py file into the (new) project folder.

## 2. Setup & Execution Sequence in VSCode terminal
Initialize fresh environment
```python -m venv venv```

Activate it
```.\venv\Scripts\Activate.ps1```

If restriction error occurs run this then re-try activation: 
```Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process```

### Install requirements
```pip install streamlit requests```    
```pip install pandas openpyxl```

### Start MVP
```streamlit run app.py``` Or ```.\venv\Scripts\python.exe -m streamlit run app.py```
### Stop MVP
Press CTRL+C in terminal
