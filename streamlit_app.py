import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

# --- 1. INITIAL CONFIGURATION ---
st.set_page_config(page_title="Logistics Command Center", layout="wide", initial_sidebar_state="expanded")

# Define the warehouse structure (Matching your map)
ZONE_LIMITS = {
    "Zone 1": 1,
    "Zone 2": 5,
    "Zone 3": 4,
    "Zone 4": 5
}

# --- 2. GITHUB SYNC ENGINE ---
def save_to_github(df):
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["REPO_NAME"]
        path = st.secrets["FILE_PATH"]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        content = output.getvalue()

        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            sha = r.json()['sha']
            payload = {
                "message": f"Dashboard Update: {datetime.now().strftime('%H:%M')}",
                "content": base64.b64encode(content).decode("utf-8"),
                "sha": sha
            }
            res = requests.put(url, json=payload, headers=headers)
            return res.status_code in [200, 201]
        return False
    except Exception as e:
        st.error(f"GitHub Sync Error: {e}")
        return False

# --- 3. DATA LOADER (FAST CACHE) ---
@st.cache_data(ttl=2)
def load_data():
    try:
        file_path = st.secrets["FILE_PATH"]
        data = pd.read_excel(file_path)
        # Clean columns to prevent KeyErrors
        data.columns = [str(c).strip() for c in data.columns]
        return data
    except Exception:
        # Fallback if file is missing/corrupt
        return pd.DataFrame(columns=["Booking_No", "Zone", "Bay", "Time", "Status"])

df = load_data()

# --- 4. SIDEBAR - SYSTEM CONTROL ---
with st.sidebar:
    st.header("🔑 Admin Access")
    admin_key = st.text_input("Enter Authorization Code", type="password")
    is_admin = admin_key == st.secrets["OFFICE_PASSWORD"]
    
    if is_admin:
        st.success("Admin Mode Active")
        if st.button("🔄 Force Global Refresh"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("Viewer Mode: Actions Restricted")

# --- 5. MAIN DASHBOARD UI ---
st.title("🚛 Container Terminal Command Center")

tab_map, tab_office, tab_search = st.tabs([
    "📍 LIVE YARD MAP", 
    "📝 OFFICE MANAGEMENT", 
    "🔍 GUARD SEARCH"
])

# --- TAB: YARD MAP ---
with tab_map:
    z_cols = st.columns(4)
    
    for i, (z_name, n_bays) in enumerate(ZONE_LIMITS.items()):
        with z_cols[i]:
            st.subheader(z_name)
            for b_num in range(1, n_bays + 1):
                b_name = f"Bay {b_num}"
                # Filter for this bay
                bay_data = df[(df['Zone'] == z_name) & (df['Bay'] == b_name)].sort_values(by='Time')
                
                with st.container(border=True):
                    if not bay_data.empty:
                        top_job = bay_data.iloc[0]
                        status = str(top_job['Status'])
                        
                        # Color coding
                        if status == "Arrived":
                            st.error(f"🔴 {b_name}: {top_job['Booking_No']}")
                        elif status == "Delayed":
                            st.warning(f"🟡 {b_name}: {top_job['Booking_No']}")
                        else:
                            st.info(f"🔵 {b_name}: {top_job['Booking_No']}")
                        
                        st.caption(f"Schedule: {top_job['Time']}")
                        
                        # Upcoming previews
                        if len(bay_data) > 1:
                            with st.expander("Upcoming"):
                                for _, row in bay_data.iloc[1:3].iterrows():
                                    st.write(f"• {row['Booking_No']} ({row['Time']})")
                        
                        # Admin Quick Actions
                        if is_admin:
                            c1, c2 = st.columns(2)
                            if c1.button("Arrive", key=f"arr_{z_name}_{b_name}"):
                                df.loc[df['Booking_No'] == top_job['Booking_No'], 'Status'] = 'Arrived'
                                if save_to_github(df): st.rerun()
                            if c2.button("Clear", key=f"clr_{z_name}_{b_name}"):
                                updated_df = df[df['Booking_No'] != top_job['Booking_No']]
                                if save_to_github(updated_df): st.rerun()
                    else:
                        st.success(f"🟢 {b_name}")
                        st.caption("Available")

# --- TAB: OFFICE MANAGEMENT ---
with tab_office:
    if is_admin:
        st.header("Add New Schedule")
        with st.form("new_booking", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            with f1:
                new_bno = st.text_input("Booking No").upper().strip()
                sel_zone = st.selectbox("Assign Zone", list(ZONE_LIMITS.keys()))
            with f2:
                # DYNAMIC BAY SELECTION
                b_count = ZONE_LIMITS[sel_zone]
                sel_bay = st.selectbox("Assign Bay", [f"Bay {j}" for j in range(1, b_count + 1)])
                sel_status = st.selectbox("Status", ["Expected", "Delayed", "Arrived"])
            with f3:
                sel_time = st.time_input("Scheduled Time")
                if st.form_submit_button("➕ Add Booking"):
                    new_entry = pd.DataFrame([{
                        "Booking_No": new_bno, "Zone": sel_zone, 
                        "Bay": sel_bay, "Time": sel_time.strftime("%H:%M"), 
                        "Status": sel_status
                    }])
                    final_df = pd.concat([df, new_entry], ignore_index=True)
                    if save_to_github(final_df):
                        st.cache_data.clear()
                        st.rerun()

        st.divider()
        st.header("Master Schedule Editor")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 Sync Table Changes"):
            if save_to_github(edited_df):
                st.cache_data.clear()
                st.success("Changes saved!")
                st.rerun()
    else:
        st.warning("Please enter the Admin Access Code in the sidebar to unlock editing.")

# --- TAB: GUARD SEARCH ---
with tab_search:
    st.header("Check-In Terminal")
    search_q = st.text_input("Scan or Type Booking Number:").upper().strip()
    if search_q:
        match = df[df['Booking_No'].astype(str).str.upper() == search_q]
        if not match.empty:
            res = match.iloc[0]
            st.balloons()
            st.success(f"### PROCEED TO {res['Zone']} - {res['Bay']}")
            st.write(f"**Schedule Time:** {res['Time']} | **Status:** {res['Status']}")
        else:
            st.error("Booking Number Not Found. Direct driver to Logistics Office.")
