import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="Container Traffic Control", layout="wide")

# GitHub saving logic (unchanged)
def update_github_excel(df):
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
            "message": "Office Update: Status/Delay change",
            "content": base64.b64encode(content).decode("utf-8"),
            "sha": sha
        }
        requests.put(url, json=payload, headers=headers)
        return True
    return False

# --- 2. DATA LOADING (CLEANED) ---
@st.cache_data(ttl=5)
def load_data():
    try:
        # Load the file
        data = pd.read_excel(st.secrets["FILE_PATH"])
        # CRITICAL FIX: Strip invisible spaces from column names
        data.columns = [str(c).strip() for c in data.columns]
        return data
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return None

df = load_data()

# Stop if data didn't load
if df is None:
    st.stop()

# --- 3. UI TABS ---
tab1, tab2 = st.tabs(["🛡️ Guard Check-In", "🏢 Logistics Office (Edit Access)"])

with tab1:
    st.header("Search Incoming Container")
    search_input = st.text_input("ENTER BOOKING NUMBER:", "").strip().upper()

    if search_input:
        # Ensure Booking_No is treated as string for searching
        result = df[df['Booking_No'].astype(str).str.upper() == search_input]
        if not result.empty:
            row = result.iloc[0]
            st.success(f"### PROCEED TO {row['Zone']}")
            st.metric(label="ASSIGNED BAY", value=row['Bay'])
            # Safety check for status
            status_val = row['Status'] if 'Status' in row else "N/A"
            st.info(f"Scheduled Time: {row['Time']} | Status: {status_val}")
        else:
            st.error("Booking Number not found. Direct driver to Office.")

    st.divider()
    st.subheader("Current Warehouse Status")
    # Show only columns that exist
    display_cols = [c for c in ['Booking_No', 'Zone', 'Bay', 'Time', 'Status'] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

with tab2:
    st.header("Office Management Portal")
    password = st.text_input("Enter Office Authorization Code:", type="password")
    
    if password == st.secrets["OFFICE_PASSWORD"]:
        st.write("✅ Access Granted.")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Apply Changes & Notify Gate"):
            with st.spinner("Syncing changes..."):
                if update_github_excel(edited_df):
                    st.success("Changes saved!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Sync failed. Check GitHub Token.")
    elif password != "":
        st.error("Incorrect Password.")

# --- 4. LIVE BAY MONITOR ---
st.divider()
st.title("🏗️ Live Warehouse Bay Monitor")

zone_configs = {"Zone 1": 1, "Zone 2": 5, "Zone 3": 4, "Zone 4": 5}
zone_cols = st.columns(4)

for i, (zone_name, num_bays) in enumerate(zone_configs.items()):
    with zone_cols[i]:
        st.markdown(f"### {zone_name}")
        for bay_num in range(1, num_bays + 1):
            bay_label = f"Bay {bay_num}"
            bay_data = df[(df['Zone'] == zone_name) & (df['Bay'] == bay_label)]
            
            with st.container(border=True):
                st.markdown(f"**{bay_label}**")
                if not bay_data.empty:
                    bay_data = bay_data.sort_values(by='Time')
                    current = bay_data.iloc[0]
                    
                    # Color coding based on status
                    status = str(current.get('Status', '')).lower()
                    if 'arrive' in status:
                        st.error(f"OCCUPIED: {current['Booking_No']}")
                    elif 'delay' in status:
                        st.warning(f"DELAYED: {current['Booking_No']}")
                    else:
                        st.info(f"NEXT: {current['Booking_No']}")
                    
                    st.caption(f"Time: {current['Time']}")
                    
                    if len(bay_data) > 1:
                        with st.expander("Upcoming"):
                            for _, row in bay_data.iloc[1:].iterrows():
                                st.write(f"• {row['Booking_No']} ({row['Time']})")
                else:
                    st.success("✅ Available")
