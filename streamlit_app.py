import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Terminal Dashboard", layout="wide")

# IMPORTANT: For GitHub/Streamlit Cloud, put 'Logistic Planner.xlsx' 
# in the same folder as your script and just use the filename.
PLANNER_FILE = 'Logistic Planner.xlsx' 
SHEET_NAME = 'Bookings'

ZONE_LIMITS = {
    "Zone 1": 1,
    "Zone 2": 5,
    "Zone 3": 4,
    "Zone 4": 5
}

# --- 2. SESSION STATE ---
if 'yard_status' not in st.session_state:
    st.session_state.yard_status = {
        z: {f"Bay {i+1}": None for i in range(count)} 
        for z, count in ZONE_LIMITS.items()
    }

def load_data():
    try:
        if os.path.exists(PLANNER_FILE):
            data = pd.read_excel(PLANNER_FILE, sheet_name=SHEET_NAME)
            # CLEANING: Remove leading/trailing spaces from column names
            data.columns = [str(c).strip() for c in data.columns]
            
            # Date filtering
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date']).dt.date
                return data[data['Date'] == datetime.now().date()]
            return data
        else:
            st.error(f"File '{PLANNER_FILE}' not found in GitHub repository.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- 3. TOP CENTER SELECTION ---
st.markdown("<h1 style='text-align: center;'>🚛 Container Terminal Dashboard</h1>", unsafe_allow_html=True)

df_today = load_data()

# Debugger (Hidden by default, click to see if names match)
with st.expander("🛠️ Column Name Debugger (If Error occurs)"):
    if not df_today.empty:
        st.write("Detected Columns:", list(df_today.columns))
    else:
        st.write("No data loaded. Ensure the Excel file is uploaded to GitHub.")

_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    with st.container(border=True):
        st.subheader("📍 Arrival Check-In")
        
        # Using a flexible way to find the Booking No column
        col_list = list(df_today.columns)
        # Tries to find 'Booking No.' or 'Booking No' or 'Booking_No'
        target_col = next((c for c in col_list if "Booking" in c), None)
        zone_col = next((c for c in col_list if "Zone" in c), None)

        if target_col and not df_today.empty:
            booking_options = df_today[target_col].dropna().astype(str).tolist()
            occupied_bookings = [val for zone in st.session_state.yard_status.values() for val in zone.values() if val]
            available_options = [b for b in booking_options if b not in occupied_bookings]
            
            selected_bno = st.selectbox("Select Arriving Booking No.", ["-- Select --"] + available_options)
            
            if selected_bno != "-- Select --":
                assigned_zone = df_today[df_today[target_col].astype(str) == selected_bno][zone_col].values[0]
                st.info(f"Assigned Zone: **{assigned_zone}**")
                
                if st.button("CONFIRM ENTRY", use_container_width=True, type="primary"):
                    target_zone_bays = st.session_state.yard_status.get(assigned_zone, {})
                    assigned_bay = next((b_name for b_name, occ in target_zone_bays.items() if occ is None), None)
                    
                    if assigned_bay:
                        st.session_state.yard_status[assigned_zone][assigned_bay] = selected_bno
                        st.rerun()
                    else:
                        st.error(f"No space in {assigned_zone}!")
        else:
            st.warning("Could not find 'Booking No.' column in Excel.")

st.divider()

# --- 4. THE LIVE YARD ---
zone_cols = st.columns(len(ZONE_LIMITS))
for idx, (zone_name, bay_dict) in enumerate(st.session_state.yard_status.items()):
    with zone_cols[idx]:
        st.markdown(f"### {zone_name}")
        for bay_name, booking in bay_dict.items():
            if booking:
                with st.container(border=True):
                    st.error(f"**{bay_name}**\n\n{booking}")
                    if st.button(f"Release", key=f"rel_{zone_name}_{bay_name}"):
                        st.session_state.yard_status[zone_name][bay_name] = None
                        st.rerun()
            else:
                with st.container(border=True):
                    st.success(f"**{bay_name}**\n\nAVAILABLE")
