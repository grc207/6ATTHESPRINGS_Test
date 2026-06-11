# 5. Core View Engine (No Pagination)
if master_data.empty:
    st.info("Awaiting initial RFID reads...")
else:
    # Append overall sequential placing
    master_data['Rank'] = range(1, len(master_data) + 1)
    
    # Isolate only required columns for displaying
    cols_to_show = ['Rank', 'Bib', 'Name', 'Loop_Count', 'Mileage', 'Overall Time', 'distance']
    display_df = master_data[cols_to_show].rename(columns={'Loop_Count': 'Loops', 'distance': 'Division'})
    
    # Render Leaderboard Grid in full - forcing height for 15 rows
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=575  # <-- This overrides the 10-row default limit
    )
    
    # Simple summary row count
    st.caption(f"Total test entries tracked: {len(display_df)}")
