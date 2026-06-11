import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import base64
import os

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
            # Changed RGBA alpha from 0.94 (very light) to 0.70 (noticeably darker)
            # This makes the background image slightly darker to improve table legibility.
            bg_image_css = f"background-image: linear-gradient(rgba(0, 0, 0, 0.70), rgba(0, 0, 0, 0.70)), url(data:image/png;base64,{encoded_string});"
    except Exception:
        # Changed fallback to a noticeably darker grey to maintain the theme if the logo fails to load.
        bg_image_css = "background-color: #333333;"
else:
    # Changed fallback to a noticeably darker grey if no logo is found.
    bg_image_css = "background-color: #333333;"

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
        # Changed title text color to light grey for contrast against the darker background.
        color: #f1f1f1 !important;
    }}
    
    /* Shrunk Global Transparent Table Layout to prevent vertical scrolling */
    table {{
        width: 100% !important;
        font-size: 18px !important;
        background-color: transparent !important;
        border-collapse: collapse !important;
    }}
    th {{
        background-color: transparent !important;
        # Changed header text color to white for contrast against the darker background.
        color: #ffffff !important;
        font-size: 19px !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 2px 8px !important; /* Shrunk padding vertically */
        border-bottom: 2px solid #f1f1f1 !important; /* Changed border to light grey for visibility */
    }}
    td {{
        padding: 2px 8px !important; /* Shrunk padding vertically */
        font-weight: 500 !important;
        text-align: center !important;
        # Changed cell text color to off-white for contrast against the darker background.
        color: #e0e0e0 !important;
        border-bottom: 1px solid #444444 !important; /* Changed border to a darker grey to define rows without stark contrast */
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_processed_data():
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

            # --- ADJUSTED FOR 7:00 AM START TIME ---
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
st.markdown("<h1>🏃‍♂️ RFID TEST LEADERBOARD - OVERALL</h1>", unsafe_allow_html=True)

# 5. Transparent Table Engine (With 15-Line Limit Slicing)
if master_data.empty:
    st.info("Awaiting initial RFID reads...")
else:
    # Append overall sequential placing based on the entire field
    master_data['Rank'] = range(1, len(master_data) + 1)
    
    # Isolate only required columns for displaying
    cols_to_show = ['Rank', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time', 'distance']
    display_df = master_data[cols_to_show].rename(columns={'Loop_Count': 'Loops', 'distance': 'Division'})
    
    # Slice the data to strictly show only the top 15 entries
    limited_display_df = display_df.head(15)
    
    # Render transparent grid using st.table
    st.table(limited_display_df, hide_index=True)
    
    # Simple summary row count showing total field size vs displayed count
    # Added CSS to st.caption to change text color to light grey for contrast against the darker background.
    st.markdown(f"<p style='color: #cccccc; font-size: 14px; text-align: left;'>Displaying top {len(limited_display_df)} runners out of {len(display_df)} total test entries tracked.</p>", unsafe_allow_html=True)
