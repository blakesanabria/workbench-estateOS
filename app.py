import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- 1. SETUP & BRIGHT THEME ---
st.set_page_config(page_title="Workbench Estate OS", layout="wide", initial_sidebar_state="expanded")

# High-Contrast Light Mode Styling
st.markdown("""
    <style>
    /* Main Background and Clean Font */
    .stApp { 
        background-color: #FFFFFF; 
        color: #1F2937;
        font-family: 'Inter', sans-serif; 
    }
    
    /* Modern Metric Cards - High Contrast */
    [data-testid="stMetricValue"] { 
        font-size: 32px !important; 
        font-weight: 800 !important; 
        color: #1D4ED8 !important; /* Professional Blue */
    }
    [data-testid="stMetricLabel"] { 
        font-size: 16px !important; 
        color: #4B5563 !important; 
        font-weight: 600 !important;
    }
    
    /* Styled Containers (Cards) with subtle shadow */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Clean Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F3F4F6 !important;
        border-right: 1px solid #E5E7EB;
    }

    /* Tab Styling - Easy to Read */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        color: #6B7280;
    }
    .stTabs [aria-selected="true"] {
        color: #1D4ED8 !important;
        border-bottom: 2px solid #1D4ED8 !important;
    }
    
    /* Headings */
    h1, h2, h3 { color: #111827 !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("Estate OS | Secure Access")
    password = st.text_input("Access Key", type="password")
    if st.button("Unlock Dashboard", use_container_width=True):
        if password == st.secrets["access_password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Invalid Key")
    return False

if not check_password():
    st.stop()

# --- 3. DATA ENGINE (Date-Fixed) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300) 
def get_data(worksheet):
    df = conn.read(worksheet=worksheet)
    # Fix dates immediately upon loading
    for col in ['date', 'due_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df

def save_data(df, worksheet):
    df_save = df.copy()
    for col in ['date', 'due_date']:
        if col in df_save.columns:
            df_save[col] = df_save[col].astype(str)
    conn.update(worksheet=worksheet, data=df_save)
    st.cache_data.clear()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Workbench Group")
    st.markdown("---")
    try:
        all_p_data = get_data("punch_list").fillna("")
        existing_props = sorted([p for p in all_p_data["property_name"].unique() if p]) if not all_p_data.empty else ["3739 Knollwood Dr"]
    except:
        existing_props = ["3739 Knollwood Dr"]

    active_property = st.selectbox("Active Estate", existing_props, index=0)
    st.markdown("---")
    with st.expander("Add New Property"):
        new_prop_name = st.text_input("Address")
        if st.button("Initialize", use_container_width=True):
            if new_prop_name and new_prop_name not in existing_props:
                seed = pd.DataFrame([{"property_name": new_prop_name, "date": datetime.now().strftime("%Y-%m-%d"), "category": "Site", "item": "Initial Setup", "status": "Resolved", "impact": "Low", "due_date": datetime.now().strftime("%Y-%m-%d"), "cost": 0.0}])
                save_data(pd.concat([get_data("punch_list").fillna(""), seed], ignore_index=True), "punch_list")
                st.rerun()

# --- 5. MAIN DASHBOARD ---
st.title(f"Property Intelligence: {active_property}")
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Field Entry", "📅 Timeline", "📊 Scorecard", "👥 Vendors"])

# --- TAB 1: ENTRY & CHECKLIST ---
with tab1:
    col_form, col_recent = st.columns([1, 1])
    with col_form:
        with st.container(border=True):
            st.subheader("New Observation")
            try:
                v_df = get_data("vendors").fillna("")
                v_options = ["Internal / Workbench"] + sorted(v_df["company_name"].unique().tolist())
            except:
                v_options = ["Internal / Workbench"]

            with st.form("entry_form", clear_on_submit=True):
                cat = st.selectbox("Category", ["Mechanical", "Pool", "Landscaping", "Envelope", "Aesthetics", "Safety", "Site"])
                item = st.text_input("Task Description")
                vendor = st.selectbox("Assign Vendor", v_options)
                c1, c2, c3 = st.columns(3)
                stat = c1.selectbox("Status", ["Needs Attention", "Pending", "Resolved"])
                due = c2.date_input("Due Date")
                cost = c3.number_input("Est. Cost ($)", min_value=0.0)
                impact = st.select_slider("Priority", options=["Low", "Medium", "High"])
                if st.form_submit_button("Log Entry", use_container_width=True):
                    full_df = get_data("punch_list").fillna("")
                    new_row = pd.DataFrame([{"property_name": active_property, "date": datetime.now().strftime("%Y-%m-%d"), "category": cat, "item": f"{item} ({vendor})", "status": stat, "impact": impact, "due_date": due.strftime("%Y-%m-%d"), "cost": cost}])
                    save_data(pd.concat([full_df, new_row], ignore_index=True), "punch_list")
                    st.rerun()

    with col_recent:
        st.subheader("Recent Activity")
        raw_hist = get_data("punch_list").fillna("")
        prop_hist = raw_hist[raw_hist["property_name"] == active_property].tail(10)
        st.dataframe(prop_hist[["date", "item", "status", "cost"]], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader(f"✅ Active Checklist")
    full_punch = get_data("punch_list").fillna("")
    if not full_punch.empty:
        checklist_df = full_punch[(full_punch["property_name"] == active_property) & (full_punch["status"] != "Resolved")].copy()
        if not checklist_df.empty:
            checklist_df.insert(0, "Done", False)
            edited_df = st.data_editor(
                checklist_df[["Done", "date", "item", "impact", "due_date"]],
                column_config={"Done": st.column_config.CheckboxColumn("Complete", default=False)},
                disabled=["date", "item", "impact", "due_date"],
                hide_index=True, use_container_width=True, key="task_checklist"
            )
            if edited_df["Done"].any():
                completed_items = edited_df[edited_df["Done"] == True]["item"].tolist()
                for item_name in completed_items:
                    full_punch.loc[(full_punch["property_name"] == active_property) & (full_punch["item"] == item_name), "status"] = "Resolved"
                save_data(full_punch, "punch_list")
                st.rerun()
        else:
            st.success("All caught up! No pending tasks.")

# --- TAB 2: TIMELINE & GUIDELINES ---
with tab2:
    try:
        all_p = get_data("punch_list").fillna("")
        all_r = get_data("master_calendar").fillna("")
        prop_p = all_p[all_p["property_name"] == active_property]
        prop_r = all_r[all_r["property_name"] == active_property]
        
        events = []
        for _, row in prop_p.iterrows():
            if row['due_date']:
                color = "#DC2626" if row['status'] == "Needs Attention" else "#D97706" if row['status'] == "Pending" else "#059669"
                events.append({"title": f"🛠️ {row['item']}", "start": str(row['due_date']), "color": color, "allDay": True})
        for _, row in prop_r.iterrows():
            events.append({"title": f"📅 {row['frequency']}: {row['task']}", "start": datetime.now().strftime("%Y-%m-%d"), "color": "#2563EB", "allDay": True})

        calendar(events=events, options={"initialView": "dayGridMonth", "height": 650})
        
        st.divider()
        st.subheader("Maintenance Standards")
        c_new, c_list = st.columns([1, 2])
        with c_new:
            with st.container(border=True):
                with st.form("guideline_form", clear_on_submit=True):
                    f_freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Bi-Annual", "Annual"])
                    f_sys = st.selectbox("System", ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"])
                    f_task = st.text_input("Task Name")
                    f_inst = st.text_area("Instructions")
                    if st.form_submit_button("Save Standard", use_container_width=True):
                        all_cal = get_data("master_calendar").fillna("")
                        new_g = pd.DataFrame([{"property_name": active_property, "frequency": f_freq, "system": f_sys, "task": f_task, "instructions": f_inst}])
                        save_data(pd.concat([all_cal, new_g], ignore_index=True), "master_calendar")
                        st.rerun()
        with c_list:
            st.dataframe(prop_r[["frequency", "system", "task", "instructions"]].sort_values(by="frequency"), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Timeline/Guideline error: {e}")

# --- TAB 3: SCORECARD ---
with tab3:
    try:
        all_d = get_data("punch_list").fillna("")
        p_data = all_d[all_d["property_name"] == active_property].copy()
        if not p_data.empty:
            p_data['cost'] = pd.to_numeric(p_data['cost'], errors='coerce').fillna(0)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Asset Health", f"{int((len(p_data[p_data['status'] == 'Resolved'])/len(p_data))*100)}%")
            m2.metric("Total Invested", f"${p_data[p_data['status'] == 'Resolved']['cost'].sum():,.0f}")
            m3.metric("Liability", f"${p_data[p_data['status'] != 'Resolved']['cost'].sum():,.0f}")
            m4.metric("Active Items", len(p_data[p_data['status'] != 'Resolved']))
            st.divider()
            st.subheader("Investment by Category")
            st.bar_chart(p_data.groupby('category')['cost'].sum(), color="#2563EB")
        else:
            st.info("No data recorded.")
    except:
        st.error("Scorecard error.")

# --- TAB 4: VENDORS ---
with tab4:
    st.subheader("Vendor Directory")
    try:
        v_data = get_data("vendors").fillna("")
        with st.expander("Register New Vendor"):
            with st.form("new_v_form", clear_on_submit=True):
                v_comp = st.text_input("Company")
                v_serv = st.selectbox("Service", ["Plumbing", "Electrical", "HVAC", "Pool", "Landscaping", "General"])
                v_name = st.text_input("Contact")
                v_ph = st.text_input("Phone")
                v_em = st.text_input("Email")
                if st.form_submit_button("Save Vendor", use_container_width=True):
                    save_data(pd.concat([v_data, pd.DataFrame([{"company_name": v_comp, "service": v_serv, "name": v_name, "phone": v_ph, "email": v_em}])], ignore_index=True), "vendors")
                    st.rerun()
        if not v_data.empty:
            st.dataframe(v_data[["company_name", "service", "name", "phone", "email"]], use_container_width=True, hide_index=True)
    except:
        st.info("No vendors yet.")
