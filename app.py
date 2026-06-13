import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="RFID TEST LEADERBOARD", layout="wide")

# --- SECURE BACKGROUND LOGO ENGINE ---
bg_image_css = ""
image_exts = ["logo.png", "logo.jpg", "logo.jpeg"]
found_image = None

for ext in image_exts:
    if os.path.exists(ext):
        found_image = ext
        break

if found_image:
    try:
        with open(found_image, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            bg_image_css = f"background-image: linear-gradient(rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.94)), url(data:image/png;base64,{encoded_string});"
    except Exception:
        bg_image_css = "background-color: #f9f9f9;"
else:
    bg_image_css = "background-color: #f9f9f9;"

st.markdown(
    f"""
    <style>
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }}
    
    .stApp {{
        {bg_image_css}
        background-size: contain;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    h1 {{
        font-size: 26px !important;
        margin-top: 20px !important;
        margin-bottom: 12px !important;
        text-align: center !important;
        font-weight: bold !important;
        color: #111111 !important;
    }}
    
    table {{
        width: 100% !important;
        font-size: 18px !important;
        background-color: transparent !important;
        border-collapse: collapse !important;
    }}
    th {{
        background-color: transparent !important;
        color: #222222 !important;
        font-size: 19px !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 2px 8px !important; 
        border-bottom: 2px solid #444444 !important;
    }}
    td {{
        padding: 2px 8px !important; 
        font-weight: 500 !important;
        text-align: center !important;
        color: #222222 !important;
        border-bottom: 1px solid #e0e0e0 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Using cache_resource ensures this function executes EXACTLY ONCE when the app starts, 
# freezing the data frame in memory forever until you modify the code or manually reboot the app server.
@st.cache_resource
def get_frozen_test_data():
    try:
        # Load Roster
        roster = conn.read(worksheet="Runner Data")
        roster.columns = roster.columns.str.strip()
        
        roster['Bib'] = pd.to_numeric(roster['Bib'], errors='coerce').fillna(0).astype(int)
        roster['Name'] = roster['First Name'].astype(str) + " " + roster['Last Name'].astype(str)
        
        # Load Data Input Sheet
        reads = conn.read(worksheet="Data Input")
        if reads.empty:
            return pd.DataFrame()
        
        reads = reads.iloc[:, :3]
        reads.columns = ['Chip_ID', 'Timestamp', 'Bib']
        
        # Clean timestamps to standard string time formatting
        if pd.api.types.is_datetime64_any_dtype(reads['Timestamp']):
            reads['Timestamp'] = reads['Timestamp'].dt.strftime('%H:%M:%S')
        else:
            reads['Timestamp'] = reads['Timestamp'].astype(str).str.strip("'\" ")
        
        reads['Bib'] = pd.to_numeric(reads['Bib'], errors='coerce').fillna(0).astype(int)
        reads = reads[reads['Bib'] > 0]
        
        # --- HARD LOCK: Filter data to ONLY include reads up to 10:00:00 AM today ---
        reads = reads[reads['Timestamp'] <= "10:00:00"]
        
        if len(reads) == 0:
            return pd.DataFrame()

        # UPDATED: Hard start time set to 7:15 AM Eastern
        start_time = datetime.strptime("07:15:00", "%H:%M:%S")
        
        stats = reads.groupby('Bib').agg(
            Loop_Count=('Timestamp', 'count'),
            Last_Read=('Timestamp', 'max')
        ).reset_index()
        
        df = pd.merge(roster, stats, on='Bib', how='inner')
        df['Mileage'] = df['Loop_Count'] * 4
        
        def calc_elapsed(ts_str):
            try:
                clean_ts = str(ts_str).strip("'\" ")
                ts_part = clean_ts.split()[-1]
                
                ts = datetime.strptime(ts_part, "%H:%M:%S")
                
                # Handling safe math if a read accidentally happened before 7:15 kickoff
                if ts < start_time:
                    return "00:00:00"
                    
                delta = ts - start_time
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except Exception:
                return "00:00:00"
                
        df['Overall Time'] = df['Last_Read'].apply(calc_elapsed)
        df = df.sort_values(by=['Loop_Count', 'Last_Read'], ascending=[False, True]).reset_index(drop=True)
        
        return df

    except Exception as e:
        st.error(f"Critical execution error tracking data: {e}")
        return pd.DataFrame()

# 3. Pull Data
master_data = get_frozen_test_data()

# 4. UI Title Layout
st.markdown("<h1>🔒 RFID TEST LEADERBOARD - FINAL RESULTS (LOCKED)</h1>", unsafe_allow_html=True)

# 5. Transparent Table Engine (With 15-Line Limit Slicing)
if master_data.empty:
    st.info("No valid test entries found between 07:15:00 and 10:00:00.")
else:
    master_data['Rank'] = range(1, len(master_data) + 1)
    cols_to_show = ['Rank', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time', 'distance']
    
    if 'distance' in master_data.columns:
        display_df = master_data[cols_to_show].rename(columns={'Loop_Count': 'Loops', 'distance': 'Division'})
    else:
        cols_to_show_backup = ['Rank', 'Bib', 'Name', 'Loops', 'Mileage', 'Overall Time', 'Division']
        display_df = master_data[cols_to_show_backup]
    
    limited_display_df = display_df.head(15)
    st.table(limited_display_df, hide_index=True)
    
    st.caption(f"Results are permanently locked. Displaying frozen final standings of {len(display_df)} entries tracked between 7:15 AM and 10:00 AM Eastern.")
