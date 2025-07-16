"""
Sector analysis tab
"""
import streamlit as st
from chart_creators import create_sector_analysis_chart
from analysis_utils import get_fastest_sector_times

def render_sector_analysis_tab(session):
    """Render sector analysis tab"""
    st.header("⏱️ Sector Time Analysis")
    
    with st.spinner("Analyzing sector times..."):
        result = create_sector_analysis_chart(session)
    
    if result[0]:
        fig, df = result
        st.plotly_chart(fig, use_container_width=True)
        
        # Sector champions
        fastest_s1, fastest_s2, fastest_s3 = get_fastest_sector_times(df)
        
        if fastest_s1 is not None:
            st.subheader("🏆 Sector Champions")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🟥 Fastest Sector 1", fastest_s1['Driver'], f"{fastest_s1['Sector1']:.3f}s")
            with col2:
                st.metric("🟨 Fastest Sector 2", fastest_s2['Driver'], f"{fastest_s2['Sector2']:.3f}s")
            with col3:
                st.metric("🟩 Fastest Sector 3", fastest_s3['Driver'], f"{fastest_s3['Sector3']:.3f}s")
            
            # Add overall fastest insight
            try:
                best_overall = df.loc[df['Total'].idxmin(), 'Driver']
                st.success(f"🏁 **Overall Fastest**: {best_overall} had the best combined sector times")
            except:
                pass
        
        st.subheader("📊 Detailed Sector Times")
        st.dataframe(df.round(3), use_container_width=True)
        
        # Sector insights
        if not df.empty:
            st.subheader("💡 Sector Insights")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("🔍 **Sector Analysis**")
                st.markdown("- **Sector 1**: Often reflects qualifying pace")
                st.markdown("- **Sector 2**: Usually the technical section") 
                st.markdown("- **Sector 3**: Final sector to the finish line")
            
            with col2:
                st.info("📊 **Performance Tips**")
                st.markdown("- Compare drivers' strengths across sectors")
                st.markdown("- Look for consistency vs peak performance")
                st.markdown("- Identify track-specific advantages")
    else:
        st.warning("⚠️ No sector time data available for this session")
        st.info("💡 **Sector data is typically available in:**")
        st.markdown("- Qualifying sessions (Q)")
        st.markdown("- Practice sessions (FP1, FP2, FP3)")
        st.markdown("- Some race sessions (R)")
        st.markdown("- Try a different session type for sector analysis")