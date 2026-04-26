import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - FULL VERSION
# Displays ALL divisions from your GitHub repo
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="VBS CEO Dashboard", page_icon="📊", layout="wide")

# Hide Streamlit branding
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Header
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
def get_all_stats():
    tables = {
        '🌾 Provincial': 'provincial_reports',
        '🔬 Laboratory': 'laboratory_reports',
        '📦 Packhouse': 'packhouse_reports',
        '📜 Standards': 'standards_reports',
        '📋 Administration': 'administration_reports',
        '✅ Conformity': 'conformity_assessment',
        '📝 General Activity': 'general_activity_log',
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

# ============================================
# TOP METRICS
# ============================================
stats = get_all_stats()
total_reports = sum(s['total'] for s in stats.values())
total_approved = sum(s['approved'] for s in stats.values())
total_pending = sum(s['pending'] for s in stats.values())
active_tables = len([s for s in stats.values() if s['total'] > 0])

col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 TOTAL REPORTS", f"{total_reports:,}")
col2.metric("✅ APPROVED", f"{total_approved:,}")
col3.metric("⏳ PENDING", f"{total_pending:,}", delta="Needs approval" if total_pending > 0 else None)
col4.metric("📂 ACTIVE", f"{active_tables} of {len(stats)}")

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
# ROW 1: REPORTS BY DIVISION
# ============================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Reports by Division")
    div_data = pd.DataFrame([
        {'Division': name, 'Approved': s['approved'], 'Pending': s['pending']} 
        for name, s in stats.items()
    ])
    fig = px.bar(div_data, x='Division', y=['Approved', 'Pending'], 
                 color_discrete_sequence=['#2c7a4d', '#ffc107'],
                 barmode='group', title="Approved vs Pending")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 Division Status")
    status_data = pd.DataFrame([
        {'Division': name, 'Status': '✅ Active' if s['total'] > 0 else '⚠️ Empty'} 
        for name, s in stats.items()
    ])
    fig = px.bar(status_data, x='Division', y='Status', color='Status',
                 color_discrete_map={'✅ Active': '#2c7a4d', '⚠️ Empty': '#dc3545'})
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=40), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# ROW 2: PROVINCIAL & PACKHOUSE
# ============================================
provincial = load_table('provincial_reports', 'APPROVED')
packhouse = load_table('packhouse_reports', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("🌾 Provincial Division")
    if not provincial.empty:
        pass_rate = ((provincial['inspection_result'] == 'Pass').sum() / len(provincial)) * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=pass_rate,
            title={'text': "Pass Rate (%)"},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c7a4d"},
                   'steps': [
                       {'range': [0, 60], 'color': "#f8d7da"},
                       {'range': [60, 80], 'color': "#fff3cd"},
                       {'range': [80, 100], 'color': "#d4edda"}]}))
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"📊 Total Inspections: {len(provincial)} | ⚠️ Non-Compliance: {provincial['non_compliance_cases'].sum()}")
    else:
        st.info("📭 No approved data yet")

with col2:
    st.subheader("📦 Packhouse")
    if not packhouse.empty:
        total_vol = packhouse['volume_processed_kg'].sum() if 'volume_processed_kg' in packhouse.columns else 0
        avg_waste = packhouse['waste_percent'].mean() if 'waste_percent' in packhouse.columns else 0
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Total Volume", f"{total_vol:,.0f} kg")
        with col_b:
            st.metric("Avg Waste", f"{avg_waste:.1f}%")
        
        if 'created_at' in packhouse.columns and 'volume_processed_kg' in packhouse.columns:
            packhouse['date'] = pd.to_datetime(packhouse['created_at']).dt.date
            volume_trend = packhouse.groupby('date')['volume_processed_kg'].sum().reset_index()
            fig = px.line(volume_trend, x='date', y='volume_processed_kg', title="Daily Volume Trend")
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 No approved data yet")

st.divider()

# ============================================
# ROW 3: LABORATORY & STANDARDS
# ============================================
laboratory = load_table('laboratory_reports', 'APPROVED')
standards = load_table('standards_reports', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔬 Laboratory")
    if not laboratory.empty:
        pass_rate = (laboratory['test_result'] == 'Pass').mean() * 100 if 'test_result' in laboratory.columns else 0
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=pass_rate,
            title={'text': "Test Pass Rate (%)"},
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c7a4d"}}))
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"🧪 Total Tests: {len(laboratory)}")
    else:
        st.info("📭 No approved data yet")

