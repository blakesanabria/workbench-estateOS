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

# --- 2. SECURE DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet):
    # The connection now handles the URL and Credentials automatically from Secrets
    return conn.read(worksheet=worksheet, ttl="1s")

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
        col1, col2, col3 = st.columns(3) # Changed to 3 columns
        with col1:
            cat = st.selectbox("System Category", ["Mechanical", "Envelope", "Aesthetics", "Safety"])
            item = st.text_input("Observation/Task")
        with col2:
            stat = st.selectbox("Current Status", ["Resolved", "Pending", "Needs Attention"])
            impact = st.select_slider("Impact on Asset Health", options=["Low", "Medium", "High"])
        with col3:
            # NEW: Date picker for the due date
            due_date = st.date_input("Target Completion Date", value=datetime.now())
        
        if st.form_submit_button("Log Weekly Finding"):
            df = get_data("punch_list")
            # Added due_date to the new row dictionary
            new_row = pd.DataFrame([{
                "date": datetime.now().strftime("%Y-%m-%d"), 
                "category": cat, 
                "item": item, 
                "status": stat, 
                "impact": impact,
                "due_date": due_date.strftime("%Y-%m-%d")
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_data(updated_df, "punch_list")
            st.success(f"Finding logged! Target: {due_date.strftime('%b %d')}")
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
    cal_df = get_data("master_calendar")
    
    if not cal_df.empty:
        # Sort so users see logical grouping
        st.table(cal_df.sort_values(by="frequency"))
    else:
        st.info("Your calendar is currently empty. Use the form above to add your first task.")
    
with tab3:
    st.header(f"Executive Stewardship Report: {datetime.now().strftime('%B %Y')}")
    
    try:
        all_data = get_data("punch_list")
        
        if not all_data.empty:
            # 1. LOGIC & CALCULATIONS
            total_items = len(all_data)
            urgent_count = len(all_data[all_data['status'] == 'Needs Attention'])
            resolved_count = len(all_data[all_data['status'] == 'Resolved'])
            completion_rate = (resolved_count / total_items) * 100 if total_items > 0 else 0

            # 2. EXECUTIVE SUMMARY BOX
            if urgent_count > 0:
                st.info(f"**Current Status:** Stewardship activities are ongoing. We are currently managing **{urgent_count}** open action items. Systems not listed below are performing within normal parameters.")
            else:
                st.success("**Current Status:** All property systems are currently stable. Maintenance is up to date with 100% completion rate for this period.")

            # 3. TOP LEVEL METRICS
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Observations", total_items)
            m2.metric("Items Resolved", resolved_count)
            m3.metric("Asset Health Score", f"{int(completion_rate)}%")

            st.divider()

            # 4. THE STATUS BOARD
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown("### 🟢 RESOLVED")
                resolved = all_data[all_data['status'] == 'Resolved']
                if not resolved.empty:
                    for _, row in resolved.tail(5).iterrows():
                        st.write(f"✅ **{row['category']}:** {row['item']}")
                        st.caption(f"Completed: {row['date']}")
                else:
                    st.write("No items resolved this period.")
                    
            with col_b:
                st.markdown("### 🟡 MONITORING")
                pending = all_data[all_data['status'] == 'Pending']
                if not pending.empty:
                    for _, row in pending.tail(5).iterrows():
                        st.write(f"⏳ **{row['category']}:** {row['item']}")
                        st.caption(f"Target: {row['due_date']}")
                else:
                    st.write("All systems clear.")
                    
            with col_c:
                st.markdown("### 🔴 ACTION REQUIRED")
                critical = all_data[all_data['status'] == 'Needs Attention']
                if not critical.empty:
                    for _, row in critical.iterrows():
                        # --- OVERDUE CALCULATION ---
                        try:
                            target = pd.to_datetime(row['due_date']).date()
                            today = datetime.now().date()
                            days_diff = (today - target).days
                            
                            if days_diff > 0:
                                # Highlight overdue in Red text for the dashboard
                                overdue_label = f":red[**{days_diff} DAYS OVERDUE**]"
                            else:
                                overdue_label = f"Target: {target.strftime('%b %d')}"
                        except:
                            overdue_label = "Target: TBD"

                        prefix = "🚨" if row['impact'] == "High" else "⚠️"
                        st.write(f"{prefix} **{row['category']}:** {row['item']}")
                        st.caption(overdue_label)
                        st.divider()
                else:
                    st.write("No urgent actions needed.")

            # 5. VISUAL DISTRIBUTION
            st.subheader("System Workload Breakdown")
            category_counts = all_data['category'].value_counts()
            st.bar_chart(category_counts)

        else:
            st.info("Log your first field entry in Tab 1 to generate the scorecard.")
            
    except Exception as e:
        st.error(f"Scorecard Error: {e}")
