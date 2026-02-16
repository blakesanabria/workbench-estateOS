import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- 1. LOGIN SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

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

# --- 2. SECURE DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300) 
def get_data(worksheet):
    # Returns the full dataframe
    return conn.read(worksheet=worksheet)

def save_data(df, worksheet):
    conn.update(worksheet=worksheet, data=df)
    st.cache_data.clear()

# --- 3. GLOBAL PROPERTY SELECTOR ---
with st.sidebar:
    st.image("https://via.placeholder.com/150?text=Workbench+Group", width=150) # Optional Logo
    st.header("Estate Selection")
    # Add new properties to this list as you expand
    property_list = ["3739 Knollwood Dr", "Example Property 2"]
    active_property = st.selectbox("Select Active Estate", property_list)
    st.info(f"Currently managing: **{active_property}**")

# --- 4. APP LAYOUT ---
st.set_page_config(page_title=f"Workbench | {active_property}", layout="wide")
st.title(f"Management Portal: {active_property}")

tab1, tab2, tab3, tab4 = st.tabs(["Weekly Field Entry", "Master Timeline", "Executive Scorecard", "Vendor Directory"])

# --- TAB 1: FIELD AUDIT & SCHEDULING ---
with tab1:
    st.header(f"Field Audit: {active_property}")
    
    try:
        # Pull vendors, but we keep the directory global so you don't have to re-add them
        vendor_df = get_data("vendors").fillna("")
        vendor_options = ["Internal / Workbench"] + sorted(vendor_df["company_name"].unique().tolist())
    except:
        vendor_options = ["Internal / Workbench"]

    with st.form("audit_entry"):
        col1, col2, col3 = st.columns([2, 2, 1]) 
        with col1:
            cat = st.selectbox("System Category", ["Mechanical", "Pool", "Landscaping", "Envelope", "Aesthetics", "Safety", "Site"])
            item = st.text_input("Observation/Task")
            assigned_vendor = st.selectbox("Assign to Vendor", vendor_options)
        with col2:
            stat = st.selectbox("Current Status", ["Needs Attention", "Pending", "Resolved"])
            due_date = st.date_input("Target Completion Date", value=datetime.now())
            impact = st.select_slider("Priority Level", options=["Low", "Medium", "High"])
        with col3:
            task_cost = st.number_input("Cost ($)", min_value=0.0, step=50.0, format="%.2f")
        
        if st.form_submit_button("Log & Schedule Task"):
            # Get ALL data first to append
            full_df = get_data("punch_list").fillna("")
            task_display = f"{item} ({assigned_vendor})" if assigned_vendor != "Internal / Workbench" else item
            
            new_row = pd.DataFrame([{
                "property_name": active_property, # KEY: Tagging the property
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": cat,
                "item": task_display,
                "status": stat,
                "impact": impact,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "cost": task_cost
            }])
            
            updated_df = pd.concat([full_df, new_row], ignore_index=True)
            save_data(updated_df, "punch_list")
            st.success("Task logged!")
            st.rerun()

    # Activity Log filtered for THIS property
    st.markdown(f"### Recent Activity for {active_property}")
    try:
        all_history = get_data("punch_list").fillna("")
        prop_history = all_history[all_history["property_name"] == active_property]
        if not prop_history.empty:
            st.table(prop_history[["date", "item", "status", "due_date", "cost"]].tail(5))
    except:
        st.info("No activity logged for this property.")

# --- TAB 2: MASTER TIMELINE ---
with tab2:
    st.header(f"Maintenance Timeline: {active_property}")
    try:
        # Filter data for active property
        all_p = get_data("punch_list").fillna("")
        all_r = get_data("master_calendar").fillna("")
        
        prop_punch = all_p[all_p["property_name"] == active_property]
        prop_rec = all_r[all_r["property_name"] == active_property]
        
        calendar_events = []
        if not prop_punch.empty:
            for _, row in prop_punch.iterrows():
                status_color = "#ff4b4b" if row['status'] == "Needs Attention" else "#ffa500" if row['status'] == "Pending" else "#28a745"
                calendar_events.append({
                    "title": f"🛠️ {row['item']}", "start": str(row['due_date']), "color": status_color, "allDay": True
                })

        if not prop_rec.empty:
            for _, row in prop_rec.iterrows():
                calendar_events.append({
                    "title": f"📅 {row['frequency']}: {row['task']}", "start": datetime.now().strftime("%Y-%m-%d"), "color": "#3b82f6", "allDay": True
                })

        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"},
            "initialView": "dayGridMonth", "height": 750,
        }
        calendar(events=calendar_events, options=calendar_options)
    except:
        st.error("Error loading Timeline.")

    st.divider()
    st.subheader(f"Manage Guidelines for {active_property}")
    with st.expander("➕ Add New Property Standard"):
        with st.form("new_calendar_task"):
            f_freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Bi-Annual", "Annual"])
            f_sys = st.selectbox("System", ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"])
            f_task = st.text_input("Task Name")
            f_inst = st.text_area("Special Instructions")
            if st.form_submit_button("Save Standard"):
                all_cal = get_data("master_calendar").fillna("")
                new_task = pd.DataFrame([{"property_name": active_property, "frequency": f_freq, "system": f_sys, "task": f_task, "instructions": f_inst}])
                save_data(pd.concat([all_cal, new_task], ignore_index=True), "master_calendar")
                st.rerun()

# --- TAB 3: EXECUTIVE SCORECARD ---
with tab3:
    st.header(f"Stewardship Report: {active_property}")
    try:
        all_d = get_data("punch_list").fillna("")
        prop_data = all_d[all_d["property_name"] == active_property]
        
        if not prop_data.empty:
            prop_data['cost'] = pd.to_numeric(prop_data['cost'], errors='coerce').fillna(0)
            total_spend = prop_data['cost'].sum()
            health = (len(prop_data[prop_data['status'] == 'Resolved']) / len(prop_data)) * 100

            m1, m2, m3 = st.columns(3)
            m1.metric("Tasks Managed", len(prop_data))
            m2.metric("Property Investment", f"${total_spend:,.2f}")
            m3.metric("Health Score", f"{int(health)}%")

            st.divider()
            # Simplified Status View
            c1, c2, c3 = st.columns(3)
            with c1:
                st.success("Resolved")
                st.write(prop_data[prop_data['status'] == 'Resolved'][['item', 'cost']].tail(3))
            with c2:
                st.warning("Pending")
                st.write(prop_data[prop_data['status'] == 'Pending'][['item', 'due_date']].tail(3))
            with c3:
                st.error("Needs Attention")
                st.write(prop_data[prop_data['status'] == 'Needs Attention'][['item', 'impact']])
        else:
            st.info("No data for this property.")
    except:
        st.error("Error loading scorecard.")

# --- TAB 4: VENDOR DIRECTORY ---
with tab4:
    st.header("Global Vendor Directory")
    # Vendors stay global so you can use the same plumber for multiple properties
    try:
        vendors = get_data("vendors").fillna("")
        # (Include your Add Vendor Form and Table logic here as before)
        st.table(vendors[["company_name", "service", "name", "phone", "email"]])
    except:
        st.info("Add vendors to get started.")
