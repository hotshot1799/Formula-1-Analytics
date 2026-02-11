"""
Data export tab
"""
import streamlit as st
import pandas as pd
from analysis_utils import prepare_export_data

def render_data_export_tab(session):
    """Render data export tab"""
    st.header("📋 Data Export & Download")
    
    # Session overview
    st.subheader("📊 Session Data Overview")
    
    try:
        total_laps = len(session.laps)
        total_drivers = len(session.laps['Driver'].unique())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Total Laps", total_laps)
        with col2:
            st.metric("🏎️ Drivers", total_drivers)
        with col3:
            data_points = total_laps * total_drivers
            st.metric("📈 Data Points", data_points)
    except Exception:
        st.info("Loading session data...")
    
    # Data preview and export
    lap_data = prepare_export_data(session)
    
    if lap_data is not None and not lap_data.empty:
        st.subheader("📋 Data Preview")
        st.markdown("*First 10 rows of session data:*")
        st.dataframe(lap_data.head(10), use_container_width=True)
        
        # Download options
        st.subheader("📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Complete dataset download
            csv_data = lap_data.to_csv(index=False)
            filename = f"{st.session_state.event_info.replace(' ', '_')}_complete_data.csv"
            
            st.download_button(
                label="📥 Download Complete Dataset",
                data=csv_data,
                file_name=filename,
                mime='text/csv',
                use_container_width=True,
                help="Download all lap data with proper time formatting"
            )
            
            # Show download info
            file_size = len(csv_data.encode('utf-8')) / 1024
            st.info(f"💾 **File size:** {file_size:.1f} KB")
        
        with col2:
            # Summary statistics download
            try:
                # Create driver summary
                summary_data = []
                for driver in lap_data['Driver'].unique():
                    driver_laps = lap_data[lap_data['Driver'] == driver]
                    
                    # Count valid lap times
                    valid_laps = driver_laps[driver_laps['LapTime'] != 'N/A']
                    
                    summary_data.append({
                        'Driver': driver,
                        'Total_Laps': len(driver_laps),
                        'Valid_Laps': len(valid_laps),
                        'Best_Lap': valid_laps['LapTime'].iloc[0] if not valid_laps.empty else 'N/A',
                        'Final_Position': driver_laps['Position'].iloc[-1] if 'Position' in driver_laps.columns else 'N/A'
                    })
                
                summary_df = pd.DataFrame(summary_data)
                csv_summary = summary_df.to_csv(index=False)
                summary_filename = f"{st.session_state.event_info.replace(' ', '_')}_summary.csv"
                
                st.download_button(
                    label="📊 Download Driver Summary",
                    data=csv_summary,
                    file_name=summary_filename,
                    mime='text/csv',
                    use_container_width=True,
                    help="Download summarized driver statistics"
                )
                
                # Show summary preview
                st.markdown("**Summary preview:**")
                st.dataframe(summary_df.head(5), use_container_width=True)
                
            except Exception as e:
                st.info("Summary not available")
        
        # Data information
        st.subheader("📋 Data Information")
        
        with st.expander("📊 Available Data Columns"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏎️ Basic Data:**")
                st.markdown("- **Driver**: Driver name/code")
                st.markdown("- **LapNumber**: Lap number in session")
                st.markdown("- **LapTime**: Total lap time (MM:SS.SSS)")
                st.markdown("- **Position**: Track position during lap")
            
            with col2:
                st.markdown("**⏱️ Detailed Timing:**")
                st.markdown("- **Sector1Time**: Sector 1 time")
                st.markdown("- **Sector2Time**: Sector 2 time") 
                st.markdown("- **Sector3Time**: Sector 3 time")
                st.markdown("- **SpeedI1/I2/FL/ST**: Speed measurements")
        
        # Export tips
        st.subheader("💡 Export Tips")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📊 **Data Analysis**")
            st.markdown("- Import CSV into Excel, Python, or R")
            st.markdown("- Lap times are formatted as text (MM:SS.SSS)")
            st.markdown("- Use for custom analysis and visualizations")
        
        with col2:
            st.info("🔧 **Technical Notes**")
            st.markdown("- All times converted to readable format")
            st.markdown("- Missing data shown as 'N/A'")
            st.markdown("- Position data may be incomplete for some sessions")
        
        # Usage examples
        with st.expander("💻 Usage Examples"):
            st.markdown("**📊 Excel Analysis:**")
            st.code("""
            1. Open CSV in Excel
            2. Create pivot tables by Driver
            3. Analyze lap time progressions
            4. Compare sector performance
            """, language="text")
            
            st.markdown("**🐍 Python Analysis:**")
            st.code("""
            import pandas as pd
            
            # Load data
            df = pd.read_csv('race_data.csv')
            
            # Analyze fastest laps
            fastest_by_driver = df.groupby('Driver')['LapTime'].min()
            
            # Position analysis
            final_positions = df.groupby('Driver')['Position'].last()
            """, language="python")
    
    else:
        st.error("❌ No data available for export")
        st.info("💡 **Troubleshooting:**")
        st.markdown("- Try loading a different session")
        st.markdown("- Check if the session has lap data")
        st.markdown("- Some sessions may have limited data")
        st.markdown("- Use the sidebar to select a working session")
        
        # Show what might be available
        if hasattr(session, 'laps'):
            try:
                available_columns = list(session.laps.columns)
                st.markdown("**Available columns in raw data:**")
                st.write(available_columns)
            except Exception:
                pass