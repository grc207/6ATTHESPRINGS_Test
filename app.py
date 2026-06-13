import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import base64
import os
import pytz  # Added to strictly lock to Eastern Time regardless of server location

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
        margin-top: 0px !important;
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

# 2. Data Connection and Lock Checking Logic
conn = st.connection("gsheets", type=GSheetsConnection)
LOCAL_BACKUP_FILE = "final_leaderboard.csv"

def is_past_lock_time():
    """Checks if the current Eastern Time is past 10:00 AM on Saturday, June 13, 2026."""
    # Force timezone calculation to US/Eastern time zone
    eastern = pytz.timezone('US/Eastern')
    now_eastern = datetime.now(eastern)
    
    # HARD TARGET: Saturday, June 13, 2026 @ 10:00:00 AM Eastern Time
    lock_target = datetime(2026, 6, 13, 10, 0, 0, tzinfo=eastern)
    
    return now_eastern >= lock_target

def get_processed_data():
    # 1. FAILSAFE CHECK: If it is past Saturday 10 AM and our permanent local backup exists, read that instantly
    if is_past_lock_time() and os.path.exists(LOCAL_BACKUP_FILE):
        try:
            return pd.read_csv(LOCAL_BACKUP_FILE)
        except Exception:
            pass # Fallback to live pull if local file reading fails inexplicably

    # 2. LIVE FETCH PATTERNS (Active until Saturday 10:00 AM)
    for attempt in range(3):
        try:
            # Load Roster
            roster = conn.read(worksheet="Runner Data", ttl="10s")
            roster.columns = roster.columns.str.strip()
            
            roster['Bib'] = pd.to_numeric(roster['Bib'], errors='coerce').fillna(0).astype(int)
            roster['Name'] = roster['First Name'].astype(str) + " " + roster['Last Name'].astype(str)
            
            # Load Data Input Sheet
            reads = conn.read(worksheet="Data Input", ttl="10s")
            
            if reads.empty:
                return pd.DataFrame()
            
            reads = reads.iloc[:, :3]
            reads.columns = ['Chip_ID', 'Timestamp', 'Bib']
            
            if pd.api.types.is_datetime64_any_dtype(reads['Timestamp']):
                reads['Timestamp'] = reads['Timestamp'].dt.strftime('%H:%M:%S')
            else:
                reads['Timestamp'] = reads['Timestamp'].astype(str).str.strip("'\" ")
            
            reads['Bib'] = pd.to_numeric(reads['Bib'], errors='coerce').fillna(0).astype(int)
            reads = reads[reads['Bib'] > 0]

            if len(reads) == 0:
                return pd.DataFrame()

            # LOCKED IN: 7:00 AM Race Start Time
            start_time = datetime.strptime("07:00:00", "%H:%M:%S")
            
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
                    delta = ts - start_time
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except Exception:
                    return "00:00:00"
                    
            df['Overall Time'] = df['Last_Read'].apply(calc_elapsed)
            
            # Sort everything globally by performance criteria
            df = df.sort_values(by=['Loop_Count', 'Last_Read'], ascending=[False, True]).reset_index(drop=True)
            
            # 3. AUTO-SAVE BACKUP AT 10:00 AM SATURDAY: Write this final dataset to local disk immediately
            if is_past_lock_time() and not os.path.exists(LOCAL_BACKUP_FILE):
                df.to_csv(LOCAL_BACKUP_FILE, index=False)
            
            return df

        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                time.sleep(1)
                continue
            else:
                st.error(f"Error processing live data: {e}")
                return pd.DataFrame()
                
    return pd.DataFrame()

# 3. Pull Data
master_data = get_processed_data()

# 4. UI Title Layout
if is_past_lock_time():
    st.markdown("<h1>🔒 RFID TEST LEADERBOARD - FINAL RESULTS (LOCKED)</h1>", unsafe_allow_html=True)
else:
    st.markdown("<h1>🏃‍♂️ RFID TEST LEADERBOARD - OVERALL (LIVE)</h1>", unsafe_allow_html=True)

# 5. Transparent Table Engine (With 15-Line Limit Slicing)
if master_data.empty:
    st.info("Awaiting initial RFID reads...")
else:
    # Append overall sequential placing based on the entire field
    master_data['Rank'] = range(1, len(master_data) + 1)
    
    # Isolate only required columns for displaying
    cols_to_show = ['Rank', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time', 'distance']
    
    if 'distance' in master_data.columns:
        display_df = master_data[cols_to_show].rename(columns={'Loop_Count': 'Loops', 'distance': 'Division'})
    else:
        cols_to_show_backup = ['Rank', 'Bib', 'Name', 'Loops', 'Mileage', 'Overall Time', 'Division']
        display_df = master_data[cols_to_show_backup]
    
    # Cap the view strictly to the top 15 rows
    limited_display_df = display_df.head(15)
    
    # Render using st.table for complete background logo transparency
    st.table(limited_display_df, hide_index=True)
    
    # Summary notification lines showing status context
    if is_past_lock_time():
        st.caption(f"Results are locked. Displaying frozen final standings of {len(display_df)} entries tracked at 10:00 AM Eastern.")
    else:
        st.caption(f"Displaying top {len(limited_display_df)} runners out of {len(display_df)} total test entries tracked.")
