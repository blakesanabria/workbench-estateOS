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

# Caching avoids the 'Quota Exceeded' error by only hitting Google once every 5 mins
@st.cache_data(ttl=300) 
def get_data(worksheet):
    return conn.read(worksheet=worksheet)

def save_data(df, worksheet):
    conn.update(worksheet=worksheet, data=df)
    # This forces a refresh so new entries show up immediately
    st.cache_data.clear()

# --- 3. APP LAYOUT ---
st.set_page_config(page_title="Workbench Group | Estate OS", layout="wide")
st.title("Maintenance Portal: 3739 Knollwood Dr")

tab1, tab2, tab3, tab4 = st.tabs(["Weekly Field Entry", "Calendar", "Monthly Scorecard", "Vendor Directory"])

# --- TAB 1: FIELD AUDIT & SCHEDULING ---
with tab1:
    st.header("Field Audit & Scheduling")
    
    try:
        vendor_df = get_data("vendors").fillna("")
        vendor_options = ["Internal / Workbench"] + sorted(vendor_df["company_name"].unique().tolist())
    except:
        vendor_options = ["Internal / Workbench"]

    with st.form("audit_entry"):
        col1, col2, col3 = st.columns([2, 2, 1]) 
        
        with col1:
            cat = st.selectbox("System Category", ["Mechanical", "Pool", "Landscaping", "Envelope", "Aesthetics", "Safety", "Site"])
            item = st.text_input("Observation/Task", placeholder="e.g., HVAC Annual Service")
            assigned_vendor = st.selectbox("Assign to Vendor", vendor_options)
            
        with col2:
            stat = st.selectbox("Current Status", ["Needs Attention", "Pending", "Resolved"])
            due_date = st.date_input("Target Completion Date", value=datetime.now())
            impact = st.select_slider("Priority Level", options=["Low", "Medium", "High"])

        with col3:
            task_cost = st.number_input("Cost ($)", min_value=0.0, step=50.0, format="%.2f")
            st.caption("Budgeted Amount")
        
        if st.form_submit_button("Log & Schedule Task"):
            df = get_data("punch_list").fillna("")
            task_display = f"{item} ({assigned_vendor})" if assigned_vendor != "Internal / Workbench" else item
            
            new_row = pd.DataFrame([{
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": cat,
                "item": task_display,
                "status": stat,
                "impact": impact,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "cost": task_cost
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_data(updated_df, "punch_list")
            st.success(f"Task logged for {assigned_vendor}!")
            st.rerun()

    st.markdown("### Recent Activity")
    try:
        history = get_data("punch_list").fillna("")
        if not history.empty:
            st.table(history[["date", "item", "status", "due_date", "cost"]].tail(5))
        else:
            st.info("No activity logged yet.")
    except:
        st.error("Error loading activity log.")

# --- TAB 2: MASTER TIMELINE ---
with tab2:
    st.header("Estate Maintenance Timeline")
    
    try:
        # 1. Pull data and handle NaNs
        punch_data = get_data("punch_list").fillna("")
        recurring_data = get_data("master_calendar").fillna("")
        calendar_events = []

        # 2. Add Punch List Items (Repairs/Tasks)
        if not punch_data.empty:
            for _, row in punch_data.iterrows():
                status_color = "#ff4b4b" if row['status'] == "Needs Attention" else "#ffa500" if row['status'] == "Pending" else "#28a745"
                calendar_events.append({
                    "title": f"🛠️ {row['item']}",
                    "start": str(row['due_date']),
                    "end": str(row['due_date']),
                    "color": status_color,
                    "allDay": True
                })

        # 3. Add Recurring Guidelines (Blue banners)
        if not recurring_data.empty:
            for _, row in recurring_data.iterrows():
                calendar_events.append({
                    "title": f"📅 {row['frequency']}: {row['task']}",
                    "start": datetime.now().strftime("%Y-%m-%d"),
                    "color": "#3b82f6",
                    "allDay": True
                })

        # 4. Calendar Configuration
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today", 
                "center": "title", 
                "right": "dayGridMonth,dayGridWeek"
            },
            "initialView": "dayGridMonth",
            "navLinks": True,
            "height": 750, 
        }

        # 5. Display the Calendar
        calendar(events=calendar_events, options=calendar_options)
        
    except Exception as e:
        st.error(f"Timeline display error: {e}")

    st.divider()
    
    # --- MISSING SECTION: MANAGE MAINTENANCE GUIDELINES ---
    st.subheader("Manage Maintenance Guidelines")
    
    # Form to add new standards
    with st.expander("➕ Add New Recurring Task"):
        with st.form("new_calendar_task"):
            f_freq = st.selectbox("Frequency", ["Monthly", "Quarterly", "Bi-Annual", "Annual"])
            f_sys = st.selectbox("System", ["Mechanical", "Envelope", "Site", "Life Safety", "Aesthetics"])
            f_task = st.text_input("Task Name", placeholder="e.g., Clean Gutters")
            f_inst = st.text_area("Special Instructions", placeholder="Tools needed, specific vendors, etc.")
            
            if st.form_submit_button("Save to Master Guidelines"):
                existing_cal = get_data("master_calendar").fillna("")
                new_task = pd.DataFrame([{
                    "frequency": f_freq, 
                    "system": f_sys, 
                    "task": f_task, 
                    "instructions": f_inst
                }])
                updated_cal = pd.concat([existing_cal, new_task], ignore_index=True)
                save_data(updated_cal, "master_calendar")
                st.success(f"Standard added: {f_task}")
                st.rerun()

    # Table view of all existing guidelines
    st.markdown("### Existing Guidelines")
    try:
        cal_df = get_data("master_calendar").fillna("")
        if not cal_df.empty:
            # Sorting by frequency makes it easier for the Monrads to read
            st.table(cal_df.sort_values(by="frequency"))
        else:
            st.info("No recurring guidelines established yet.")
    except Exception as e:
        st.warning("Could not load guidelines table. Check 'master_calendar' worksheet.")

# --- TAB 3: EXECUTIVE SCORECARD ---
with tab3:
    st.header(f"Executive Stewardship Report: {datetime.now().strftime('%B %Y')}")
    
    try:
        all_data = get_data("punch_list").fillna("")
        if not all_data.empty:
            all_data['cost'] = pd.to_numeric(all_data['cost'], errors='coerce').fillna(0)
            total_items = len(all_data)
            urgent_count = len(all_data[all_data['status'] == 'Needs Attention'])
            resolved_count = len(all_data[all_data['status'] == 'Resolved'])
            total_spend = all_data['cost'].sum()
            health_score = (resolved_count / total_items) * 100 if total_items > 0 else 0

            if urgent_count > 0:
                st.info(f"**Status Update:** Managing **{urgent_count}** urgent items. Total investment: **${total_spend:,.2f}**.")
            else:
                st.success(f"**Status Update:** Systems stable. Total investment: **${total_spend:,.2f}**.")

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Observations", total_items)
            m2.metric("Total Investment", f"${total_spend:,.2f}")
            m3.metric("Asset Health Score", f"{int(health_score)}%")

            st.divider()
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown("### 🟢 RESOLVED")
                resolved_df = all_data[all_data['status'] == 'Resolved']
                for _, row in resolved_df.tail(5).iterrows():
                    st.write(f"✅ **{row['category']}:** {row['item']}")
                    st.caption(f"Cost: ${row['cost']:,.2f}")
                    
            with col_b:
                st.markdown("### 🟡 MONITORING")
                pending_df = all_data[all_data['status'] == 'Pending']
                for _, row in pending_df.tail(5).iterrows():
                    st.write(f"⏳ **{row['category']}:** {row['item']}")
                    st.caption(f"Target: {row['due_date']} | Est: ${row['cost']:,.2f}")
                    
            with col_c:
                st.markdown("### 🔴 ACTION REQUIRED")
                critical_df = all_data[all_data['status'] == 'Needs Attention']
                for _, row in critical_df.iterrows():
                    try:
                        target = pd.to_datetime(row['due_date']).date()
                        days_diff = (datetime.now().date() - target).days
                        overdue_msg = f":red[**{days_diff} DAYS OVERDUE**]" if days_diff > 0 else f"Target: {target.strftime('%b %d')}"
                    except:
                        overdue_msg = "Target: TBD"
                    prefix = "🚨" if row['impact'] == "High" else "⚠️"
                    st.write(f"{prefix} **{row['category']}:** {row['item']}")
                    st.caption(f"{overdue_msg} | Est: ${row['cost']:,.2f}")
                    st.divider()

            st.divider()
            st.subheader("Investment by Property System")
            cost_chart_data = all_data.groupby('category')['cost'].sum()
            st.bar_chart(cost_chart_data)
        else:
            st.info("No data available for report.")
    except Exception as e:
        st.error(f"Scorecard Error: {e}")

# --- TAB 4: VENDOR DIRECTORY ---
with tab4:
    st.header("Service Provider Directory")
    with st.expander("➕ Add New Service Provider"):
        with st.form("new_vendor"):
            v_company = st.text_input("Company Name")
            v_contact = st.text_input("Contact Person")
            v_serv = st.selectbox("Service Category", ["Pool", "HVAC", "Landscaping", "Plumbing", "Electrical", "Roofing", "Aesthetics", "General"])
            v_phone = st.text_input("Phone Number")
            v_email = st.text_input("Email Address")
            if st.form_submit_button("Add to Directory"):
                v_df = get_data("vendors").fillna("")
                new_v = pd.DataFrame([{"company_name": v_company, "name": v_contact, "service": v_serv, "phone": v_phone, "email": v_email}])
                updated_v = pd.concat([v_df, new_v], ignore_index=True)
                save_data(updated_v, "vendors")
                st.success(f"Vendor '{v_company}' saved!")
                st.rerun()

    st.divider()
    try:
        vendors = get_data("vendors").fillna("")
        if not vendors.empty:
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search_query = st.text_input("🔍 Search Directory")
            with col_filter:
                category_filter = st.selectbox("Filter", ["All"] + sorted(vendors["service"].unique().tolist()))
            
            filtered_df = vendors.copy()
            if search_query:
                filtered_df = filtered_df[filtered_df['company_name'].str.contains(search_query, case=False) | filtered_df['name'].str.contains(search_query, case=False)]
            if category_filter != "All":
                filtered_df = filtered_df[filtered_df['service'] == category_filter]
            
            st.table(filtered_df[["company_name", "service", "name", "phone", "email"]])
        else:
            st.info("Directory is empty.")
    except:
        st.error("Could not load vendors.")
