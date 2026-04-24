import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - WITH VISUAL CHARTS
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="VBS CEO Dashboard", page_icon="📊", layout="wide")

# Header
st.title("📊 VBS CEO Dashboard")
st.caption(f"Vanuatu Bureau of Standards | Live Data | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# LOAD DATA FUNCTIONS
# ============================================
@st.cache_data(ttl=60)
def load_table(table_name, status_filter=None):
    try:
        query = supabase.table(table_name).select("*")
        if status_filter:
            query = query.eq("status", status_filter)
        response = query.execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_all_stats():
    tables = {
        'Provincial': 'provincial_reports',
        'Laboratory': 'laboratory_reports',
        'Packhouse': 'packhouse_reports',
        'Standards': 'standards_reports',
        'Administration': 'administration_reports',
        'Conformity': 'conformity_assessment',
        'General Activity': 'general_activity_log',
        'Timesheet': 'timesheet'
    }
    
    stats = {}
    for name, table in tables.items():
        try:
            total = supabase.table(table).select("id", count="exact").execute()
            approved = supabase.table(table).select("id", count="exact").eq("status", "APPROVED").execute()
            pending = supabase.table(table).select("id", count="exact").eq("status", "PENDING").execute()
            stats[name] = {
                'total': total.count or 0,
                'approved': approved.count or 0,
                'pending': pending.count or 0
            }
        except:
            stats[name] = {'total': 0, 'approved': 0, 'pending': 0}
    return stats

# ============================================
# TOP METRICS ROW
# ============================================
stats = get_all_stats()
total_reports = sum(s['total'] for s in stats.values())
total_approved = sum(s['approved'] for s in stats.values())
total_pending = sum(s['pending'] for s in stats.values())
active_tables = len([s for s in stats.values() if s['total'] > 0])

col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 Total Reports", total_reports)
col2.metric("✅ Approved", total_approved)
col3.metric("⏳ Pending", total_pending, delta="needs approval" if total_pending > 0 else None)
col4.metric("📂 Active Divisions", active_tables)

st.divider()

# ============================================
# ROW 1: REPORTS BY DIVISION (Bar Chart)
# ============================================
st.subheader("📊 Reports by Division")

div_data = pd.DataFrame([
    {'Division': name, 'Total': s['total'], 'Approved': s['approved'], 'Pending': s['pending']}
    for name, s in stats.items()
])

fig1 = px.bar(div_data, x='Division', y=['Approved', 'Pending'], 
              title="Reports by Division (Approved vs Pending)",
              barmode='group', color_discrete_sequence=['#2c7a4d', '#ffc107'])
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ============================================
# ROW 2: PROVINCIAL DIVISION CHARTS
# ============================================
provincial = load_table('provincial_reports', 'APPROVED')

if not provincial.empty:
    st.subheader("🌾 Provincial Division")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pass rate gauge
        if 'inspection_result' in provincial.columns:
            pass_count = (provincial['inspection_result'] == 'Pass').sum()
            pass_rate = (pass_count / len(provincial)) * 100
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pass_rate,
                title={'text': "Pass Rate (%)"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "#2c7a4d"},
                       'steps': [
                           {'range': [0, 60], 'color': "#f8d7da"},
                           {'range': [60, 80], 'color': "#fff3cd"},
                           {'range': [80, 100], 'color': "#d4edda"}]}))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Non-compliance pie chart
        if 'non_compliance_cases' in provincial.columns:
            nc_total = provincial['non_compliance_cases'].sum()
            fig = go.Figure(go.Indicator(
                mode="number",
                value=nc_total,
                title={'text': "Total Non-Compliance Cases"},
                number={'font': {'size': 60, 'color': "#dc3545"}}))
            st.plotly_chart(fig, use_container_width=True)
    
    # Top locations
    if 'location' in provincial.columns:
        st.subheader("📍 Top Inspection Locations")
        locations = provincial['location'].value_counts().head(5).reset_index()
        locations.columns = ['Location', 'Inspections']
        fig = px.bar(locations, x='Location', y='Inspections', title="Top 5 Locations",
                    color='Inspections', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# ROW 3: PACKHOUSE CHARTS
# ============================================
packhouse = load_table('packhouse_reports', 'APPROVED')

if not packhouse.empty:
    st.subheader("📦 Packhouse Division")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'volume_processed_kg' in packhouse.columns:
            total_volume = packhouse['volume_processed_kg'].sum()
            fig = go.Figure(go.Indicator(
                mode="number",
                value=total_volume,
                title={'text': "Total Volume Processed (kg)"},
                number={'font': {'size': 60}}))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'waste_percent' in packhouse.columns:
            avg_waste = packhouse['waste_percent'].mean()
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_waste,
                title={'text': "Average Waste (%)"},
                gauge={'axis': {'range': [0, 20]},
                       'bar': {'color': "#dc3545" if avg_waste > 5 else "#2c7a4d"}}))
            st.plotly_chart(fig, use_container_width=True)
    
    # Volume trend over time
    if 'created_at' in packhouse.columns and 'volume_processed_kg' in packhouse.columns:
        packhouse['date'] = pd.to_datetime(packhouse['created_at']).dt.date
        volume_trend = packhouse.groupby('date')['volume_processed_kg'].sum().reset_index()
        fig = px.line(volume_trend, x='date', y='volume_processed_kg', 
                     title="Daily Processing Volume Trend",
                     markers=True, line_shape='linear')
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# ROW 4: LABORATORY CHARTS
# ============================================
laboratory = load_table('laboratory_reports', 'APPROVED')

