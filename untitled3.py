import streamlit as st
import datetime
import json
import os

# --- Page Configuration ---
st.set_page_config(page_title="Multi-Tenant CPMS", layout="wide")

# --- Constant File Path for Persistent Storage ---
DB_FILE = "construction_db.json"

# --- JSON Database Helper Functions ---
def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_database(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Database Write Error: {e}")

# --- Initialize Session State Memory ---
if 'global_db' not in st.session_state:
    st.session_state.global_db = load_database()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- Authentication System ---
def verify_login():
    username = st.session_state.user.strip()
    password = st.session_state.pwd.strip()
    
    if "users" in st.secrets:
        if username in st.secrets["users"] and st.secrets["users"][username] == password:
            st.session_state.logged_in = True
            st.session_state.current_user = username
            st.session_state.global_db = load_database()
        else:
            st.error("Access Denied: Incorrect Username or Password.")
    else:
        st.error("System Error: User credentials not configured in cloud secrets.")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.rerun()

# --- Login Screen ---
if not st.session_state.logged_in:
    st.title("🔐 Multi-Tenant CPMS - Secure Login")
    st.markdown("Please authenticate with your company credentials.")
    
    with st.container():
        st.text_input("Company Username", key="user")
        st.text_input("Password", type="password", key="pwd")
        st.button("Login", on_click=verify_login)
    
    st.stop()

# =========================================================================
# MAIN APP BEGINS HERE
# =========================================================================

tenant = st.session_state.current_user

if tenant not in st.session_state.global_db:
    st.session_state.global_db[tenant] = {}
    save_database(st.session_state.global_db)

my_projects = st.session_state.global_db[tenant]

# --- UI Header Framework ---
col_head, col_log = st.columns([9, 1])
with col_head:
    st.title("🏗️ Construction Progress Monitoring System")
    st.markdown(f"Active Company Workspace: `{tenant.upper()}`")
with col_log:
    st.button("Log Out", on_click=logout, use_container_width=True)

st.divider()

# --- Sidebar Navigation Control ---
st.sidebar.header("System Menu")
menu_choice = st.sidebar.radio(
    "Select Action:",
    ["1. Setup New Project", "2. Update Daily Progress", "3. Generate Progress Report"]
)

# --- Logic: Setup New Project ---
if menu_choice == "1. Setup New Project":
    st.header("Setup New Project & Activities")
    
    col1, col2 = st.columns(2)
    with col1:
        project_id = st.text_input("Project ID (e.g., P-01)").upper()
        project_name = st.text_input("Project Name")
    
    st.subheader("Add Activity")
    with st.form("activity_form"):
        act_id = st.text_input("Activity ID (e.g., ACT-01)").upper()
        act_name = st.text_input("Activity Name")
        
        # Expanded to 4 columns to accommodate the calendar widgets
        col3, col4, col5, col6 = st.columns(4)
        with col3:
            planned_qty = st.number_input("Planned Quantity", min_value=0.0, step=1.0)
        with col4:
            budget = st.number_input("Allocated Budget (Rs.)", min_value=0.0, step=100.0)
        with col5:
            # NEW: Interactive calendar picker for Start Date
            planned_start = st.date_input("Planned Start Date")
        with col6:
            # NEW: Interactive calendar picker for End Date (forces it to be after start date)
            planned_end = st.date_input("Planned End Date", min_value=planned_start)
            
        submit_btn = st.form_submit_button("Save Activity to System")
        
        if submit_btn:
            if project_id and project_name and act_id and act_name:
                
                # Calculate the duration dynamically (+1 ensures same-day tasks equal 1 day of work)
                calculated_duration = (planned_end - planned_start).days + 1
                
                if project_id not in my_projects:
                    my_projects[project_id] = {
                        "name": project_name,
                        "date": datetime.date.today().strftime("%Y-%m-%d"),
                        "activities": {}
                    }
                
                my_projects[project_id]["activities"][act_id] = {
                    "name": act_name,
                    "planned_qty": planned_qty,
                    "budget": budget,
                    # Convert dates to strings so they can be saved in the JSON file securely
                    "planned_start": planned_start.strftime("%Y-%m-%d"),
                    "planned_end": planned_end.strftime("%Y-%m-%d"),
                    "planned_duration": calculated_duration, 
                    "actual_qty": 0.0,
                    "actual_cost": 0.0,
                    "actual_duration": 0
                }
                
                st.session_state.global_db[tenant] = my_projects
                save_database(st.session_state.global_db)
                st.success(f"Activity '{act_name}' added! Programmed duration: {calculated_duration} Days.")
            else:
                st.error("Error: Please fill in all text input parameter fields before saving.")

# --- Logic: Update Daily Progress ---
elif menu_choice == "2. Update Daily Progress":
    st.header("Update Daily Progress Metrics")
    
    if not my_projects:
        st.warning("No projects found in your database. Please setup a project first.")
    else:
        project_list = list(my_projects.keys())
        selected_proj = st.selectbox("Select Project to Update", project_list)
        
        activities = my_projects[selected_proj]["activities"]
        if not activities:
            st.warning("No activities found in this project.")
        else:
            act_list = list(activities.keys())
            selected_act = st.selectbox("Select Target Process Activity", act_list)
            
            activity_data = activities[selected_act]
            st.info(f"Modifying: {activity_data['name']} | Planned Qty: {activity_data['planned_qty']} | Scheduled Duration: {activity_data.get('planned_duration', 0)} Days")
            
            with st.form("update_form"):
                qty_done = st.number_input("Quantity Completed Since Last Update", min_value=0.0)
                cost_incurred = st.number_input("Cost Incurred Since Last Update (Rs.)", min_value=0.0)
                days_worked = st.number_input("Days Worked Since Last Update", min_value=0, step=1)
                
                update_btn = st.form_submit_button("Submit Operational Progress Update")
                
                if update_btn:
                    my_projects[selected_proj]["activities"][selected_act]["actual_qty"] += qty_done
                    my_projects[selected_proj]["activities"][selected_act]["actual_cost"] += cost_incurred
                    current_dur = my_projects[selected_proj]["activities"][selected_act].get("actual_duration", 0)
                    my_projects[selected_proj]["activities"][selected_act]["actual_duration"] = current_dur + days_worked
                    
                    st.session_state.global_db[tenant] = my_projects
                    save_database(st.session_state.global_db)
                    st.success("Progress record successfully updated!")

# --- Logic: Generate Progress Report ---
elif menu_choice == "3. Generate Progress Report":
    st.header("Project Performance Dashboard")
    
    if not my_projects:
        st.warning("No active records found in your workspace.")
    else:
        project_list = list(my_projects.keys())
        selected_proj = st.selectbox("Select Target Project Dashboard", project_list)
        project_data = my_projects[selected_proj]
        
        st.subheader(f"Performance Metrics: {project_data['name']} ({selected_proj})")
        
        total_budget = 0
        total_actual = 0
        
        for act_id, details in project_data["activities"].items():
            
            # Fetch the baseline dates for the report header
            p_start = details.get("planned_start", "N/A")
            p_end = details.get("planned_end", "N/A")
            
            st.markdown(f"**Activity Line: {act_id} - {details['name']}** | 🗓️ Baseline: {p_start} to {p_end}")
            
            planned_qty = details["planned_qty"]
            actual_qty = details["actual_qty"]
            budget = details["budget"]
            actual_cost = details["actual_cost"]
            
            planned_dur = details.get("planned_duration", 0)
            actual_dur = details.get("actual_duration", 0)
            
            total_budget += budget
            total_actual += actual_cost
            
            percent_complete = (actual_qty / planned_qty * 100) if planned_qty > 0 else 0
            cost_variance = budget - actual_cost
            dur_variance = planned_dur - actual_dur 
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Completion", f"{percent_complete:.1f}%")
            col2.metric("Output (Qty)", f"{actual_qty}/{planned_qty}")
            col3.metric("Cost Variance", f"Rs. {cost_variance:,.0f}", delta=cost_variance)
            col4.metric("Schedule Variance", f"{dur_variance} Days", delta=dur_variance)
            
            with col5:
                if cost_variance < 0:
                    st.error("BUDGET OVERRUN")
                elif dur_variance < 0 and percent_complete < 100:
                    st.error("SCHEDULE DELAY")
                elif percent_complete >= 100:
                    st.success("COMPLETED")
                elif percent_complete > 0:
                    st.warning("IN PROGRESS")
                else:
                    st.info("NOT STARTED")
                
            st.divider()
            
        st.markdown(f"### Total Project Budget: **Rs. {total_budget:,.2f}**")
        st.markdown(f"### Cumulative Actual Cost: **Rs. {total_actual:,.2f}**")
