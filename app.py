import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="Workbench Estate OS", layout="wide", initial_sidebar_state="expanded")

# Professional Modern Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Inter', sans-serif; }
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #00d4ff !important; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #1a1c24;
        border: 1px solid #2d2f39 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff !important;
    }
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

# --- 3. DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300) 
def get_data(worksheet):
    return conn.read(worksheet=worksheet)

def save_data(df, worksheet):
    conn.update(worksheet=worksheet, data=df)
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

# --- 5. DASHBOARD ---
st.title(f"Property Overview: {active_property}")
tab1, tab2, tab3, tab4 = st.tabs(["Field Entry", "Calendar", "Scorecard", "Vendors"])

# --- TAB 1: FIELD ENTRY & CHECKLIST ---
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
                cost = c3.number_input("Est. Cost", min_value=0.0)
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
                color = "#ff4b4b" if row['status'] == "Needs Attention" else "#ffa500" if row['status'] == "Pending" else "#28a745"
                events.append({"title": f"🛠️ {row['item']}", "start": str(row['due_date']), "color": color, "allDay": True})
        for _, row in prop_r.iterrows():
            events.append({"title": f"📅 {row['frequency']}: {row['task']}", "start": datetime.now().strftime("%Y-%m-%d"), "color": "#3b82f6", "allDay": True})

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
        
# --- TAB 3: EXECUTIVE SCORECARD ---
with tab3:
    st.header(f"Monthly Report: {active_property}")
    try:
        all_d = get_data("punch_list").fillna("")
        p_data = all_d[all_d["property_name"] == active_property].copy()
        
        if not p_data.empty:
            # 1. Data Cleaning & Calculations
            p_data['cost'] = pd.to_numeric(p_data['cost'], errors='coerce').fillna(0)
            
            total_invested = p_data[p_data['status'] == 'Resolved']['cost'].sum()
            upcoming_liability = p_data[p_data['status'] != 'Resolved']['cost'].sum()
            resolved_count = len(p_data[p_data['status'] == 'Resolved'])
            total_tasks = len(p_data)
            health_score = int((resolved_count / total_tasks) * 100) if total_tasks > 0 else 0
            
            # 2. Key Performance Indicators (KPIs)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Asset Health", f"{health_score}%")
            k2.metric("Total Spent", f"${total_invested:,.0f}")
            k3.metric("Upcoming Liability", f"${upcoming_liability:,.0f}")
            k4.metric("Active Items", total_tasks - resolved_count)

            st.markdown("---")
            
            # 3. Financial & Operational Analysis
            col_chart, col_stat = st.columns([2, 1])
            
            with col_chart:
                st.subheader("Cost by System")
                # Horizontal bars are easier to read for category names
                cat_spend = p_data.groupby('category')['cost'].sum().sort_values(ascending=True)
                st.bar_chart(cat_spend, horizontal=True, color="#00d4ff")
                
                with st.expander("🔍 View Detailed Cost Audit"):
                    st.dataframe(
                        p_data[p_data['cost'] > 0][['item', 'category', 'cost']].sort_values(by='cost', ascending=False),
                        use_container_width=True, hide_index=True
                    )

            with col_stat:
                st.subheader("System Health Grid")
                # This shows a count of tasks by status for each category
                if not p_data.empty:
                    grid = pd.crosstab(p_data['category'], p_data['status'])
                    st.dataframe(grid, use_container_width=True)

            st.markdown("---")

            # 4. Critical Attention Burn-Down List
            st.subheader("⚠️ Priority Focus Items")
            critical_items = p_data[(p_data['impact'] == 'High') & (p_data['status'] != 'Resolved')]
            
            if not critical_items.empty:
                st.dataframe(
                    critical_items[['item', 'category', 'due_date', 'cost']],
                    column_config={
                        "item": "Task Name",
                        "due_date": st.column_config.DateColumn("Target Date"),
                        "cost": st.column_config.NumberColumn("Est. Cost", format="$%d")
                    },
                    hide_index=True, use_container_width=True
                )
            else:
                st.success("All high-impact systems are currently stable.")

        else:
            st.info(f"No management data found for {active_property}. Log your first audit in Tab 1.")
            
    except Exception as e:
        st.error(f"Scorecard Display Error: {e}")

# --- TAB 4: VENDOR DIRECTORY ---
with tab4:
    st.subheader("Vendor Directory")
    v_data = get_data("vendors").fillna("")
    if not v_data.empty:
        st.dataframe(v_data[["company_name", "service", "name", "phone", "email"]], use_container_width=True, hide_index=True)
