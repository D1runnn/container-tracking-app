import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Guard Check-In Terminal", layout="wide")

# Local File Path
PLANNER_FILE = r'C:\Users\USER\Desktop\booking\Logistic Planner.xlsx'
SHEET_NAME = 'Bookings'

# Define Bay Structure
ZONE_STRUCTURE = {
    "Zone 1": ["Bay 1"],
    "Zone 2": ["Bay 1", "Bay 2", "Bay 3", "Bay 4", "Bay 5"],
    "Zone 3": ["Bay 1", "Bay 2", "Bay 3", "Bay 4"],
    "Zone 4": ["Bay 1", "Bay 2", "Bay 3", "Bay 4", "Bay 5"]
}

# --- 2. STATE MANAGEMENT & DATA ---
if 'occupied_bays' not in st.session_state:
    st.session_state.occupied_bays = {zone: [] for zone in ZONE_STRUCTURE}

def load_todays_bookings():
    try:
        if os.path.exists(PLANNER_FILE):
            data = pd.read_excel(PLANNER_FILE, sheet_name=SHEET_NAME)
            # Ensure date column is datetime and Booking No is string
            data['Date'] = pd.to_datetime(data['Date']).dt.date
            today = datetime.now().date()
            # Filter for today only
            todays_data = data[data['Date'] == today]
            return todays_data
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return pd.DataFrame()

# --- 3. UI LAYOUT ---
st.title("🚛 Container Terminal: Guard Check-In")
st.subheader(f"Schedule for {datetime.now().strftime('%d %B %Y')}")

df = load_todays_bookings()

# Split screen into Check-in (Left) and Live Status (Right)
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.header("Step 1: Driver Check-In")
    
    if not df.empty:
        # Create a searchable dropdown of Booking Numbers
        booking_options = df['Booking No.'].dropna().astype(str).tolist()
        selected_bno = st.selectbox("Select Booking No.", ["-- Select Booking --"] + booking_options)

        if selected_bno != "-- Select Booking --":
            # Find the zone assigned by the planner
            assigned_zone = df[df['Booking No.'].astype(str) == selected_bno]['Zone'].values[0]
            
            # Logic to find the first available bay in that zone
            all_bays = ZONE_STRUCTURE.get(assigned_zone, [])
            occupied = st.session_state.occupied_bays.get(assigned_zone, [])
            available_bays = [b for b in all_bays if b not in occupied]

            st.info(f"📍 **Planner Instruction:** Proceed to {assigned_zone}")

            if available_bays:
                target_bay = available_bays[0]
                st.success(f"### ✅ ASSIGN TO: {assigned_zone} - {target_bay}")
                
                if st.button("CONFIRM CHECK-IN", use_container_width=True, type="primary"):
                    st.session_state.occupied_bays[assigned_zone].append(target_bay)
                    st.toast(f"{selected_bno} assigned to {target_bay}")
                    st.rerun()
            else:
                st.error(f"🚨 ALERT: All bays in {assigned_zone} are currently full! Please hold driver.")
    else:
        st.warning("No bookings found in the planner for today.")

with col_right:
    st.header("Step 2: Live Yard Occupancy")
    
    # Display the status of every zone and bay
    for zone, bays in ZONE_STRUCTURE.items():
        with st.container(border=True):
            st.write(f"**{zone}**")
            cols = st.columns(len(bays))
            for idx, bay in enumerate(bays):
                is_busy = bay in st.session_state.occupied_bays[zone]
                
                if is_busy:
                    if cols[idx].button(f"🔴 {bay}\n(Clear)", key=f"btn_{zone}_{bay}"):
                        st.session_state.occupied_bays[zone].remove(bay)
                        st.rerun()
                else:
                    cols[idx].write(f"🟢 {bay}")

# Visualizing the layout for the guard


# --- 4. OPTIONAL REFRESH ---
if st.button("🔄 Refresh Data from Planner"):
    st.rerun()
