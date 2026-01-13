import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Container Traffic Control", layout="wide")

# This function updates the Excel file back to GitHub when changes are made
def update_github_excel(df):
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["REPO_NAME"]
    path = st.secrets["FILE_PATH"]
    
    # Convert DataFrame back to Excel bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    content = output.getvalue()

    # Get current file info (sha)
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        sha = r.json()['sha']
        # Upload new version
        payload = {
            "message": "Update schedule (delay/edit)",
            "content": base64.b64encode(content).decode("utf-8"),
            "sha": sha
        }
        requests.put(url, json=payload, headers=headers)
        return True
    return False

# --- 2. DATA LOADING ---
@st.cache_data(ttl=5) # Refreshes every 5 seconds for live updates
def load_data():
    return pd.read_excel(st.secrets["FILE_PATH"])

try:
    df = load_data()
except Exception:
    st.error("Excel file not found. Check FILE_PATH in Secrets.")
    st.stop()

# --- 3. THE UI LAYOUT ---
st.title("🚛 Gate Management System")

tab1, tab2 = st.tabs(["🛡️ Guard House View", "⚙️ Office (Edit Delays)"])

# --- TAB 1: GUARD VIEW ---
with tab1:
    st.header("Container Check-In")
    search_input = st.text_input("ENTER BOOKING NUMBER:", "").strip().upper()

    if search_input:
        # Match booking number
        result = df[df['Booking_No'].astype(str) == search_input]
        
        if not result.empty:
            row = result.iloc[0]
            # Visual Instruction Card
            st.markdown(f"""
                <div style="background-color:#1E3A8A; color:white; padding:30px; border-radius:15px; text-align:center;">
                    <h1 style="font-size:50px; margin:0;">ZONE: {row['Zone']}</h1>
                    <h2 style="font-size:40px; margin:0;">BAY: {row['Bay']}</h2>
                    <hr>
                    <h3>STATUS: {row['Status']} | SCHEDULED: {row['Time']}</h3>
                </div>
            """, unsafe_allow_value=True)
        else:
            st.warning("⚠️ Booking Number not found. Please refer to Logistics Office.")

# --- TAB 2: OFFICE VIEW ---
with tab2:
    st.header("Live Schedule Editor")
    st.write("Modify the Bay, Time, or Status below if there is a delay.")
    
    # Interactive Table
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Save & Sync Changes"):
        with st.spinner("Syncing with master file..."):
            success = update_github_excel(edited_df)
            if success:
                st.success("Master Schedule Updated!")
                st.cache_data.clear()
            else:
                st.error("Sync failed. Check GitHub Token.")

# --- FOOTER: WAREHOUSE OVERVIEW ---
st.divider()
st.subheader("Current Bay Occupancy Map")
z1, z2, z3, z4 = st.columns(4)

zones = ["Zone 1", "Zone 2", "Zone 3", "Zone 4"]
cols = [z1, z2, z3, z4]

for i, zone_name in enumerate(zones):
    with cols[i]:
        st.info(f"**{zone_name}**")
        zone_subset = df[df['Zone'] == zone_name][['Bay', 'Time', 'Status']]
        st.dataframe(zone_subset, hide_index=True)
