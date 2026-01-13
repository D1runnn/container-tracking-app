import streamlit as st
import pandas as pd
import requests
import base64
import io
import os

st.set_page_config(page_title="Container Traffic Control", layout="wide")

# --- DATA LOADING (Direct from Folder) ---
@st.cache_data(ttl=2)
def load_data():
    # This checks if the file actually exists in the GitHub folder
    file_path = "loading_schedule.xlsx"
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        return None

df = load_data()

if df is None:
    st.error("❌ loading_schedule.xlsx not found in GitHub. Please upload it to the main folder.")
    st.stop()

# --- APP UI ---
st.title("🚛 Container Entry System")

tab1, tab2 = st.tabs(["🛡️ Guard View", "🏢 Office Edit"])

with tab1:
    search = st.text_input("Enter Booking Number:").strip().upper()
    if search:
        # We ensure Booking_No is treated as a string for searching
        match = df[df['Booking_No'].astype(str) == search]
        if not match.empty:
            res = match.iloc[0]
            st.success(f"### PROCEED TO {res['Zone']} - {res['Bay']}")
        else:
            st.error("Booking Not Found.")
    
    st.dataframe(df)

with tab2:
    # We use a simple hardcoded password check first to see if it loads
    pwd = st.text_input("Office Password", type="password")
    if pwd == st.secrets.get("OFFICE_PASSWORD", "admin123"):
        st.write("Edit Mode Active")
        edited_df = st.data_editor(df)
        if st.button("Save Changes"):
            st.info("Saving logic is currently paused to test loading. If you see this, the app is working!")
