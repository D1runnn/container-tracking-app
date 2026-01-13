import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="Container Traffic Control", layout="wide")

# This handles the GitHub saving logic
def update_github_excel(df):
    # Use the labels (Keys) here, not the actual values
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

# --- 2. DATA LOADING ---
@st.cache_data(ttl=5)
def load_data():
    # Use the label "FILE_PATH" to find the filename
    return pd.read_excel(st.secrets["FILE_PATH"])

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading Excel: {e}")
    st.stop()

# --- 3. UI TABS ---
tab1, tab2 = st.tabs(["🛡️ Guard Check-In", "🏢 Logistics Office (Edit Access)"])

# --- TAB 1: GUARD HOUSE VIEW ---
with tab1:
    st.header("Search Incoming Container")
    search_input = st.text_input("ENTER BOOKING NUMBER:", "").strip().upper()

    if search_input:
        result = df[df['Booking_No'].astype(str) == search_input]
        if not result.empty:
            row = result.iloc[0]
            st.success(f"### PROCEED TO {row['Zone']}")
            st.metric(label="ASSIGNED BAY", value=row['Bay'])
            st.info(f"Scheduled Time: {row['Time']} | Status: {row['Status']}")
        else:
            st.error("Booking Number not found. Direct driver to Office.")

    st.divider()
    st.subheader("Current Warehouse Status")
    st.dataframe(df[['Booking_No', 'Zone', 'Bay', 'Time', 'Status']], use_container_width=True)

# --- TAB 2: LOGISTICS OFFICE VIEW ---
with tab2:
    st.header("Office Management Portal")
    password = st.text_input("Enter Office Authorization Code:", type="password")
    
    # Use the label "OFFICE_PASSWORD" to check the password
    if password == st.secrets["OFFICE_PASSWORD"]:
        st.write("✅ Access Granted.")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Apply Changes & Notify Gate"):
            with st.spinner("Syncing changes..."):
                if update_github_excel(edited_df):
                    st.success("Changes saved!")
                    st.cache_data.clear()
                else:
                    st.error("Sync failed. Check GitHub Token and Permissions.")
    elif password == "":
        st.info("Enter password to unlock editing features.")
    else:
        st.error("Incorrect Password.")
