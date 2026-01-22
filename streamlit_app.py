import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Terminal Dashboard", layout="wide")

PLANNER_FILE = r'C:\Users\USER\Desktop\booking\Logistic Planner.xlsx'
SHEET_NAME = 'Bookings'

# Map showing how many bays each zone has
ZONE_LIMITS = {
    "Zone 1": 1,
    "Zone 2": 5,
    "Zone 3": 4,
    "Zone 4": 5
}

# --- 2. SESSION STATE (The Live Yard Data) ---
# This stores: {"Zone 1": {"Bay 1": "BOOKING123"}, "Zone 2": {"Bay 1": None, ...}}
if 'yard_status' not in st.session_state:
    st.session_state.yard_status = {
        z: {f"Bay {i+1}": None for i in range(count)} 
        for z, count in ZONE_LIMITS.items()
    }

def load_data():
    try:
        if os.path.exists(PLANNER_FILE):
            data = pd.read_excel(PLANNER_FILE, sheet_name=SHEET_NAME)
            data['Date'] = pd.to_datetime(data['Date']).dt.date
            return data[data['Date'] == datetime.now().date()]
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return pd.DataFrame()

# --- 3. TOP CENTER SELECTION ---
st.markdown("<h1 style='text-align: center;'>🚛 Container Terminal Dashboard</h1>", unsafe_allow_html=True)

df_today = load_data()

# Centering the Check-in Box
_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    with st.container(border=True):
        st.subheader("📍 Arrival Check-In")
        booking_options = df_today['Booking No.'].dropna().astype(str).tolist()
        
        # Only show bookings that aren't already in the yard
        occupied_bookings = [val for zone in st.session_state.yard_status.values() for val in zone.values() if val]
        available_options = [b for b in booking_options if b not in occupied_bookings]
        
        selected_bno = st.selectbox("Select Arriving Booking No.", ["-- Select --"] + available_options)
        
        if selected_bno != "-- Select --":
            assigned_zone = df_today[df_today['Booking No.'].astype(str) == selected_bno]['Zone'].values[0]
            st.info(f"Assigned Zone: **{assigned_zone}**")
            
            if st.button("CONFIRM ENTRY", use_container_width=True, type="primary"):
                # Find first empty bay in assigned zone
                target_zone_bays = st.session_state.yard_status[assigned_zone]
                assigned_bay = None
                for b_name, occupant in target_zone_bays.items():
                    if occupant is None:
                        assigned_bay = b_name
                        break
                
                if assigned_bay:
                    st.session_state.yard_status[assigned_zone][assigned_bay] = selected_bno
                    st.toast(f"{selected_bno} sent to {assigned_zone} - {assigned_bay}")
                    st.rerun()
                else:
                    st.error(f"No space available in {assigned_zone}!")

st.divider()

# --- 4. THE LIVE YARD (Columns for Zones) ---
st.subheader("🏗️ Live Yard Occupancy")
zone_cols = st.columns(len(ZONE_LIMITS))

for idx, (zone_name, bay_dict) in enumerate(st.session_state.yard_status.items()):
    with zone_cols[idx]:
        st.markdown(f"### {zone_name}")
        
        for bay_name, booking in bay_dict.items():
            # Creating a visual 'Bay' card
            if booking:
                # Occupied State
                with st.container(border=True):
                    st.markdown(f"**{bay_name}**")
                    st.error(f"ID: {booking}")
                    if st.button(f"Release {bay_name}", key=f"rel_{zone_name}_{bay_name}"):
                        st.session_state.yard_status[zone_name][bay_name] = None
                        st.rerun()
            else:
                # Empty State
                with st.container(border=True):
                    st.markdown(f"**{bay_name}**")
                    st.success("AVAILABLE")
                    st.caption("Waiting for truck...")

# Add manual refresh for Excel updates
if st.button("🔄 Sync with Planner Excel"):
    st.rerun()
