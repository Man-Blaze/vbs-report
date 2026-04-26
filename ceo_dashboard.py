import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - MATCHES YOUR SCHEMA
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="VBS CEO Dashboard", page_icon="📊", layout="wide")

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("📊 VBS CEO Dashboard")
st.caption(f"Vanuatu Bureau of Standards | Live Data | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# DATA FUNCTIONS
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
def get_stats():
    tables = {
        '🌾 Provincial': 'provincial_reports',
        '🔬 Laboratory': 'laboratory_reports',
        '📦 Packhouse': 'packhouse_reports',
        '📜 Standards': 'standards_reports',
        '📋 Administration': 'administration_reports',
        '✅ Conformity': 'conformity_assessment',
        '📝 General': 'general_activity_log',
        '⏰ Timesheet': 'timesheet',
        '📋 Leave': 'leave_requests'
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
                'pending': pending.count or 0,
                'table': table
            }
        except:
            stats[name] = {'total': 0, 'approved': 0, 'pending': 0, 'table': table}
    return stats

stats = get_stats()
total_reports = sum(s['total'] for s in stats.values())
total_pending = sum(s['pending'] for s in stats.values())

# ============================================
# TOP METRICS
# ============================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 TOTAL REPORTS", f"{total_reports:,}")
col2.metric("✅ APPROVED", f"{sum(s['approved'] for s in stats.values()):,}")
col3.metric("⏳ PENDING", f"{total_pending:,}", delta="Needs approval" if total_pending > 0 else None)
col4.metric("📂 ACTIVE", f"{len([s for s in stats.values() if s['total'] > 0])} of {len(stats)}")

st.divider()

# ============================================
# PENDING ALERTS
# ============================================
if total_pending > 0:
    st.error(f"⚠️ {total_pending} REPORTS PENDING MANAGER APPROVAL")
    pending_list = [(name, s['pending']) for name, s in stats.items() if s['pending'] > 0]
    cols = st.columns(min(len(pending_list), 4))
    for i, (name, count) in enumerate(pending_list):
        if i < 4:
            with cols[i]:
                st.warning(f"**{name}**\n\n{count} pending")
    st.divider()

# ============================================
# REPORTS BY DIVISION (Bar Chart)
# ============================================
st.subheader("📊 Reports by Division")
div_data = pd.DataFrame([
    {'Division': name, 'Approved': s['approved'], 'Pending': s['pending']} 
    for name, s in stats.items()
])
fig = px.bar(div_data, x='Division', y=['Approved', 'Pending'], 
             color_discrete_sequence=['#2c7a4d', '#ffc107'],
             barmode='group')
fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=40))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# PROVINCIAL DIVISION
# ============================================
provincial = load_table('provincial_reports', 'APPROVED')
st.subheader("🌾 Provincial Division")
if not provincial.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        pass_rate = ((provincial['inspection_result'] == 'Pass').sum() / len(provincial)) * 100
        st.metric("Pass Rate", f"{pass_rate:.1f}%")
    with col2:
        st.metric("Total Inspections", len(provincial))
    with col3:
        st.metric("Non-Compliance", provincial['non_compliance_cases'].sum())
    
    # Top locations
    if 'location' in provincial.columns:
        locations = provincial['location'].value_counts().head(5).reset_index()
        locations.columns = ['Location', 'Count']
        fig = px.bar(locations, x='Location', y='Count', title="Top 5 Inspection Locations", color='Count')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved provincial data yet")
st.divider()

# ============================================
# PACKHOUSE
# ============================================
packhouse = load_table('packhouse_reports', 'APPROVED')
st.subheader("📦 Packhouse")
if not packhouse.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Processed", f"{packhouse['volume_processed_kg'].sum():,.0f} kg")
    with col2:
        st.metric("Avg Waste", f"{packhouse['waste_percent'].mean():.1f}%")
    with col3:
        st.metric("Avg Rejection", f"{packhouse['rejection_rate_percent'].mean():.1f}%")
else:
    st.info("No approved packhouse data yet")
st.divider()

# ============================================
# LABORATORY
# ============================================
laboratory = load_table('laboratory_reports', 'APPROVED')
st.subheader("🔬 Laboratory")
if not laboratory.empty:
    col1, col2 = st.columns(2)
    with col1:
        pass_rate = (laboratory['test_result'] == 'Pass').mean() * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=pass_rate,
            title={'text': "Test Pass Rate (%)"},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c7a4d"}}))
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        if 'test_type' in laboratory.columns:
            test_counts = laboratory['test_type'].value_counts().reset_index()
            test_counts.columns = ['Test Type', 'Count']
            fig = px.pie(test_counts, values='Count', names='Test Type', title="Tests by Type")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved laboratory data yet")
