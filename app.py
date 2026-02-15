import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = init_db()
    c = conn.cursor()
    # Table 1: Your activity logs
    c.execute('''CREATE TABLE IF NOT EXISTS punch_list 
                 (id INTEGER PRIMARY KEY, date TEXT, category TEXT, 
                  item TEXT, status TEXT, impact TEXT)''')
    # Table 2: Your master calendar guidelines (The New Part)
    c.execute('''CREATE TABLE IF NOT EXISTS master_calendar 
                 (id INTEGER PRIMARY KEY, frequency TEXT, system TEXT, 
                  task TEXT, instructions TEXT)''')
    conn.commit()
    return conn

# --- APP LAYOUT ---
st.set_page_config(page_title="Workbench Group | Estate OS", layout="wide")
st.title("Stewardship Portal: 3739 Knollwood Dr")

tab1, tab2, tab3 = st.tabs(["Weekly Field Entry", "Master Maintenance Calendar", "Executive Scorecard"])

with tab1:
    st.header("Field Audit & Punch List")
    with st.form("audit_entry"):
        col1, col2 = st.columns(2)
        with col1:
            cat = st.selectbox("System Category", ["Mechanical", "Envelope", "Aesthetics", "Safety"])
            item = st.text_input("Observation/Task")
        with col2:
            stat = st.selectbox("Current Status", ["Resolved", "Pending", "Needs Attention"])
            impact = st.select_slider("Impact on Asset Health", options=["Low", "Medium", "High"])
        
        if st.form_submit_button("Log Weekly Finding"):
            c = conn.cursor()
            c.execute("INSERT INTO punch_list (date, category, item, status, impact) VALUES (?,?,?,?,?)",
                      (datetime.now().strftime("%Y-%m-%d"), cat, item, stat, impact))
            conn.commit()
            st.success("Finding logged to Estate History.")

    st.markdown("### Recent Activity")
    history = pd.read_sql("SELECT date, category, item, status FROM punch_list ORDER BY id DESC LIMIT 5", conn)
    st.table(history)
    
with tab2:
    st.header("52-Week Stewardship Guidelines")
    
    # --- FORM TO ADD NEW TASKS ---
    with st.expander("➕ Add New Guideline Task"):
        with st.form("new_calendar_task"):
            f_freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Bi-Annual", "Annual"])
            f_sys = st.selectbox("System", ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"])
            f_task = st.text_input("Task Name")
            f_inst = st.text_area("Special Instructions")
            
            if st.form_submit_button("Save to Master Calendar"):
                c = conn.cursor()
                c.execute("INSERT INTO master_calendar (frequency, system, task, instructions) VALUES (?,?,?,?)",
                          (f_freq, f_sys, f_task, f_inst))
                conn.commit()
                st.success("Guideline Added!")

    # --- DISPLAY THE CALENDAR FROM DATABASE ---
    st.markdown("---")
    cal_df = pd.read_sql("SELECT frequency, system, task, instructions FROM master_calendar", conn)
    
    if not cal_df.empty:
        # Sort so users see logical grouping
        st.table(cal_df.sort_values(by="Frequency"))
    else:
        st.info("Your calendar is currently empty. Use the form above to add your first task.")
    
with tab3:
    st.header(f"Executive Scorecard: {datetime.now().strftime('%B %Y')}")
    all_data = pd.read_sql("SELECT * FROM punch_list", conn)
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.success("### 🟢 THE GOOD")
        resolved = all_data[all_data['status'] == 'Resolved']['item'].tolist()
        for i in resolved[-4:]: st.write(f"**Fixed:** {i}")
            
    with col_b:
        st.warning("### 🟡 CAUTION")
        pending = all_data[all_data['status'] == 'Pending']['item'].tolist()
        for i in pending[-4:]: st.write(f"**Monitoring:** {i}")
            
    with col_c:
        st.error("### 🔴 ACTION REQUIRED")
        critical = all_data[all_data['status'] == 'Needs Attention']['item'].tolist()
        for i in critical[-4:]: st.write(f"**Urgent:** {i}")
