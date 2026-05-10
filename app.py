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
    
    # --- CLEANING UP DECIMALS ---
    # Convert numeric columns to 'Int64' which handles missing values but keeps numbers as integers
    cols_to_fix = ['Bib', 'Loop Count', 'Mileage']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    return df

if 'view_index' not in st.session_state:
    st.session_state.view_index = 0

views = ["OVERALL 6-HOUR", "FEMALE 6-HOUR", "MALE 6-HOUR"]
current_view = views[st.session_state.view_index % len(views)]

st.markdown(f"<h1 style='text-align: center; font-size: 60px;'>🏆 {current_view}</h1>", unsafe_allow_html=True)

try:
    data = get_leaderboard_data()

    # Filtering logic
    filtered_df = data[data['Event'].str.contains("6HR", na=False, case=False)]

    if "FEMALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'F']
    elif "MALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'M']

    # Sort by Loop Count (Highest first)
    leaderboard = filtered_df.sort_values(by='Loop Count', ascending=False).head(15)

    # Display the table
    st.table(leaderboard[['Bib', 'Name', 'Loop Count', 'Mileage']])

except Exception as e:
    st.error(f"Aligning data columns... (Current Issue: {e})")
    if 'data' in locals():
        st.write("Available columns found:", list(data.columns))

time.sleep(15)
st.session_state.view_index += 1
st.rerun()
