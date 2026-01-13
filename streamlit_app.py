import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="Warehouse Command Center", layout="wide")

def save_to_github(df):
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
            "message": "Dashboard Update",
            "content": base64.b64encode(content).decode("utf-8"),
            "sha": sha
        }
        requests.put(url, json=payload, headers=headers)
        return True
    return False

# --- 2. DATA LOADING ---
@st.cache_data(ttl=2) # Very low TTL for live feel
def load_data():
    try:
        data = pd.read_excel(st.secrets["FILE_PATH"])
        data.columns = [str(c).strip() for c in data.columns]
        return data
    except:
        return None

df = load_data()

# --- 3. THE COMMAND CENTER ---
st.title("🏗️ Warehouse Loading Command Center")

# --- TOP STATS ---
total_in = len(df[df['Status'] == 'Arrived'])
pending = len(df[df['Status'] == 'Expected'])
s1, s2, s3 = st.columns(3)
s1.metric("Bays Occupied", f"{total_in}")
s2.metric("Upcoming Today", f"{pending}")
s3.metric("System Time", datetime.now().strftime("%H:%M"))

# --- MAIN INTERFACE TABS ---
tab_map, tab_edit, tab_search = st.tabs(["🗺️ Visual Yard Map", "📝 Bulk Editor", "🔍 Guard Search"])

with tab_map:
    # 4 Zone Layout
    z_config = {"Zone 1": 1, "Zone 2": 5, "Zone 3": 4, "Zone 4": 5}
    z_cols = st.columns(4)
    
    for i, (z_name, n_bays) in enumerate(z_config.items()):
        with z_cols[i]:
            st.subheader(z_name)
            for b_num in range(1, n_bays + 1):
                b_name = f"Bay {b_num}"
                bay_data = df[(df['Zone'] == z_name) & (df['Bay'] == b_name)]
                
                with st.container(border=True):
                    if not bay_data.empty:
                        # Sort to find who is currently in the bay
                        bay_data = bay_data.sort_values(by='Time')
                        top_job = bay_data.iloc[0]
                        status = str(top_job['Status'])
                        
                        # Visual Header
                        if status == "Arrived":
                            st.error(f"🔴 {b_name}: {top_job['Booking_No']}")
                        elif status == "Delayed":
                            st.warning(f"🟡 {b_name}: {top_job['Booking_No']}")
                        else:
                            st.info(f"🔵 {b_name}: {top_job['Booking_No']}")
                        
                        st.caption(f"Schedule: {top_job['Time']}")
                        
                        # --- ONE-CLICK ACTIONS ---
                        c1, c2 = st.columns(2)
                        # Password protected actions
                        pwd = st.sidebar.text_input(f"Admin Key for {b_name}", type="password", key=f"pwd_{z_name}_{b_name}")
                        if pwd == st.secrets["OFFICE_PASSWORD"]:
                            if c1.button("✅ Arrived", key=f"arr_{z_name}_{b_name}"):
                                df.loc[df['Booking_No'] == top_job['Booking_No'], 'Status'] = 'Arrived'
                                save_to_github(df)
                                st.rerun()
                            if c2.button("🏁 Clear", key=f"clr_{z_name}_{b_name}"):
                                # Remove or mark as completed
                                df = df[df['Booking_No'] != top_job['Booking_No']]
                                save_to_github(df)
                                st.rerun()
                    else:
                        st.success(f"🟢 {b_name}: Available")

with tab_edit:
    st.info("🏢 Logistics Office: Manage Schedule via Dropdowns")
    admin_pwd = st.text_input("Enter Admin Password to Edit:", type="password", key="bulk_admin")
    
    if admin_pwd == st.secrets["OFFICE_PASSWORD"]:
        # 1. Define the dropdown options
        zone_options = ["Zone 1", "Zone 2", "Zone 3", "Zone 4"]
        bay_options = [f"Bay {i}" for i in range(1, 6)]
        status_options = ["Expected", "Arrived", "Delayed", "Completed"]

        # 2. Configure the data editor with dropdowns
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Zone": st.column_config.SelectboxColumn(
                    "Warehouse Zone",
                    help="Select the assigned area",
                    options=zone_options,
                    required=True,
                ),
                "Bay": st.column_config.SelectboxColumn(
                    "Loading Bay",
                    options=bay_options,
                    required=True,
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Current Status",
                    options=status_options,
                    required=True,
                ),
                "Time": st.column_config.TimeColumn(
                    "Scheduled Time",
                    format="HH:mm",
                    step=60,
                ),
                "Booking_No": st.column_config.TextColumn(
                    "Booking Number",
                    max_chars=15,
                    validate="^[A-Z0-9-]+$", # Only allows Uppercase, Numbers, and Dashes
                )
            },
            hide_index=True,
        )
        
        if st.button("🚀 Sync All Changes to Yard Map"):
            with st.spinner("Updating GitHub..."):
                if save_to_github(edited_df):
                    st.success("Yard Map Updated! The Guards will see the changes instantly.")
                    st.cache_data.clear()
                    st.rerun()

with tab_search:
    query = st.text_input("Search Booking No:").upper()
    if query:
        match = df[df['Booking_No'].astype(str) == query]
        if not match.empty:
            st.dataframe(match)
