import os
import sqlite3
import glob
import pandas as pd

DB_FILE = "metadata_catalog.db"

# --- CONFIGURATION FOR LEAN MVP ---
MAX_ROWS_PER_FILE = 5  # Number of random rows to pull from each file

CHOSEN_COLUMNS = [
    "VP: Manufacturer Group",
    "VP: Production Brand",
    "VP: Production Nameplate",
    "E: Fuel Type",
    "EP: Battery Type",
    "Component Volume 2027",
    "Vehicle Volume 2027"
]

def detect_separator(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
            if ";" in first_line:
                return ";"
    except Exception:
        pass
    return ","

def seed_database_from_any_csv():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT, status TEXT, location TEXT)''')

    c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_dedup ON tickets (question)")

    csv_files = glob.glob("*.csv")
    
    if not csv_files:
        print("ℹ No CSV files found in this folder. Skipping auto-seeding.")
        conn.close()
        return

    for file_path in csv_files:
        print(f"Discovered file: {file_path}. Processing...")
        sep = detect_separator(file_path)
        
        try:
            df = pd.read_csv(file_path, sep=sep)
            df.columns = [str(col).strip() for col in df.columns]
            
            # --- MODIFIED: RANDOM SAMPLING ---
            # Ensures we don't crash if a file has fewer rows than MAX_ROWS_PER_FILE
            sample_size = min(MAX_ROWS_PER_FILE, len(df))
            
            # random_state=42 ensures you get the exact same "random" rows every time you run it.
            # This keeps your presentation data stable and predictable!
            df = df.sample(n=sample_size, random_state=42)
            
            inserted_count = 0
            skipped_count = 0
            
            for index, row in df.iterrows():
                details_list = []
                
                for col in CHOSEN_COLUMNS:
                    if col in df.columns:
                        val = str(row[col]).strip()
                        if val and val.lower() != "nan" and val.lower() != "none":
                            details_list.append(f"**{col}**: {val}")
                
                if not details_list:
                    continue
                    
                brand = str(row.get("VP: Production Brand", "Unknown")).strip()
                model = str(row.get("VP: Production Nameplate", "Model")).strip()
                
                question = f"What is the market forecast and drivetrain architecture for the {brand} {model}?"
                answer = " | ".join(details_list)
                location = f"Market Forecasting Database -> Archive: {os.path.basename(file_path)}"
                
                c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", 
                          (question, answer, location))
                
                if c.fetchone() is None:
                    c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, 'Resolved', ?)", 
                              (question, answer, location))
                    inserted_count += 1
                else:
                    skipped_count += 1
            
            conn.commit()
            print(f"Finished '{file_path}': Loaded {inserted_count} random rows. (Skipped {skipped_count} duplicates).")
            
        except Exception as e:
            print(f" Failed to parse '{file_path}'. Error: {e}")
            
    conn.close()
    print("All available CSV data sources have been synchronized with the knowledge base.")

if __name__ == "__main__":
    seed_database_from_any_csv()