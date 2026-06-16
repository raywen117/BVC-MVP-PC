import os
import sqlite3
import glob
import pandas as pd

DB_FILE = "metadata_catalog.db"

def detect_separator(file_path):
    """Sniffs the file to see if it uses a semicolon or a comma as a separator."""
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

    # 1. Look for ANY CSV file in the current project directory
    csv_files = glob.glob("*.csv")
    
    if not csv_files:
        print("ℹNo CSV files found in this folder. Skipping auto-seeding.")
        conn.close()
        return

    # Process every CSV file it discovers
    for file_path in csv_files:
        print(f"Discovered file: {file_path}. Processing...")
        
        # 2. Dynamic Separator Check
        sep = detect_separator(file_path)
        
        try:
            df = pd.read_csv(file_path, sep=sep)
            
            # Clean column names (strip trailing spaces)
            df.columns = [str(col).strip() for col in df.columns]
            
            inserted_count = 0
            skipped_count = 0
            
            # 3. Dynamic Row-by-Row parsing
            for index, row in df.iterrows():
                # Build a dynamic, descriptive answer using whatever headers exist in the file
                details_list = []
                for col in df.columns:
                    val = str(row[col]).strip()
                    if val and val.lower() != "nan":
                        details_list.append(f"**{col}**: {val}")
                
                # If the row is completely empty, skip it
                if not details_list:
                    continue
                    
                # Create a generalized topic title based on the filename and row number
                file_clean_name = os.path.basename(file_path).replace(".csv", "")
                question = f"Data record summary from dataset: '{file_clean_name}' (Record #{index + 1})"
                
                # Join all the columns into a structured markdown block for the LLM context
                answer = " | ".join(details_list)
                location = f"Imported Database Archive -> File: {file_path}"
                
                # 4. Strict Deduplication Check
                c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", 
                          (question, answer, location))
                
                if c.fetchone() is None:
                    c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, 'Resolved', ?)", 
                              (question, answer, location))
                    inserted_count += 1
                else:
                    skipped_count += 1
            
            conn.commit()
            print(f"Finished '{file_path}': Loaded {inserted_count} rows. (Skipped {skipped_count} duplicates).")
            
        except Exception as e:
            print(f" Failed to parse '{file_path}'. Error: {e}")
            
    conn.close()
    print("All available CSV data sources have been synchronized with the knowledge base.")

if __name__ == "__main__":
    seed_database_from_any_csv()