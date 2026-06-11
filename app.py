import streamlit as st
import sqlite3
import requests

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
        st.header("Log New Meta-Knowledge")
        st.write("e.g. Microsoft Forms or Power Apps")
        with st.form("ticket_form", clear_on_submit=True):
            q = st.text_input("User Question / Data Needed", placeholder="e.g., Where is the 2025 sales data for product X?")
            a = st.text_area("Answer / Resolution", placeholder="Leave blank if unknown or open...")
            loc = st.text_input("Storage Location / System", placeholder="e.g., SharePoint / SAP table / Snowflake prod cluster")
            status = st.selectbox("Status", ["Open", "Resolved"])
            submitted = st.form_submit_button("Submit Entry")
            
            if submitted and q:
                c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, ?, ?)", (q, a, status, loc))
                conn.commit()
                st.success("Knowledge logged successfully!")
                st.rerun()
                
    with col2:
        st.header("Corporate Data Knowledge Base")
        st.write("e.g. Microsoft Lists or SharePoint Online")
        data = c.execute("SELECT id, question, answer, location, status FROM tickets").fetchall()
        if data:
            for row in data:
                icon = "✅" if row[4] == "Resolved" else "⏳"
                with st.expander(f"{icon} [{row[4].upper()}] {row[1]}"):
                    st.write(f"**Answer/Context:** {row[2] if row[2] else '*No solution yet. Team is investigating.*'}")
                    st.write(f"**Technical Location:** `{row[3] if row[3] else 'Unknown / Unmapped'}`")
        else:
            st.info("The knowledge base is currently empty. Log a manual ticket or instruct the AI assistant to map data.")

# --- TAB 2: AI COPILOT SIMULATOR ---
with tab2:
    st.header("Ask or Train the Assistant")
    st.write("This workspace simulates how Microsoft Copilot parses the logged solutions to answer employee questions natively.")
    user_query = st.text_input("Ask a data question, or explicitly tell the AI to log new details:")

    if user_query:
        # Pull resolved metadata to pass as context for RAG
        knowledge_entries = c.execute("SELECT question, answer, location FROM tickets WHERE status='Resolved'").fetchall()
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
                response = requests.post(
                    "http://localhost:11434/api/generate", 
                    json={"model": "llama3.2", "prompt": system_prompt + "\n\nUser Input: " + user_query, "stream": False},
                    timeout=30
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
                    
                    # Write clean extracted values to SQL
                    c.execute("INSERT INTO tickets (question, answer, status, location) VALUES (?, ?, 'Resolved', ?)", 
                              (q_data, a_data, loc_data))
                    conn.commit()
                    
                    st.success("🤖 **Agentic Action Triggered:** Llama 3.2 successfully updated the SQL Knowledge Base!")
                    st.write(f"**Saved Question:** {q_data}")
                    st.write(f"**Saved Answer:** {a_data}")
                    st.write(f"**Saved Location:** `{loc_data}`")
                except Exception as parse_error:
                    st.error(f"The AI tried to save data but formatted it slightly wrong. Try rephrasing. Details: {parse_error}")
                    st.text("AI raw text output was:")
                    st.code(ai_text)
            else:
                st.info("🤖 **Copilot Assistant Response:**")
                st.write(ai_text)
                
        except Exception as e:
            st.error(f"Could not reach Ollama. Verify your background service is active. Error: {e}")