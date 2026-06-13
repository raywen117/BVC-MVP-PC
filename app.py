import streamlit as st
import sqlite3
import requests
import pandas as pd  # For reading the Excel file

# Initialize local SQLite database file
conn = sqlite3.connect("metadata_catalog.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tickets 
             (id INTEGER PRIMARY KEY, question TEXT, answer TEXT, status TEXT, location TEXT)''')
conn.commit()

# Page layout configuration
st.set_page_config(layout="wide", page_title="Company H Data Catalog MVP")
st.title("📦 Meta-Knowledge System (MVP Sandbox)")
st.write("Isolated prototype to showcase our idea in practice")

# UI Navigation Tabs
tab1, tab2 = st.tabs(["Dashboard & Ticket Entry", "🤖 AI Copilot Simulator"])

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
                # DEDUPLICATION CHECK: See if manual ticket already exists
                c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", (q, a, loc))
                duplicate = c.fetchone()
                
                if not duplicate:
                    c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, ?, ?)", (q, a, status, loc))
                    conn.commit()
                    st.success("Knowledge logged successfully!")
                else:
                    st.warning("⚠️ This exact entry already exists in the database. Skipped to prevent duplicates.")
                
                st.rerun()
        
        # --- PART B: EXCEL FILE UPLOAD ---
        st.write("---") # Visual horizontal line as separator
        st.subheader("📊 Import Excel Data")
        st.write("Simulate Excel file access by uploading it (creates tickets/cards from data rows; only use small files)")
        uploaded_file = st.file_uploader("Drop Excel file here", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("🚀 Start Bulk Import", key="process_excel_btn"):
                try:
                    with st.spinner("Parsing, cleaning, and deduplicating rows..."):
                        # Read the file using pandas
                        df = pd.read_excel(uploaded_file)
                        
                        inserted_count = 0
                        skipped_count = 0
                        
                        # Loop through rows and translate the automotive columns into text cards (tickets) for the AI
                        for index, row in df.iterrows():
                            # 1. Pull real data out of the specific Excel column headers
                            manufacturer = str(row.get("VP: Manufacturer Group", "Unknown Manufacturer"))
                            region = str(row.get("VP: Region", "Unknown Region"))
                            country = str(row.get("VP: Country/Territory", "Unknown Country"))
                            propulsion = str(row.get("E: Propulsion System Design", "N/A"))
                            battery = str(row.get("EP: Battery Type", "N/A"))
                            voltage = str(row.get("EP: System Voltage", "N/A"))
                            motor_supplier = str(row.get("T: Manufacturer", "N/A"))
                            vol_2024 = str(row.get("Vehicle Volume 2024", "0"))
                            vol_2027 = str(row.get("Vehicle Volume 2027", "0"))
                            
                            # 2. Stitch together into meaningful Title and Description
                            question = f"Specifications and volume overview for {manufacturer} ({country})"
                            answer = f"This vehicle uses an {propulsion} design equipped with a {battery} battery operating at {voltage}V. The transmission/motor components are supplied by {motor_supplier}. Current 2024 production volume is {vol_2024} units, projected to scale to {vol_2027} units by 2027."
                            location = f"Global Automotive Catalog -> Region: {region}"
                            
                            # 3. DEDUPLICATION CHECK: Look up row contents before saving
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
                            
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error reading Excel file. Ensure it has data. Details: {e}")
                
    with col2:
        st.header("Corporate Data Knowledge Base")
        st.write("e.g. Microsoft Lists or SharePoint Online *(Showing latest 50 entries)*")
        
        data = c.execute("SELECT id, question, answer, location, status FROM tickets ORDER BY id DESC LIMIT 50").fetchall()
        
        if data:
            for row in data:
                ticket_id = row[0]  # The unique database ID for this specific card
                icon = "✅" if row[4] == "Resolved" else "⏳"
                
                with st.expander(f"{icon} [{row[4].upper()}] {row[1]}"):
                    st.write(f"**Answer/Context:** {row[2] if row[2] else '*No solution yet. Team is investigating.*'}")
                    st.write(f"**Technical Location:** `{row[3] if row[3] else 'Unknown / Unmapped'}`")
                    
                    # Small visual separator line inside the card
                    st.write("---")
                    
                    # Delete Button
                    if st.button("🗑️ Delete Entry", key=f"del_{ticket_id}"):
                        c.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
                        conn.commit()
                        st.success("Entry deleted!")
                        st.rerun()
        else:
            st.info("The knowledge base is currently empty. Log a manual ticket or instruct the AI assistant to map data.")

# --- TAB 2: AI COPILOT SIMULATOR ---
# --- TAB 2: AI COPILOT SIMULATOR ---
with tab2:
    st.header("Ask or Train the Assistant")
    st.write("This workspace simulates how Microsoft Copilot parses the logged solutions to answer employee questions natively.")
    user_query = st.text_input("Ask a data question, or explicitly tell the AI to log new details:")

    if user_query:
        # OPTIMIZED: Extract keywords from user query to pull only relevant context rows from SQL
        # This keeps the context window clean and prevents Ollama from timing out
        keywords = user_query.split()
        search_conditions = []
        params = []
        
        for word in keywords:
            if len(word) > 2:  # Ignore short words like 'in', 'to', 'the'
                search_conditions.append("(question LIKE ? OR answer LIKE ? OR location LIKE ?)")
                params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])
        
        if search_conditions:
            query_where = " AND " + " AND ".join(search_conditions)
            query_str = f"SELECT question, answer, location FROM tickets WHERE status='Resolved' {query_where} LIMIT 15"
            knowledge_entries = c.execute(query_str, params).fetchall()
        else:
            # Fallback if query is too short: just grab the 10 most recent entries
            knowledge_entries = c.execute("SELECT question, answer, location FROM tickets WHERE status='Resolved' ORDER BY id DESC LIMIT 10").fetchall()
            
        context_str = "\n".join([f"Question: {row[0]} | Answer: {row[1]} | Location: {row[2]}" for row in knowledge_entries])
        
        # Enhanced few-shot prompt giving Llama 3.2 an exact template match to follow
        system_prompt = (
            f"You are the Data Copilot for Company H. Use the following corporate meta-knowledge context to answer inquiries:\n{context_str}\n\n"
            f"CRITICAL RULE FOR LOGGING DATA:\n"
            f"If the user tells you to save, map, or log where a specific dataset or table is located, you must extract the values and output exactly this text block structure, replacing the examples with their data:\n\n"
            f"EXAMPLE OF HOW YOU MUST OUTPUT:\n"
            f"[START_LOG]\n"
            f"QUESTION: Location of the marketing reports\n"
            f"ANSWER: Stored inside the Salesforce marketing cloud platform\n"
            f"LOCATION: Salesforce Marketing Cloud\n"
            f"[END_LOG]\n\n"
            f"Do not write 'Not provided' or 'None' if the user provided the details in their input. Extract the information accurately. Do not include conversational text before or after the tags."
        )

        try:
            with st.spinner("Analyzing corporate knowledge base..."):
                # OPTIMIZED: Increased timeout to 90 seconds to account for local token generation processing times
                response = requests.post(
                    "http://localhost:11434/api/generate", 
                    json={"model": "llama3.2", "prompt": system_prompt + "\n\nUser Input: " + user_query, "stream": False},
                    timeout=90
                )
                ai_text = response.json().get("response", "").strip()
            
            # Text-parsing logic
            if "[START_LOG]" in ai_text:
                try:
                    log_content = ai_text.split("[START_LOG]")[1].split("[END_LOG]")[0].strip()
                    lines = log_content.split("\n")
                    q_data, a_data, loc_data = "AI Logged Data", "Automatically indexed", "Unspecified"
                    
                    for line in lines:
                        if line.startswith("QUESTION:"):
                            q_data = line.replace("QUESTION:", "").strip()
                        elif line.startswith("ANSWER:"):
                            a_data = line.replace("ANSWER:", "").strip()
                        elif line.startswith("LOCATION:"):
                            loc_data = line.replace("LOCATION:", "").strip()
                    
                    # DEDUPLICATION CHECK: Check if the AI's parsed entry is already in the database
                    c.execute("SELECT id FROM tickets WHERE question = ? AND answer = ? AND location = ?", (q_data, a_data, loc_data))
                    if c.fetchone() is None:
                        c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, 'Resolved', ?)", 
                                  (q_data, a_data, loc_data))
                        conn.commit()
                        
                        st.success("🤖 **Agentic Action Triggered:** Llama 3.2 successfully updated the SQL Knowledge Base!")
                        st.write(f"**Saved Question:** {q_data}")
                        st.write(f"**Saved Answer:** {a_data}")
                        st.write(f"**Saved Location:** `{loc_data}`")
                    else:
                        st.info("🤖 **Agentic Action:** Llama 3.2 identified this meta-knowledge, but it already exists in the database. Entry skipped to prevent duplication.")
                        
                except Exception as parse_error:
                    st.error(f"The AI tried to save data but formatted it slightly wrong. Try rephrasing. Details: {parse_error}")
                    st.text("AI raw text output was:")
                    st.code(ai_text)
            else:
                st.info("🤖 **Copilot Assistant Response:**")
                st.write(ai_text)
                
        except Exception as e:
            st.error(f"Could not reach Ollama. Verify your background service is active. Error: {e}")
