import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar

# --- 1. SETUP & THEMING ---
st.set_page_config(page_title="Workbench Estate OS", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Modern UI
st.markdown("""
    <style>
    /* Main Background and Font */
    .stApp { background-color: #0e1117; font-family: 'Inter', sans-serif; }
    
    /* Modern Metric Cards */
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #00d4ff !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #9ca3af !important; }
    
    /* Styled Containers/Cards */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #1a1c24;
        border: 1px solid #2d2f39 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    
    /* Modern Tabs */
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

# --- 2. LOGIN SECURITY ---
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

# --- 4. SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("Workbench Group")
    st.markdown("---")
    
    # Dynamic Property Pull
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

# --- 5. DASHBOARD LAYOUT ---
st.title(f"Property Intelligence: {active_property}")

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Field Entry", "📅 Timeline", "📊 Scorecard", "👥 Vendors"])

# --- TAB 1: FIELD ENTRY ---
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

# --- TAB 2: TIMELINE ---
with tab2:
    try:
        all_p = get_data("punch_list").fillna("")
        prop_p = all_p[all_p["property_name"] == active_property]
        
        events = []
        for _, row in prop_p.iterrows():
            if row['due_date']:
                color = "#ff4b4b" if row['status'] == "Needs Attention" else "#ffa500" if row['status'] == "Pending" else "#28a745"
                events.append({"title": f"🛠️ {row['item']}", "start": str(row['due_date']), "color": color})

        calendar(events=events, options={"initialView": "dayGridMonth", "height": 650})
    except Exception as e:
        st.error(f"Timeline error: {e}")

# --- TAB 3: SCORECARD ---
with tab3:
    try:
        all_d = get_data("punch_list").fillna("")
        p_data = all_d[all_d["property_name"] == active_property].copy()
        
        if not p_data.empty:
            p_data['cost'] = pd.to_numeric(p_data['cost'], errors='coerce').fillna(0)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Active Tasks", len(p_data[p_data['status'] != 'Resolved']))
            m2.metric("Total Investment", f"${p_data['cost'].sum():,.2f}")
            m3.metric("Asset Health", f"{int((len(p_data[p_data['status'] == 'Resolved'])/len(p_data))*100)}%")
            
            st.divider()
            st.subheader("Investment by System")
            st.bar_chart(p_data.groupby('category')['cost'].sum())
        else:
            st.info("No data recorded.")
    except:
        st.error("Scorecard error.")

# --- TAB 4: VENDOR DIRECTORY ---
with tab4:
    st.subheader("Global Vendor Access")
    v_data = get_data("vendors").fillna("")
    if not v_data.empty:
        st.dataframe(v_data[["company_name", "service", "name", "phone", "email"]], use_container_width=True, hide_index=True)
