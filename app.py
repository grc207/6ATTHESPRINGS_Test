import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# 1. Page Configuration & Full-Screen Background CSS
st.set_page_config(page_title="LIVE LEADERBOARD", layout="wide")

st.markdown(
    """
    <style>
    /* Faint full-screen background logo */
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.92)), url("app/static/logo.jpg");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Monitor-friendly clean table styling (No blue border fill) */
    table {
        width: 100% !important;
        font-size: 24px !important;
        background-color: transparent !important;
        border-collapse: collapse !important;
    }
    th {
        background-color: transparent !important;
        color: #111111 !important;
        font-size: 26px !important;
        font-weight: bold !important;
        border-bottom: 3px solid #333333 !important;
        text-align: left !important;
        padding: 12px !important;
    }
    td {
        padding: 14px 12px !important;
        font-weight: 500 !important;
        border-bottom: 1px solid #cccccc !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_raw_data():
    try:
        # Load Roster from "Runner Data"
        roster = conn.read(worksheet="Runner Data", ttl="0s")
        roster.columns = roster.columns.str.strip()
        
        # Clean roster columns and compile Name
        roster['Bib'] = pd.to_numeric(roster['Bib'], errors='coerce').fillna(0).astype(int)
        roster['Name'] = roster['First Name'].astype(str) + " " + roster['Last Name'].astype(str)
        
        # Load Raw Reads from "Data Input"
        reads = conn.read(worksheet="Data Input", ttl="0s")
        reads.columns = reads.columns.str.strip()
        reads['Bib'] = pd.to_numeric(reads['Bib'], errors='coerce').fillna(0).astype(int)
        
        if reads.empty or 'Bib' not in reads.columns:
            return pd.DataFrame()

        # Race configuration
        start_time = datetime.strptime("08:00:00", "%H:%M:%S")
        
        # Calculate loops (count of raw reads) and latest read time per bib
        stats = reads.groupby('Bib').agg(
            Loop_Count=('Timestamp', 'count'),
            Last_Read=('Timestamp', 'max')
        ).reset_index()
        
        # Merge raw metrics with runner details
        df = pd.merge(roster, stats, on='Bib', how='inner')
        
        # Filter for the 6HR event using your exact column name: 'distance'
        df = df[df['distance'].str.contains("6HR", na=False, case=False)].copy()
        
        # Calculate Mileage (1 read = 1 loop = 4 miles)
        df['Mileage'] = df['Loop_Count'] * 4
        
        # Calculate Elapsed Time string from 8:00 AM
        def calc_elapsed(ts_str):
            try:
                ts = datetime.strptime(str(ts_str).split()[-1], "%H:%M:%S")
                delta = ts - start_time
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except:
                return "00:00:00"
                
        df['Overall Time'] = df['Last_Read'].apply(calc_elapsed)
        
        # Strict Sorting: Loops (Highest) -> Last Read Timestamp (Earliest/Shortest Time)
        df = df.sort_values(by=['Loop_Count', 'Last_Read'], ascending=[False, True]).reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Error processing live data: {e}")
        return pd.DataFrame()

# 3. Process Live Metrics and Positions
data = get_raw_data()

if not data.empty:
    # Generate overall numeric positions (1, 2, 3...) instead of O1, O2...
    data['Position'] = [i+1 for i in range(len(data))]
    
    # Generate Class Places (M1, M2... / F1, F2...)
    data['Class Place'] = ""
    m_count, f_count = 1, 1
    for idx, row in data.iterrows():
        if str(row['gender']).upper() == 'M':
            data.at[idx, 'Class Place'] = f"M{m_count}"
            m_count += 1
        elif str(row['gender']).upper() == 'F':
            data.at[idx, 'Class Place'] = f"F{f_count}"
            f_count += 1

# 4. Cycle & Chunk State Setup
views = ["OVERALL 6-HOUR", "FEMALE 6-HOUR", "MALE 6-HOUR", "PODIUM & YOUTH"]

if 'view_index' not in st.session_state:
    st.session_state.view_index = 0
if 'row_chunk' not in st.session_state:
    st.session_state.row_chunk = 0

current_view = views[st.session_state.view_index % len(views)]
ROWS_PER_SCREEN = 12

# 5. Render Layout
st.markdown(f"<h1 style='text-align: center; font-size: 55px; margin-bottom: 20px;'>🏆 {current_view}</h1>", unsafe_allow_html=True)

if data.empty:
    st.info("Awaiting initial RFID reads...")
else:
    cols_to_show = []
    display_df = pd.DataFrame()
    
    if current_view == "OVERALL 6-HOUR":
        display_df = data.copy()
        cols_to_show = ['Position', 'Class Place', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time']
        
    elif current_view == "FEMALE 6-HOUR":
        display_df = data[data['gender'].str.upper() == 'F'].copy()
        cols_to_show = ['Class Place', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time']
        
    elif current_view == "MALE 6-HOUR":
        display_df = data[data['gender'].str.upper() == 'M'].copy()
        cols_to_show = ['Class Place', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time']
        
    elif current_view == "PODIUM & YOUTH":
        col1, col2 = st.columns(2)
        podium_cols = ['Class Place', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time']
        
        with col1:
            st.markdown("### 🏃‍♂️ Top 5 Men")
            top_m = data[data['gender'].str.upper() == 'M'].head(5).copy()
            st.table(top_m[podium_cols].rename(columns={'Loop_Count': 'Loops'}))
            
        with col2:
            st.markdown("### 🏃‍♀️ Top 5 Women")
            top_f = data[data['gender'].str.upper() == 'F'].head(5).copy()
            st.table(top_f[podium_cols].rename(columns={'Loop_Count': 'Loops'}))
            
        st.markdown("---")
        st.markdown("### 🧒 All Youth (Under 18)")
        youth_df = data[data['Age'] < 18].copy()
        # Showing full context for youth positioning
        st.table(youth_df[['Position', 'Class Place', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time']].rename(columns={'Loop_Count': 'Loops'}))

    # Chunking / Scrolling engine for long main pages
    if not display_df.empty:
        total_rows = len(display_df)
        start_row = st.session_state.row_chunk * ROWS_PER_SCREEN
        end_row = start_row + ROWS_PER_SCREEN
        
        sliced_df = display_df.iloc[start_row:end_row]
        st.table(sliced_df[cols_to_show].rename(columns={'Loop_Count': 'Loops'}))
        
        if end_row >= total_rows:
            st.session_state.row_chunk = 0
            st.session_state.view_index += 1
        else:
            st.session_state.row_chunk += 1
    else:
        # Dashboard layout logic progression
        st.session_state.row_chunk = 0
        st.session_state.view_index += 1

# 6. Refresh interval (12 seconds)
time.sleep(12)
st.rerun()