st.divider()

# ============================================
# STANDARDS
# ============================================
standards = load_table('standards_reports', 'APPROVED')
st.subheader("📜 Standards & Certification")
if not standards.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Standards Developed", standards['standards_developed'].sum())
    with col2:
        st.metric("Certifications Issued", standards['certifications_issued'].sum())
else:
    st.info("No approved standards data yet")
st.divider()

# ============================================
# LEAVE REQUESTS
# ============================================
leave = load_table('leave_requests', 'APPROVED')
st.subheader("📋 Leave Requests")
if not leave.empty:
    col1, col2 = st.columns(2)
    with col1:
        leave_counts = leave['leave_type'].value_counts().reset_index()
        leave_counts.columns = ['Leave Type', 'Count']
        fig = px.bar(leave_counts, x='Leave Type', y='Count', title="Leave Requests by Type")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.metric("Total Requests", len(leave))
        st.metric("Total Days", f"{leave['total_days'].sum():.0f}")
else:
    st.info("No approved leave requests yet")
st.divider()

# ============================================
# CONFORMITY ASSESSMENT
# ============================================
conformity = load_table('conformity_assessment', 'APPROVED')
st.subheader("✅ Conformity Assessment")
if not conformity.empty:
    compliant = (conformity['assessment_result'] == 'Compliant').sum()
    non_compliant = len(conformity) - compliant
    fig = go.Figure(go.Pie(
        labels=['Compliant', 'Non-Compliant'],
        values=[compliant, non_compliant],
        marker_colors=['#2c7a4d', '#dc3545'],
        hole=0.4
    ))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved conformity data yet")
st.divider()

# ============================================
# GENERAL ACTIVITY
# ============================================
general = load_table('general_activity_log', 'APPROVED')
st.subheader("📝 General Activity")
if not general.empty:
    if 'activity_type' in general.columns:
        activity_counts = general['activity_type'].value_counts().head(5).reset_index()
        activity_counts.columns = ['Activity', 'Count']
        fig = px.bar(activity_counts, x='Activity', y='Count', title="Top Activities")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved general activity data yet")
st.divider()

# ============================================
# TIMESHEET
# ============================================
timesheet = load_table('timesheet', 'APPROVED')
st.subheader("⏰ Timesheet")
if not timesheet.empty:
    total_hours = timesheet['hours_worked'].sum()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Hours", f"{total_hours:.1f}")
    with col2:
        st.metric("Total Entries", len(timesheet))
    with col3:
        st.metric("Avg Hours/Day", f"{total_hours/len(timesheet):.1f}" if len(timesheet) > 0 else "0")
    
    if 'report_date' in timesheet.columns:
        timesheet['date'] = pd.to_datetime(timesheet['report_date'])
        hours_by_day = timesheet.groupby('date')['hours_worked'].sum().reset_index()
        fig = px.bar(hours_by_day, x='date', y='hours_worked', title="Daily Hours")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved timesheet data yet")
st.divider()

# ============================================
# TOP OFFICERS
# ============================================
st.subheader("👥 Top Officers")
all_officers = []
for table in ['provincial_reports', 'laboratory_reports', 'packhouse_reports', 'standards_reports']:
    df = load_table(table, 'APPROVED')
    if not df.empty and 'officer_name' in df.columns:
        all_officers.extend(df['officer_name'].tolist())
if all_officers:
    officer_counts = pd.Series(all_officers).value_counts().head(10).reset_index()
    officer_counts.columns = ['Officer', 'Reports']
    fig = px.bar(officer_counts, x='Officer', y='Reports', color='Reports',
                 color_continuous_scale='Greens', title="Top 10 Officers")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No officer data yet")

st.divider()

# ============================================
# QUICK LINKS
# ============================================
st.subheader("🔗 Quick Links")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("📝 [Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
with col2:
    st.markdown("✅ [Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
with col3:
    st.markdown("👥 [Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")
with col4:
    st.markdown("🔬 [Lab Inventory](https://Man-Blaze.github.io/vbs-report/lab_inventory.html)")

st.caption(f"© 2026 Vanuatu Bureau of Standards | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
