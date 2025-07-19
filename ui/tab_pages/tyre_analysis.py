"""
Tyre Compound Analysis Tab
Create this as: ui/tab_pages/tyre_analysis.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def render_tyre_analysis_tab(session):
    """Render tyre compound analysis tab"""
    st.header("🏎️ Tyre Compound Analysis")
    
    # Check if tyre data is available
    if not hasattr(session, 'laps') or session.laps.empty:
        st.error("❌ No lap data available for tyre analysis")
        return
    
    # Check for tyre compound data
    if 'Compound' not in session.laps.columns:
        st.warning("⚠️ Tyre compound data not available for this session")
        st.info("💡 **Tyre data is typically available in:**")
        st.markdown("- Race sessions (R)")
        st.markdown("- Some practice and qualifying sessions")
        st.markdown("- More recent F1 seasons (2018+)")
        return
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if not available_drivers:
        st.error("No drivers found in this session")
        return
    
    # Driver selection
    default_count = min(5, len(available_drivers))
    selected_drivers = st.multiselect(
        "Select drivers for tyre analysis (max 8):",
        available_drivers,
        default=available_drivers[:default_count],
        max_selections=8,
        help="Analyze tyre compound usage and performance for selected drivers"
    )
    
    if not selected_drivers:
        st.warning("Please select at least one driver for tyre analysis")
        return
    
    # Analyze tyre data
    with st.spinner("Analyzing tyre compound data..."):
        tyre_data = analyze_tyre_compounds(session, selected_drivers)
    
    if not tyre_data:
        st.error("❌ Could not analyze tyre compound data")
        return
    
    # Display analysis
    render_tyre_compound_overview(tyre_data)
    st.markdown("---")
    render_tyre_stint_analysis(session, selected_drivers, tyre_data)
    st.markdown("---")
    render_compound_performance_comparison(tyre_data)
    st.markdown("---")
    render_tyre_strategy_insights(tyre_data)

def analyze_tyre_compounds(session, selected_drivers):
    """Analyze tyre compound usage for selected drivers"""
    tyre_analysis = {}
    
    for driver in selected_drivers:
        try:
            driver_laps = session.laps[session.laps['Driver'] == driver].copy()
            
            if driver_laps.empty:
                continue
            
            # Remove invalid lap times and compounds
            valid_laps = driver_laps[
                (driver_laps['LapTime'].notna()) & 
                (driver_laps['Compound'].notna()) &
                (driver_laps['LapTime'] > pd.Timedelta(seconds=30)) &  # Remove very fast invalid times
                (driver_laps['LapTime'] < pd.Timedelta(seconds=200))   # Remove very slow invalid times
            ].copy()
            
            if valid_laps.empty:
                continue
            
            # Convert lap times to seconds
            valid_laps['LapTimeSeconds'] = valid_laps['LapTime'].dt.total_seconds()
            
            # Group by compound
            compound_analysis = {}
            
            for compound in valid_laps['Compound'].unique():
                compound_laps = valid_laps[valid_laps['Compound'] == compound]
                
                if not compound_laps.empty:
                    # Calculate statistics
                    lap_count = len(compound_laps)
                    avg_pace = compound_laps['LapTimeSeconds'].mean()
                    best_lap = compound_laps['LapTimeSeconds'].min()
                    worst_lap = compound_laps['LapTimeSeconds'].max()
                    std_dev = compound_laps['LapTimeSeconds'].std()
                    
                    # Get lap numbers for stint analysis
                    lap_numbers = compound_laps['LapNumber'].tolist()
                    lap_times = compound_laps['LapTimeSeconds'].tolist()
                    
                    compound_analysis[compound] = {
                        'lap_count': lap_count,
                        'avg_pace': avg_pace,
                        'best_lap': best_lap,
                        'worst_lap': worst_lap,
                        'consistency': std_dev,
                        'lap_numbers': lap_numbers,
                        'lap_times': lap_times,
                        'compound_color': get_compound_color(compound)
                    }
            
            if compound_analysis:
                tyre_analysis[driver] = compound_analysis
                
        except Exception as e:
            st.error(f"Error analyzing tyre data for {driver}: {e}")
            continue
    
    return tyre_analysis

def get_compound_color(compound):
    """Get color for tyre compound visualization"""
    compound_colors = {
        'SOFT': '#FF0000',      # Red
        'MEDIUM': '#FFFF00',    # Yellow  
        'HARD': '#FFFFFF',      # White
        'INTERMEDIATE': '#00FF00', # Green
        'WET': '#0000FF',       # Blue
        'HYPERSOFT': '#FF00FF', # Magenta
        'ULTRASOFT': '#800080', # Purple
        'SUPERSOFT': '#FF0000', # Red
        'SUPERSOFTHYPERSOFT': '#FF1493', # Deep pink
    }
    
    return compound_colors.get(compound.upper(), '#808080')  # Default gray

def format_lap_time_display(seconds):
    """Format lap time in seconds to MM:SS.SSS"""
    try:
        if pd.isna(seconds) or seconds <= 0:
            return "N/A"
        
        minutes = int(seconds // 60)
        seconds_remainder = seconds % 60
        return f"{minutes}:{seconds_remainder:06.3f}"
    except:
        return "N/A"

def render_tyre_compound_overview(tyre_data):
    """Render overview of tyre compound usage"""
    st.subheader("🏎️ Compound Usage Overview")
    
    # Create overview table
    overview_data = []
    
    for driver, compounds in tyre_data.items():
        total_laps = sum(data['lap_count'] for data in compounds.values())
        
        for compound, data in compounds.items():
            overview_data.append({
                'Driver': driver,
                'Compound': compound,
                'Laps Used': data['lap_count'],
                'Percentage': f"{(data['lap_count'] / total_laps * 100):.1f}%",
                'Avg Pace': format_lap_time_display(data['avg_pace']),
                'Best Lap': format_lap_time_display(data['best_lap']),
                'Consistency': f"{data['consistency']:.3f}s"
            })
    
    if overview_data:
        overview_df = pd.DataFrame(overview_data)
        st.dataframe(overview_df, use_container_width=True)
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_drivers = len(tyre_data)
        st.metric("👥 Drivers Analyzed", total_drivers)
    
    with col2:
        all_compounds = set()
        for compounds in tyre_data.values():
            all_compounds.update(compounds.keys())
        st.metric("🏎️ Compounds Used", len(all_compounds))
    
    with col3:
        total_laps_analyzed = sum(
            sum(data['lap_count'] for data in compounds.values())
            for compounds in tyre_data.values()
        )
        st.metric("🔄 Total Laps", total_laps_analyzed)

def render_tyre_stint_analysis(session, selected_drivers, tyre_data):
    """Render tyre stint visualization"""
    st.subheader("📊 Tyre Stint Visualization")
    
    fig = go.Figure()
    
    y_position = 0
    driver_positions = {}
    
    for driver in selected_drivers:
        if driver not in tyre_data:
            continue
        
        driver_positions[driver] = y_position
        compounds = tyre_data[driver]
        
        # Create stint bars for each compound
        for compound, data in compounds.items():
            lap_numbers = data['lap_numbers']
            if lap_numbers:
                # Group consecutive laps into stints
                stints = []
                current_stint = [lap_numbers[0]]
                
                for i in range(1, len(lap_numbers)):
                    if lap_numbers[i] == lap_numbers[i-1] + 1:
                        current_stint.append(lap_numbers[i])
                    else:
                        stints.append(current_stint)
                        current_stint = [lap_numbers[i]]
                
                stints.append(current_stint)
                
                # Add stint bars
                for stint in stints:
                    if stint:
                        start_lap = min(stint)
                        end_lap = max(stint)
                        duration = end_lap - start_lap + 1
                        
                        fig.add_trace(go.Bar(
                            x=[duration],
                            y=[driver],
                            base=[start_lap - 1],
                            orientation='h',
                            name=f"{driver} - {compound}",
                            marker_color=data['compound_color'],
                            hovertemplate=f'<b>{driver}</b><br>Compound: {compound}<br>Laps: {start_lap}-{end_lap} ({duration} laps)<br>Avg Pace: {format_lap_time_display(data["avg_pace"])}<extra></extra>',
                            showlegend=False
                        ))
        
        y_position += 1
    
    fig.update_layout(
        title="Tyre Stint Timeline",
        xaxis_title="Lap Number",
        yaxis_title="Driver",
        height=400,
        barmode='stack',
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_compound_performance_comparison(tyre_data):
    """Render compound performance comparison"""
    st.subheader("⚡ Compound Performance Comparison")
    
    # Collect data for comparison
    compound_performance = {}
    
    for driver, compounds in tyre_data.items():
        for compound, data in compounds.items():
            if compound not in compound_performance:
                compound_performance[compound] = {
                    'avg_paces': [],
                    'lap_counts': [],
                    'drivers': [],
                    'color': data['compound_color']
                }
            
            compound_performance[compound]['avg_paces'].append(data['avg_pace'])
            compound_performance[compound]['lap_counts'].append(data['lap_count'])
            compound_performance[compound]['drivers'].append(driver)
    
    if compound_performance:
        # Create comparison charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Average pace comparison
            fig_pace = go.Figure()
            
            compounds = list(compound_performance.keys())
            avg_paces = [sum(compound_performance[comp]['avg_paces']) / len(compound_performance[comp]['avg_paces']) 
                        for comp in compounds]
            colors = [compound_performance[comp]['color'] for comp in compounds]
            
            fig_pace.add_trace(go.Bar(
                x=compounds,
                y=avg_paces,
                marker_color=colors,
                text=[format_lap_time_display(pace) for pace in avg_paces],
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>Avg Pace: %{text}<extra></extra>'
            ))
            
            fig_pace.update_layout(
                title="Average Pace by Compound",
                xaxis_title="Compound",
                yaxis_title="Lap Time (seconds)",
                showlegend=False
            )
            
            st.plotly_chart(fig_pace, use_container_width=True)
        
        with col2:
            # Usage distribution
            fig_usage = go.Figure()
            
            total_laps = [sum(compound_performance[comp]['lap_counts']) for comp in compounds]
            
            fig_usage.add_trace(go.Pie(
                labels=compounds,
                values=total_laps,
                marker_colors=colors,
                hovertemplate='<b>%{label}</b><br>Laps: %{value}<br>Percentage: %{percent}<extra></extra>'
            ))
            
            fig_usage.update_layout(
                title="Compound Usage Distribution",
                showlegend=True
            )
            
            st.plotly_chart(fig_usage, use_container_width=True)

def render_tyre_strategy_insights(tyre_data):
    """Render strategic insights from tyre data"""
    st.subheader("🧠 Tyre Strategy Insights")
    
    insights = []
    
    # Find fastest compound
    all_compound_paces = {}
    for driver, compounds in tyre_data.items():
        for compound, data in compounds.items():
            if compound not in all_compound_paces:
                all_compound_paces[compound] = []
            all_compound_paces[compound].append(data['avg_pace'])
    
    if all_compound_paces:
        compound_avg_paces = {
            comp: sum(paces) / len(paces) 
            for comp, paces in all_compound_paces.items()
        }
        
        fastest_compound = min(compound_avg_paces.keys(), key=lambda x: compound_avg_paces[x])
        slowest_compound = max(compound_avg_paces.keys(), key=lambda x: compound_avg_paces[x])
        
        fastest_time = format_lap_time_display(compound_avg_paces[fastest_compound])
        slowest_time = format_lap_time_display(compound_avg_paces[slowest_compound])
        
        insights.append(f"🏆 **Fastest Compound**: {fastest_compound} (avg: {fastest_time})")
        insights.append(f"🐌 **Slowest Compound**: {slowest_compound} (avg: {slowest_time})")
        
        # Pace difference
        if len(compound_avg_paces) > 1:
            pace_diff = compound_avg_paces[slowest_compound] - compound_avg_paces[fastest_compound]
            insights.append(f"⏱️ **Pace Gap**: {pace_diff:.3f} seconds between fastest and slowest compounds")
    
    # Find most used compound
    compound_usage = {}
    for driver, compounds in tyre_data.items():
        for compound, data in compounds.items():
            if compound not in compound_usage:
                compound_usage[compound] = 0
            compound_usage[compound] += data['lap_count']
    
    if compound_usage:
        most_used = max(compound_usage.keys(), key=lambda x: compound_usage[x])
        least_used = min(compound_usage.keys(), key=lambda x: compound_usage[x])
        
        insights.append(f"📊 **Most Used**: {most_used} ({compound_usage[most_used]} laps total)")
        insights.append(f"📊 **Least Used**: {least_used} ({compound_usage[least_used]} laps total)")
    
    # Strategy patterns
    multi_compound_drivers = []
    for driver, compounds in tyre_data.items():
        if len(compounds) > 1:
            multi_compound_drivers.append(driver)
    
    if multi_compound_drivers:
        insights.append(f"🔄 **Multi-compound strategy**: {len(multi_compound_drivers)} drivers used multiple compounds")
    
    # Display insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Performance Insights")
        for insight in insights[:len(insights)//2 + 1]:
            st.info(insight)
    
    with col2:
        st.markdown("### 🏁 Strategy Insights")
        for insight in insights[len(insights)//2 + 1:]:
            st.info(insight)
    
    # Strategic recommendations
    st.markdown("### 💡 Strategic Analysis")
    
    if len(compound_avg_paces) > 1:
        st.markdown("**🔍 Key Takeaways:**")
        
        # Find optimal strategy
        fastest_comp = min(compound_avg_paces.keys(), key=lambda x: compound_avg_paces[x])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ **Optimal pace compound**: {fastest_comp}")
            st.info(f"📊 **Performance hierarchy**: " + " > ".join(
                sorted(compound_avg_paces.keys(), key=lambda x: compound_avg_paces[x])
            ))
        
        with col2:
            if compound_usage:
                strategy_efficiency = {
                    comp: compound_usage[comp] / compound_avg_paces[comp] 
                    for comp in compound_avg_paces.keys()
                }
                most_efficient = max(strategy_efficiency.keys(), key=lambda x: strategy_efficiency[x])
                st.success(f"🎯 **Most strategically used**: {most_efficient}")
                st.info("💭 **Strategy balance**: Consider both pace and durability for optimal race strategy")
    
    else:
        st.info("📋 Single compound session - no strategy comparison available")