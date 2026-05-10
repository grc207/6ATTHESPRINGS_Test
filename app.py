import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

st.set_page_config(page_title="LIVE LEADERBOARD", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_leaderboard_data():
    # header=1 tells Python that the actual titles are on the SECOND row of the sheet
    df = conn.read(worksheet="Statistics", ttl="5s", header=1)
    
    # Clean up column names in case there are hidden spaces
    df.columns = df.columns.str.strip()
    
    # Convert Loop Count to numbers so we can sort properly
    if 'Loop Count' in df.columns:
        df['Loop Count'] = pd.to_numeric(df['Loop Count'], errors='coerce').fillna(0)
    return df

if 'view_index' not in st.session_state:
    st.session_state.view_index = 0

views = ["OVERALL 6-HOUR", "FEMALE 6-HOUR", "MALE 6-HOUR"]
current_view = views[st.session_state.view_index % len(views)]

st.markdown(f"<h1 style='text-align: center; font-size: 60px;'>🏆 {current_view}</h1>", unsafe_allow_html=True)

try:
    data = get_leaderboard_data()

    # Filtering logic - using the exact column names from your screenshot
    # We check if the 'Event' column contains "6HR"
    filtered_df = data[data['Event'].str.contains("6HR", na=False, case=False)]

    if "FEMALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'F']
    elif "MALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'M']

    # Sort by Loop Count (Highest first)
    leaderboard = filtered_df.sort_values(by='Loop Count', ascending=False).head(15)

    # Display the table with your specific column names
    st.table(leaderboard[['Bib', 'Name', 'Loop Count', 'Mileage']])

except Exception as e:
    # This will show us if a column name is still slightly off
    st.error(f"Aligning data columns... (Current Issue: {e})")
    st.write("Available columns found:", list(data.columns) if 'data' in locals() else "None")

time.sleep(15)
st.session_state.view_index += 1
st.rerun()
