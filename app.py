import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# Set up the page
st.set_page_config(page_title="LIVE LEADERBOARD", layout="wide")

# Connect to Google Sheets (This looks at your Cloud Secrets for the URL)
conn = st.connection("gsheets", type=GSheetsConnection)

def get_leaderboard_data():
    # Read the 'Statistics' tab
    # ttl="5s" means it refreshes every 5 seconds
    df = conn.read(worksheet="Statistics", ttl="5s")
    
    # Ensure the 'Loop Count' is a number so we can sort it
    df['Loop Count'] = pd.to_numeric(df['Loop Count'], errors='coerce').fillna(0)
    return df

# Initialize rotation counter
if 'view_index' not in st.session_state:
    st.session_state.view_index = 0

# The categories we want to rotate through
views = ["OVERALL 6-HOUR", "FEMALE 6-HOUR", "MALE 6-HOUR"]
current_view = views[st.session_state.view_index % len(views)]

# Big Header
st.markdown(f"<h1 style='text-align: center; font-size: 60px;'>🏆 {current_view}</h1>", unsafe_allow_html=True)

try:
    data = get_leaderboard_data()

    # Filtering logic based on your sheet columns 'Gender' and 'Event'
    # Adjusting "6HR" filter to match your 'Event' column text
    filtered_df = data[data['Event'].str.contains("6HR", na=False)]

    if "FEMALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'F']
    elif "MALE" in current_view:
        filtered_df = filtered_df[filtered_df['Gender'] == 'M']

    # Sort by Loop Count (Highest first) and take top 15
    leaderboard = filtered_df.sort_values(by='Loop Count', ascending=False).head(15)

    # Display only the columns people care about
    st.table(leaderboard[['Bib', 'Name', 'Loop Count', 'Mileage']])

except Exception as e:
    st.error(f"Connecting to spreadsheet... please wait. (Error: {e})")

# Auto-refresh and rotate every 15 seconds
time.sleep(15)
st.session_state.view_index += 1
st.rerun()
