import streamlit as st
import sqlite3
import requests
import pandas as pd  # For reading the Excel file
import re

DB_FILE = "metadata_catalog.db"

# --- THREAD-SAFE DATABASE HELPER FUNCTIONS ---
def get_db_connection():
    """Creates a unique database connection per thread/interaction."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tickets 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT, status TEXT, location TEXT)''')
        conn.commit()

# Initialize database right away
init_db()

# Page layout configuration
st.set_page_config(layout="wide", page_title="Company H Data Catalog MVP")
st.title("Meta-Knowledge System (MVP Sandbox)")
st.write("Isolated prototype to showcase our idea in practice")

# UI Navigation Tabs
tab1, tab2 = st.tabs(["Dashboard & Ticket Entry", "AI Copilot Simulator"])

# --- TAB 1: TICKETING & METADATA ENTRY ---
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # --- PART A: MANUAL Knowledge Entry ---
        st.header("Log New Meta-Knowledge")
        st.write("e.g. Microsoft Forms or Power Apps")
        with st.form("ticket_form", clear_on_submit=True):
            q = st.text_input("User Question / Data Needed", placeholder="e.g., Where is the 2025 sales data for product X?")
            a = st.text_area("Answer / Resolution", placeholder="Leave blank if unknown or open...")
            loc = st.text_input("Storage Location / System", placeholder="e.g., SharePoint / SAP table / Snowflake prod cluster")
            status = st.selectbox("Status", ["Open", "Resolved"])
            submitted = st.form_submit_button("Submit Entry")
            
            if submitted and q:
                with get_db_connection() as conn:
                    c = conn.cursor()
                    # DEDUPLICATION CHECK: See if manual ticket already exists
                    c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", (q, a, loc))
                    duplicate = c.fetchone()
                    
                    if not duplicate:
                        c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, ?, ?)", (q, a, status, loc))
                        conn.commit()
                        st.success("Knowledge logged successfully!")
                    else:
                        st.warning("This exact entry already exists in the database. Skipped to prevent duplicates.")
                st.rerun()
        
        # --- PART B: EXCEL FILE UPLOAD ---
        st.write("---") # Visual horizontal line as separator
        st.subheader("Import Excel Data")
        st.write("Simulate Excel file access by uploading it (creates tickets/cards from data rows; only use small files)")
        uploaded_file = st.file_uploader("Drop Excel file here", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("Start Bulk Import", key="process_excel_btn"):
                try:
                    with st.spinner("Parsing, cleaning, and deduplicating rows..."):
                        df = pd.read_excel(uploaded_file)
                        
                        inserted_count = 0
                        skipped_count = 0
                        
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            # Loop through rows and translate the automotive columns into text cards (tickets) for the AI
                            for index, row in df.iterrows():
                                manufacturer = str(row.get("VP: Manufacturer Group", "Unknown Manufacturer"))
                                region = str(row.get("VP: Region", "Unknown Region"))
                                country = str(row.get("VP: Country/Territory", "Unknown Country"))
                                propulsion = str(row.get("E: Propulsion System Design", "N/A"))
                                battery = str(row.get("EP: Battery Type", "N/A"))
                                voltage = str(row.get("EP: System Voltage", "N/A"))
                                motor_supplier = str(row.get("T: Manufacturer", "N/A"))
                                vol_2024 = str(row.get("Vehicle Volume 2024", "0"))
                                vol_2027 = str(row.get("Vehicle Volume 2027", "0"))
                                
                                question = f"Specifications and volume overview for {manufacturer} ({country})"
                                answer = f"This vehicle uses an {propulsion} design equipped with a {battery} battery operating at {voltage}V. The transmission/motor components are supplied by {motor_supplier}. Current 2024 production volume is {vol_2024} units, projected to scale to {vol_2027} units by 2027."
                                location = f"Global Automotive Catalog -> Region: {region}"
                                
                                c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", (question, answer, location))
                                if c.fetchone() is None:
                                    c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, 'Resolved', ?)", 
                                              (question, answer, location))
                                    inserted_count += 1
                                else:
                                    skipped_count += 1
                            conn.commit()
                        
                        if inserted_count > 0:
                            st.success(f"Successfully imported {inserted_count} new unique rows! (Skipped {skipped_count} duplicates)")
                        else:
                            st.info(f"Import complete. No new data added. All {skipped_count} rows were identical duplicates.")
                
                except Exception as e:
                    st.error(f"Error reading Excel file. Ensure it has data. Details: {e}")
                
    with col2:
        st.header("Corporate Data Knowledge Base")
        st.write("e.g. Microsoft Lists or SharePoint Online *(Showing latest 50 entries)*")
        
        with get_db_connection() as conn:
            c = conn.cursor()
            data = c.execute("SELECT id, question, answer, location, status FROM tickets ORDER BY id DESC LIMIT 50").fetchall()
        
        if data:
            for row in data:
                ticket_id = row[0]
                current_status = row[4]
                icon = "✅" if current_status == "Resolved" else "⏳"
                
                with st.expander(f"{icon} [{current_status.upper()}] {row[1]}"):
                    st.write(f"**Answer/Context:** {row[2] if row[2] else '*No solution yet. Team is investigating.*'}")
                    st.write(f"**Technical Location:** `{row[3] if row[3] else 'Unknown / Unmapped'}`")
                    
                    st.write("---")
                    
                    with st.form(key=f"edit_form_{ticket_id}"):
                        new_answer = st.text_area("Update Answer / Resolution", value=row[2] if row[2] else "")
                        status_index = 0 if current_status == "Open" else 1
                        new_status = st.selectbox("Update Status", ["Open", "Resolved"], index=status_index)
                        
                        col_save, col_empty = st.columns([1, 2])
                        with col_save:
                            if st.form_submit_button("💾 Save Changes"):
                                with get_db_connection() as conn:
                                    c = conn.cursor()
                                    c.execute("UPDATE tickets SET answer = ?, status = ? WHERE id = ?", (new_answer, new_status, ticket_id))
                                    conn.commit()
                                st.success("Ticket updated successfully!")
                                st.rerun()
                    
                    if st.button("🗑️ Delete Entry", key=f"del_{ticket_id}"):
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
                            conn.commit()
                        st.success("Entry deleted!")
                        st.rerun()
        else:
            st.info("The knowledge base is currently empty. Log a manual ticket or instruct the AI assistant to map data.")

# --- TAB 2: AI COPILOT SIMULATOR ---
with tab2:
    st.header("Ask or Train the Assistant")
    st.write("This workspace simulates how Microsoft Copilot parses the logged solutions to answer employee questions natively.")
    user_query = st.text_input("Ask a data question, or explicitly tell the AI to log new details:")

    if user_query:
        with get_db_connection() as conn:
            c = conn.cursor()
            all_resolved = c.execute("SELECT question, answer, location FROM tickets WHERE status='Resolved'").fetchall()
        
        clean_query = re.sub(r'[^\w\s]', '', user_query.lower())
        # Changed len(w) > 1 to capture important acronyms like IT, S3, SAP, UI
        query_words = {w for w in clean_query.split() if len(w) > 1}
        
        scored_entries = []
        for row in all_resolved:
            row_text = f"{row[0]} {row[1]} {row[2]}".lower()
            score = sum(1 for w in query_words if w in row_text)
            scored_entries.append((score, row))
            
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        knowledge_entries = [entry[1] for entry in scored_entries[:15]]
        
        context_str = "\n".join([f"Question: {row[0]} | Answer: {row[1]} | Location: {row[2]}" for row in knowledge_entries])
        
        system_prompt = (
            f"You are the Data Copilot for Company H. Your job is to help employees find where data, machines, and files are located.\n"
            f"NEVER write code (SQL, Python, etc.) to extract data.\n\n"
            f"KNOWLEDGE BASE CONTEXT:\n{context_str}\n\n"
            f"CRITICAL INTENT CLASSIFICATION - CHOOSE EXACTLY ONE SCENARIO:\n\n"
            f"SCENARIO 1 [QUESTION WITH ANSWER]: The user is asking a question, and the answer IS present in the KNOWLEDGE BASE CONTEXT.\n"
            f"- ACTION: Answer the question naturally in plain conversational text based ONLY on the context. DO NOT use the log template.\n\n"
            f"SCENARIO 2 [QUESTION WITHOUT ANSWER]: The user is asking a pure question, the answer is NOT in the context, and the user DID NOT give you the answer in their message.\n"
            f"- ACTION: Say 'I do not have this information' and output the LOG TEMPLATE with STATUS: Open. Leave ANSWER and LOCATION completely blank.\n\n"
            f"SCENARIO 3 [ADD/ENTER KNOWLEDGE]: The user is explicitly instructing you to 'enter', 'add', 'log', 'save', 'store', or 'remember' new information, OR they are providing a factual statement containing both a topic and its location/contact.\n"
            f"- ACTION: Extract the data provided by the user in their query. Output the LOG TEMPLATE with STATUS: Resolved.\n"
            f"- IMPORTANT: Carefully pull the answer details (e.g., contact persons, departments, machines) from the user's prompt and map them to the ANSWER and LOCATION fields. Do not leave them blank.\n\n"
            f"LOG TEMPLATE (Use ONLY for Scenario 2 and Scenario 3):\n"
            f"[START_LOG]\n"
            f"QUESTION: <Summarize the core topic or question being answered>\n"
            f"ANSWER: <The resolution, person, or system details provided by the user>\n"
            f"LOCATION: <The specific department, folder, or machine provided by the user>\n"
            f"STATUS: <Open or Resolved>\n"
            f"[END_LOG]"
        )

        try:
            with st.spinner("Analyzing corporate knowledge base..."):
                response = requests.post(
                    "http://localhost:11434/api/generate", 
                    json={"model": "llama3.2", "prompt": system_prompt + "\n\nUser Input: " + user_query, "stream": False},
                    timeout=90
                )
                ai_text = response.json().get("response", "").strip()
            
            if "[START_LOG]" in ai_text:
                try:
                    log_content = ai_text.split("[START_LOG]")[1].split("[END_LOG]")[0].strip()
                    lines = log_content.split("\n")
                    
                    q_data, a_data, loc_data, status_data = "Unknown Question", "", "", "Open"
                    
                    for line in lines:
                        if line.startswith("QUESTION:"): q_data = line.replace("QUESTION:", "").strip()
                        elif line.startswith("ANSWER:"): a_data = line.replace("ANSWER:", "").strip()
                        elif line.startswith("LOCATION:"): loc_data = line.replace("LOCATION:", "").strip()
                        elif line.startswith("STATUS:"): status_data = line.replace("STATUS:", "").strip()
                    
                    if a_data.lower() in ["", "none", "unknown", "n/a", "not provided"]: a_data = ""
                    if loc_data.lower() in ["", "none", "unknown", "n/a", "not provided"]: loc_data = ""
                    if "open" in status_data.lower(): status_data = "Open"
                    else: status_data = "Resolved"
                    
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", (q_data, a_data, loc_data))
                        if c.fetchone() is None:
                            c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, ?, ?)", 
                                      (q_data, a_data, status_data, loc_data))
                            conn.commit()
                            
                            if status_data == "Open":
                                st.warning(" **Agentic Action:** The AI didn't know the answer, so it automatically created an **Open Ticket**!")
                            else:
                                st.success(" **Agentic Action:** Llama 3.2 successfully updated the SQL Knowledge Base with a **Resolved Ticket**!")
                                
                            st.write(f"**Saved Question:** {q_data}")
                            st.write(f"**Saved Answer:** {a_data if a_data else '*Left blank for human input*'}")
                            st.write(f"**Saved Location:** `{loc_data if loc_data else 'Unknown'}`")
                        else:
                            st.info("🤖 **Agentic Action:** Llama 3.2 identified this meta-knowledge, but it already exists in the database.")
                        
                except Exception as parse_error:
                    st.error(f"The AI tried to save data but formatted it slightly wrong. Try rephrasing. Details: {parse_error}")
                    st.text("AI raw text output was:")
                    st.code(ai_text)
            else:
                st.info(" **Copilot Assistant Response:**")
                st.write(ai_text)
                
        except Exception as e:
            st.error(f"Could not reach Ollama. Verify your background service is active. Error: {e}")