with col2:
    st.subheader("📜 Standards & Certification")
    if not standards.empty:
        standards_dev = standards['standards_developed'].sum() if 'standards_developed' in standards.columns else 0
        certs_issued = standards['certifications_issued'].sum() if 'certifications_issued' in standards.columns else 0
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Standards Developed", standards_dev)
        with col_b:
            st.metric("Certifications Issued", certs_issued)
        st.caption(f"📋 Total Reports: {len(standards)}")
    else:
        st.info("📭 No approved data yet")

st.divider()

# ============================================
# ROW 4: ADMIN & LEAVE
# ============================================
administration = load_table('administration_reports', 'APPROVED')
leave = load_table('leave_requests', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Administration")
    if not administration.empty:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Budget Utilization", f"{administration['budget_utilization_percent'].mean():.1f}%" if 'budget_utilization_percent' in administration.columns else "N/A")
        with col_b:
            st.metric("Revenue", f"VT {administration['revenue_collected_vt'].sum():,.0f}" if 'revenue_collected_vt' in administration.columns else "N/A")
        with col_c:
            st.metric("Reports", len(administration))
    else:
        st.info("📭 No approved data yet")

with col2:
    st.subheader("📋 Leave Requests")
    if not leave.empty:
        leave_types = leave['leave_type'].value_counts().head(3) if 'leave_type' in leave.columns else pd.Series()
        for lt, count in leave_types.items():
            st.write(f"**{lt}:** {count} requests")
        st.caption(f"📊 Total Leave Requests: {len(leave)}")
    else:
        st.info("📭 No approved leave requests yet")

st.divider()

# ============================================
# ROW 5: CONFORMITY & GENERAL ACTIVITY
# ============================================
conformity = load_table('conformity_assessment', 'APPROVED')
general = load_table('general_activity_log', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("✅ Conformity Assessment")
    if not conformity.empty:
        compliant = (conformity['assessment_result'] == 'Compliant').sum() if 'assessment_result' in conformity.columns else 0
        non_compliant = len(conformity) - compliant
        fig = go.Figure(go.Pie(
            labels=['Compliant', 'Non-Compliant'],
            values=[compliant, non_compliant],
            marker_colors=['#2c7a4d', '#dc3545'],
            hole=0.4
        ))
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"📊 Total Assessments: {len(conformity)}")
    else:
        st.info("📭 No approved data yet")

with col2:
    st.subheader("📝 General Activity")
    if not general.empty:
        activity_counts = general['activity_type'].value_counts().head(5) if 'activity_type' in general.columns else pd.Series()
        for act, count in activity_counts.items():
            st.write(f"**{act}:** {count}")
        st.caption(f"📊 Total Activities: {len(general)}")
    else:
        st.info("📭 No approved data yet")

st.divider()

# ============================================
# ROW 6: TIMESHEET
# ============================================
timesheet = load_table('timesheet', 'APPROVED')

st.subheader("⏰ Timesheet Summary")
if not timesheet.empty:
    total_hours = timesheet['hours_worked'].sum() if 'hours_worked' in timesheet.columns else 0
    total_entries = len(timesheet)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Entries", total_entries)
    col2.metric("Total Hours", f"{total_hours:.1f}")
    col3.metric("Avg Hours/Day", f"{total_hours/total_entries:.1f}" if total_entries > 0 else "0")
    col4.metric("Active Staff", timesheet['officer_name'].nunique() if 'officer_name' in timesheet.columns else 0)
    
    if 'report_date' in timesheet.columns:
        timesheet['date'] = pd.to_datetime(timesheet['report_date'])
        hours_by_day = timesheet.groupby('date')['hours_worked'].sum().reset_index()
        fig = px.bar(hours_by_day, x='date', y='hours_worked', title="Daily Hours Tracked")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📭 No approved timesheet entries yet")

st.divider()

# ============================================
# ROW 7: TOP OFFICERS
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
                 color_continuous_scale='Greens', title="Top 10 Officers by Reports")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📭 No officer data yet")

st.divider()

# ============================================
# FOOTER WITH QUICK LINKS
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

st.caption(f"© 2026 Vanuatu Bureau of Standards | Data from Supabase | Auto-refreshes every 60 seconds | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
