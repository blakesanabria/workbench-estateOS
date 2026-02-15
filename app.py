import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('workbench_estate.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS punch_list 
                 (id INTEGER PRIMARY KEY, date TEXT, category TEXT, 
                  item TEXT, status TEXT, impact TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- APP LAYOUT ---
st.set_page_config(page_title="Workbench Group | Estate OS", layout="wide")
st.title("Management Portal: 3739 Knollwood Dr")

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
    st.header("52-Week Maintenance Calendar")
    st.info("Guideline for standards for 3739 Knollwood.")

    # Hardcoded Guidelines (The "North Star")
    calendar_data = {
        "Frequency": ["Monthly", "Quarterly", "Bi-Annual", "Annual", "Annual"],
        "System": ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"],
        "Task": [
            "HVAC Filter Audit & Condensate Line Flush",
            "Building Envelope Scan (Masonry/Sealants)",
            "Irrigation 'Wet Test' & Zone Calibration",
            "Generator Full-Load Test & Fluid Check",
            "Stone/Marble Sealant Integrity Audit"
        ],
        "Special Instructions": [
            "Check all 5 zones; confirm 48-50% RH.",
            "Inspect North-facing stucco for hairline cracks.",
            "Adjust heads for seasonal wind patterns.",
            "Verify remote monitoring is active.",
            "Focus on high-use kitchen & master bath surfaces."
        ]
    }
    
    df_cal = pd.DataFrame(calendar_data)
    
    # Filter by Frequency for quick viewing
    freq_filter = st.multiselect("Filter by Frequency", options=["Monthly", "Quarterly", "Bi-Annual", "Annual"], default=["Monthly", "Quarterly"])
    filtered_df = df_cal[df_cal["Frequency"].isin(freq_filter)]
    
    st.table(filtered_df)

    st.markdown("---")
    
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
