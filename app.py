import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import base64
import os

# 1. Page Configuration
st.set_page_config(page_title="LIVE LEADERBOARD", layout="wide")

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
    /* Moved headers down slightly more to fit perfectly on monitor screens */
    .block-container {{
        padding-top: 3.2rem !important;
        padding-bottom: 0rem !important;
    }}
    
    /* Full-screen faint background logo */
    .stApp {{
        {bg_image_css}
        background-size: contain;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Main titles cleanly positioned */
    h1 {{
        font-size: 30px !important;
        margin-top: 0px !important;
        margin-bottom: 20px !important;
        padding-top: 0px !important;
        text-align: center !important;
        font-weight: bold !important;
        color: #111111 !important;
    }}
    
    /* Standard minimalist design for scrolling lists */
    table {{
        width: 100% !important;
        font-size: 24px !important;
        background-color: transparent !important;
        border-collapse: collapse !important;
        margin-left: auto;
        margin-right: auto;
    }}
    th {{
        background-color: transparent !important;
        color: #222222 !important;
        font-size: 26px !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 8px !important;
        border-bottom: 2px solid #444444 !important;
    }}
    td {{
        padding: 8px !important;
        font-weight: 500 !important;
        text-align: center !important;
        border-bottom: 1px solid #e0e0e0 !important;
    }}
    
    /* Dedicated full-border targeting rules for Top 5 Dashboard tables */
    div[data-testid="stHorizontalBlock"] table {{
        border: 2px solid #555555 !important;
    }}
    div[data-testid="stHorizontalBlock"] th {{
        border: 1px solid #555555 !important;
        border-bottom: 2px solid #555555 !important;
        background-color: rgba(0, 0, 0, 0.02) !important;
    }}
    div[data-testid="stHorizontalBlock"] td {{
        border: 1px solid #555555 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_processed_data():
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
            return pd.DataFrame(), pd.DataFrame()

        # Race configuration
        start_time = datetime.strptime("08:00:00", "%H:%M:%S")
        
        # Calculate loops (count of raw reads) and latest read time per bib
        stats = reads.groupby('Bib').agg(
            Loop_Count=('Timestamp', 'count'),
            Last_Read=('Timestamp', 'max')
        ).reset_index()
        
        # Merge raw metrics with runner details
        df = pd.merge(roster, stats, on='Bib', how='inner')
        
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
                
        df['Overall Time'] = df
