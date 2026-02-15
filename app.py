import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. LOGIN SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Password input UI
    st.title("Workbench Group | Estate OS")
    password = st.text_input("Enter Workbench Access Key", type="password")
    if st.button("Unlock Dashboard"):
        if password == st.secrets["access_password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Access Denied")
    return False

if not check_password():
    st.stop()

# --- 2. GOOGLE SHEETS CONNECTION (BYPASS METHOD) ---
SHEET_ID = "1wOU3UAX89VOshu42bnB4A9AqoUe6dNp-TjsZGDhtozQ" 

def get_data(worksheet):
    if worksheet == "punch_list":
        # Usually gid=0 for the first tab
        url = f"https://docs.google.com/spreadsheets/d/1wOU3UAX89VOshu42bnB4A9AqoUe6dNp-TjsZGDhtozQ/export?format=csv&gid=0"
    else:
        # REPLACE '123456' with the gid from your Master Calendar tab URL
        url = f"https://docs.google.com/spreadsheets/d/1wOU3UAX89VOshu42bnB4A9AqoUe6dNp-TjsZGDhtozQ/export?format=csv&gid=63964639"
    return pd.read_csv(url)

# Note: We will keep using the 'conn' logic ONLY for saving 
# because it handles the "Write" permission better.
conn = st.connection("gsheets", type=GSheetsConnection)

def save_data(df, worksheet):
    conn.update(worksheet=worksheet, data=df)
    st.cache_data.clear()
    
# --- 3. APP LAYOUT ---
st.set_page_config(page_title="Workbench Group | Estate OS", layout="wide")
st.title("Maintenance Portal: 3739 Knollwood Dr")

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
        
        # This button MUST be indented to stay inside the form
        if st.form_submit_button("Log Weekly Finding"):
            # 1. Pull current data from Sheets
            df = get_data("punch_list")
            # 2. Create new row
            new_row = pd.DataFrame([{"date": datetime.now().strftime("%Y-%m-%d"), "category": cat, "item": item, "status": stat, "impact": impact}])
            # 3. Combine and save
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_data(updated_df, "punch_list")
            st.success("Finding logged to Google Sheets!")
            st.rerun()

    st.markdown("### Recent Activity")
    try:
        # Using our new direct function
        history = get_data("punch_list")
        if not history.empty:
            # Show the last 5 entries
            st.table(history.tail(5))
        else:
            st.info("No activity logged yet.")
    except Exception as e:
        st.error(f"Waiting for Google Sheets connection... {e}")
    
with tab2:
    st.header("52-Week Maintenance Calendar")
    
    # --- FORM TO ADD NEW TASKS ---
    with st.expander("➕ Add New Maintenance Task"):
        with st.form("new_calendar_task"):
            f_freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Bi-Annual", "Annual"])
            f_sys = st.selectbox("System", ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"])
            f_task = st.text_input("Task Name")
            f_inst = st.text_area("Special Instructions")
            
            if st.form_submit_button("Save to Master Calendar"):
                # 1. Fetch current guidelines
                existing_cal = get_data("master_calendar")
                
                # 2. Create new row with Calendar headers
                new_task = pd.DataFrame([{
                    "frequency": f_freq, 
                    "system": f_sys, 
                    "task": f_task, 
                    "instructions": f_inst
                }])
                
                # 3. Merge and Save to the 'master_calendar' worksheet
                updated_cal = pd.concat([existing_cal, new_task], ignore_index=True)
                save_data(updated_cal, "master_calendar")
                
                st.success("Guideline Added to Google Sheets!")
                st.rerun()

    # --- DISPLAY THE CALENDAR FROM DATABASE ---
    st.markdown("---")
    cal_df = pd.read_sql("SELECT frequency, system, task, instructions FROM master_calendar", conn)
    
    if not cal_df.empty:
        # Sort so users see logical grouping
        st.table(cal_df.sort_values(by="frequency"))
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
