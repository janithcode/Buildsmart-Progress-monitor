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
    """Loads the database from a physical JSON file so data persists across logouts and refreshes."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_database(data):
    """Saves the current database state to the JSON file immediately after any modification."""
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
            
            # Re-sync local global database from the persistent file upon successful login
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
# MAIN APP BEGINS HERE (Only accessible after successful login authentication)
# =========================================================================

# Extract the active company's username for multi-tenant data parsing
tenant = st.session_state.current_user

# Ensure a dedicated dictionary partition exists exclusively for this specific tenant company
if tenant not in st.session_state.global_db:
    st.session_state.global_db[tenant] = {}
    save_database(st.session_state.global_db)

# Define the isolated sandbox database for the logged-in company
my_projects = st.session_state.global_db[tenant]

# --- UI Header Framework ---
col_head, col_log = st.columns([8, 2])
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
        col3, col4 = st.columns(2)
        with col3:
            planned_qty = st.number_input("Planned Quantity", min_value=0.0, step=1.0)
        with col4:
            budget = st.number_input("Allocated Budget (Rs.)", min_value=0.0, step=100.0)
            
        submit_btn = st.form_submit_button("Save Activity to System")
        
        if submit_btn:
            if project_id and project_name and act_id and act_name:
                # Initialize project structural blueprint within the tenant's sandbox if missing
                if project_id not in my_projects:
                    my_projects[project_id] = {
                        "name": project_name,
                        "date": datetime.date.today().strftime("%Y-%m-%d"),
                        "activities": {}
                    }
                
                # Append the newly declared construction activity parameters
                my_projects[project_id]["activities"][act_id] = {
                    "name": act_name,
                    "planned_qty": planned_qty,
                    "budget": budget,
                    "actual_qty": 0.0,
                    "actual_cost": 0.0
                }
                
                # Commit updates instantly to global memory matrix and write structurally into the file
                st.session_state.global_db[tenant] = my_projects
                save_database(st.session_state.global_db)
                st.success(f"Activity '{act_name}' successfully added to {project_name} and committed to cloud disk storage!")
            else:
                st.error("Error: Please fill in all text input parameter fields before saving.")

# --- Logic: Update Daily Progress ---
elif menu_choice == "2. Update Daily Progress":
    st.header("Update Daily Progress Metrics")
    
    if not my_projects:
        st.warning("No projects found in your corporate database partition. Please setup a project first.")
    else:
        project_list = list(my_projects.keys())
        selected_proj = st.selectbox("Select Project to Update", project_list)
        
        activities = my_projects[selected_proj]["activities"]
        if not activities:
            st.warning("No tracking activities found within the designated project module.")
        else:
            act_list = list(activities.keys())
            selected_act = st.selectbox("Select Target Process Activity", act_list)
            
            activity_data = activities[selected_act]
            st.info(f"Currently Modifying: {activity_data['name']} | Planned baseline Target: {activity_data['planned_qty']}")
            
            with st.form("update_form"):
                qty_done = st.number_input("Quantity Completed Today", min_value=0.0)
                cost_incurred = st.number_input("Cost Incurred Today (Rs.)", min_value=0.0)
                
                update_btn = st.form_submit_button("Submit Operational Progress Update")
                
                if update_btn:
                    # Apply cumulative increments safely inside the tenant-isolated data block
                    my_projects[selected_proj]["activities"][selected_act]["actual_qty"] += qty_done
                    my_projects[selected_proj]["activities"][selected_act]["actual_cost"] += cost_incurred
                    
                    # Force save changes immediately to file system
                    st.session_state.global_db[tenant] = my_projects
                    save_database(st.session_state.global_db)
                    st.success("Progress record successfully saved and persistently logged to server space!")

# --- Logic: Generate Progress Report ---
elif menu_choice == "3. Generate Progress Report":
    st.header("Project Performance Dashboard")
    
    if not my_projects:
        st.warning("No active records found in your company workspace data stream.")
    else:
        project_list = list(my_projects.keys())
        selected_proj = st.selectbox("Select Target Project Dashboard", project_list)
        project_data = my_projects[selected_proj]
        
        st.subheader(f"Performance Metrics: {project_data['name']} Matrix Reference ({selected_proj})")
        
        total_budget = 0
        total_actual = 0
        
        for act_id, details in project_data["activities"].items():
            st.markdown(f"**Activity Line: {act_id} - {details['name']}**")
            
            planned_qty = details["planned_qty"]
            actual_qty = details["actual_qty"]
            budget = details["budget"]
            actual_cost = details["actual_cost"]
            
            total_budget += budget
            total_actual += actual_cost
            
            # Execute core automated computations
            percent_complete = (actual_qty / planned_qty * 100) if planned_qty > 0 else 0
            cost_variance = budget - actual_cost
            
            # Map analytical UI layout
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Progress Rate Completion", f"{percent_complete:.1f}%")
            col2.metric("Recorded Output Balance", f"{actual_qty} / {planned_qty}")
            col3.metric("Cost Variance Threshold", f"Rs. {cost_variance:,.2f}", delta=cost_variance)
            
            # Rule Engine Trigger Evaluation for Alerts
            if cost_variance < 0:
                col4.error("CRITICAL: BUDGET OVERRUN")
            elif percent_complete < 100 and percent_complete > 0:
                col4.warning("STATUS: IN PROGRESS")
            elif percent_complete >= 100:
                col4.success("STATUS: COMPLETED")
            else:
                col4.info("STATUS: LOGGED / NOT STARTED")
                
            st.divider()
            
        # Cumulative structural aggregations
        st.markdown(f"### Total Project Budget: **Rs. {total_budget:,.2f}**")
        st.markdown(f"### Cumulative Actual Outlay Cost: **Rs. {total_actual:,.2f}**")
