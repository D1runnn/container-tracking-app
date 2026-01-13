import streamlit as st
import pandas as pd

# ... (Keep your existing data loading code here) ...

st.title("🏗️ Live Warehouse Bay Monitor")

# Define the layout based on your map
# Zone 1: 1 Bay | Zone 2: 5 Bays | Zone 3: 4 Bays | Zone 4: 5 Bays
zone_configs = {
    "Zone 1": 1,
    "Zone 2": 5,
    "Zone 3": 4,
    "Zone 4": 5
}

# Create 4 main columns for the 4 Zones
zone_cols = st.columns(4)

for i, (zone_name, num_bays) in enumerate(zone_configs.items()):
    with zone_cols[i]:
        st.markdown(f"### {zone_name}")
        
        # Loop through each bay in this zone
        for bay_num in range(1, num_bays + 1):
            bay_label = f"Bay {bay_num}"
            
            # Filter data for this specific Bay
            bay_data = df[(df['Zone'] == zone_name) & (df['Bay'] == bay_label)]
            
            # Create a visual box for the Bay
            with st.container(border=True):
                if not bay_data.empty:
                    # Sort by time to see what's next
                    bay_data = bay_data.sort_values(by='Time')
                    
                    # Current/Next Container
                    current = bay_data.iloc[0]
                    st.markdown(f"**{bay_label}**")
                    st.info(f"🚚 {current['Booking_No']}\n\nTime: {current['Time']}")
                    
                    # Upcoming Containers (if any)
                    if len(bay_data) > 1:
                        with st.expander("View Upcoming"):
                            for _, row in bay_data.iloc[1:].iterrows():
                                st.write(f"• {row['Booking_No']} ({row['Time']})")
                else:
                    # Empty Bay
                    st.markdown(f"**{bay_label}**")
                    st.caption("✅ Available")