if not laboratory.empty:
    st.subheader("🔬 Laboratory Division")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'test_result' in laboratory.columns:
            test_results = laboratory['test_result'].value_counts().reset_index()
            test_results.columns = ['Result', 'Count']
            fig = px.pie(test_results, values='Count', names='Result', 
                        title="Test Results", hole=0.4,
                        color_discrete_sequence=['#2c7a4d', '#ffc107', '#dc3545'])
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'test_type' in laboratory.columns:
            test_types = laboratory['test_type'].value_counts().reset_index()
            test_types.columns = ['Test Type', 'Count']
            fig = px.bar(test_types, x='Test Type', y='Count', 
                        title="Tests by Type", color='Count',
                        color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# ROW 5: STAFF PERFORMANCE
# ============================================
all_officers = []
for table in ['provincial_reports', 'laboratory_reports', 'packhouse_reports']:
    df = load_table(table, 'APPROVED')
    if not df.empty and 'officer_name' in df.columns:
        all_officers.extend(df['officer_name'].tolist())

if all_officers:
    st.subheader("👥 Staff Performance")
    
    officer_counts = pd.Series(all_officers).value_counts().reset_index()
    officer_counts.columns = ['Officer', 'Reports']
    officer_counts = officer_counts.head(10)
    
    fig = px.bar(officer_counts, x='Officer', y='Reports', 
                title="Top 10 Officers by Reports",
                color='Reports', color_continuous_scale='Greens')
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# ROW 6: TABLE STATUS (Heatmap style)
# ============================================
st.subheader("📋 Division Status Overview")

status_data = []
for name, s in stats.items():
    status_data.append({
        'Division': name,
        'Status': '✅ Active' if s['total'] > 0 else '⚠️ Empty',
        'Reports': s['total'],
        'Approved': s['approved'],
        'Pending': s['pending']
    })

status_df = pd.DataFrame(status_data)
st.dataframe(status_df, use_container_width=True)

# Show empty tables warning
empty = [s for s in status_data if s['Status'] == '⚠️ Empty']
if empty:
    st.warning(f"⚠️ {len(empty)} divisions have NO data: {', '.join([e['Division'] for e in empty])}")

st.divider()

# ============================================
# QUICK ACTION LINKS
# ============================================
st.subheader("🔗 Quick Actions")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("📝 [Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
with col2:
    st.markdown("✅ [Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
with col3:
    st.markdown("👥 [Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")

st.caption("© 2026 Vanuatu Bureau of Standards | Data from Supabase | Auto-refreshes every 60 seconds")
