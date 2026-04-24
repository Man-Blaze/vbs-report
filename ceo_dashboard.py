import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - ALL DIVISIONS
# For flat screen TV in CEO office
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page config
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
st.title("📊 VBS Vanuatu Bureau of Standards")
st.caption(f"CEO Dashboard | Live Data | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# LOAD DATA
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
            stats[name] = {'total': total.count or 0, 'approved': approved.count or 0, 'pending': pending.count or 0}
        except:
            stats[name] = {'total': 0, 'approved': 0, 'pending': 0}
    return stats

stats = get_stats()
total_reports = sum(s['total'] for s in stats.values())
total_pending = sum(s['pending'] for s in stats.values())

# ============================================
# ROW 1: BIG METRICS (4 cards)
# ============================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 TOTAL REPORTS", f"{total_reports:,}")
col2.metric("✅ APPROVED", f"{sum(s['approved'] for s in stats.values()):,}")
col3.metric("⏳ PENDING", f"{total_pending:,}", delta="Need approval" if total_pending > 0 else None)
col4.metric("📂 ACTIVE", f"{len([s for s in stats.values() if s['total'] > 0])} Divisions")

# ============================================
# ROW 2: PENDING ALERT (if any)
# ============================================
if total_pending > 0:
    pending_df = pd.DataFrame([{'Division': d, 'Pending': s['pending']} for d, s in stats.items() if s['pending'] > 0])
    pending_df = pending_df.sort_values('Pending', ascending=False)
    st.error(f"⚠️ {total_pending} REPORTS PENDING MANAGER APPROVAL")
    cols = st.columns(min(len(pending_df), 4))
    for i, (idx, row) in enumerate(pending_df.iterrows()):
        if i < 4:
            with cols[i]:
                st.warning(f"**{row['Division']}**\n{row['Pending']} pending")

# ============================================
# ROW 3: TWO MAIN CHARTS
# ============================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Reports by Division")
    div_data = pd.DataFrame([{'Division': d, 'Approved': s['approved'], 'Pending': s['pending']} for d, s in stats.items()])
    fig = px.bar(div_data, x='Division', y=['Approved', 'Pending'], 
                 color_discrete_sequence=['#2c7a4d', '#ffc107'],
                 barmode='group')
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Division Status")
    status_data = [{'Division': d, 'Status': '✅ Active' if s['total'] > 0 else '⚠️ Empty'} for d, s in stats.items()]
    status_df = pd.DataFrame(status_data)
    fig = px.bar(status_df, x='Division', y='Status', color='Status',
                 color_discrete_map={'✅ Active': '#2c7a4d', '⚠️ Empty': '#dc3545'})
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# ROW 4: PROVINCIAL AND PACKHOUSE
# ============================================
provincial = load_table('provincial_reports', 'APPROVED')
packhouse = load_table('packhouse_reports', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("🌾 Provincial")
    if not provincial.empty:
        pass_rate = ((provincial['inspection_result'] == 'Pass').sum() / len(provincial)) * 100
        fig = go.Figure(go.Indicator(mode="gauge+number", value=pass_rate,
                                     title={'text': "Pass Rate (%)"},
                                     gauge={'axis': {'range': [0, 100]},
                                            'bar': {'color': "#2c7a4d"},
                                            'steps': [{'range': [0, 60], 'color': "#f8d7da"},
                                                      {'range': [60, 80], 'color': "#fff3cd"},
                                                      {'range': [80, 100], 'color': "#d4edda"}]}))
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Total Inspections: {len(provincial)} | Non-Compliance: {provincial['non_compliance_cases'].sum()}")
    else:
        st.info("No data yet")

with col2:
    st.subheader("📦 Packhouse")
    if not packhouse.empty:
        total_vol = packhouse['volume_processed_kg'].sum() if 'volume_processed_kg' in packhouse.columns else 0
        avg_waste = packhouse['waste_percent'].mean() if 'waste_percent' in packhouse.columns else 0
        fig = go.Figure()
        fig.add_trace(go.Indicator(mode="number", value=total_vol,
                                   title={'text': "Total Volume (kg)"},
                                   number={'font': {'size': 40}}))
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Avg Waste: {avg_waste:.1f}% | Rejection: {packhouse['rejection_rate_percent'].mean():.1f}%")
    else:
        st.info("No data yet")

# ============================================
# ROW 5: LABORATORY AND STANDARDS
# ============================================
laboratory = load_table('laboratory_reports', 'APPROVED')
standards = load_table('standards_reports', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔬 Laboratory")
    if not laboratory.empty:
        pass_rate = (laboratory['test_result'] == 'Pass').mean() * 100 if 'test_result' in laboratory.columns else 0
        test_count = len(laboratory)
        fig = go.Figure(go.Indicator(mode="gauge+number", value=pass_rate,
                                     title={'text': "Test Pass Rate (%)"},
                                     gauge={'axis': {'range': [0, 100]},
                                            'bar': {'color': "#2c7a4d"}}))
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Total Tests: {test_count}")
    else:
        st.info("No data yet")

with col2:
    st.subheader("📜 Standards & Certification")
    if not standards.empty:
        standards_dev = standards['standards_developed'].sum() if 'standards_developed' in standards.columns else 0
        certs_issued = standards['certifications_issued'].sum() if 'certifications_issued' in standards.columns else 0
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("📋 Standards Developed", standards_dev)
        with col_b:
            st.metric("📜 Certifications Issued", certs_issued)
        st.caption(f"Total Reports: {len(standards)}")
    else:
        st.info("No data yet")

# ============================================
# ROW 6: ADMINISTRATION AND CONFORMITY
# ============================================
administration = load_table('administration_reports', 'APPROVED')
conformity = load_table('conformity_assessment', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Administration")
    if not administration.empty:
        total_leave = administration['leave_type'].count() if 'leave_type' in administration.columns else 0
        total_overtime = administration['overtime_hours'].sum() if 'overtime_hours' in administration.columns else 0
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("📝 Leave Requests", total_leave)
        with col_b:
            st.metric("⏰ Overtime Hours", f"{total_overtime:.1f}")
        st.caption(f"Total Reports: {len(administration)}")
    else:
        st.info("No data yet")

with col2:
    st.subheader("✅ Conformity Assessment")
    if not conformity.empty:
        compliant = (conformity['assessment_result'] == 'Compliant').sum() if 'assessment_result' in conformity.columns else 0
        non_compliant = len(conformity) - compliant
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("✅ Compliant", compliant)
        with col_b:
            st.metric("❌ Non-Compliant", non_compliant)
        st.caption(f"Total Assessments: {len(conformity)}")
    else:
        st.info("No data yet")

# ============================================
# ROW 7: GENERAL ACTIVITY AND TIMESHEET
# ============================================
general = load_table('general_activity_log', 'APPROVED')
timesheet = load_table('timesheet', 'APPROVED')

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 General Activity")
    if not general.empty:
        activity_types = general['activity_type'].value_counts().head(3) if 'activity_type' in general.columns else pd.Series()
        st.write("**Top Activities:**")
        for act, count in activity_types.items():
            st.write(f"- {act}: {count}")
        st.caption(f"Total Activities: {len(general)}")
    else:
        st.info("No data yet")

with col2:
    st.subheader("⏰ Timesheet")
    if not timesheet.empty:
        total_hours = timesheet['hours_worked'].sum() if 'hours_worked' in timesheet.columns else 0
        total_entries = len(timesheet)
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("👥 Total Entries", total_entries)
        with col_b:
            st.metric("🕐 Total Hours", f"{total_hours:.1f}")
    else:
        st.info("No data yet")

# ============================================
# ROW 8: TOP OFFICERS
# ============================================
st.subheader("👥 Top Officers")

all_officers = []
for table in ['provincial_reports', 'laboratory_reports', 'packhouse_reports', 'standards_reports', 'administration_reports']:
    df = load_table(table, 'APPROVED')
    if not df.empty and 'officer_name' in df.columns:
        all_officers.extend(df['officer_name'].tolist())

if all_officers:
    officer_counts = pd.Series(all_officers).value_counts().head(5).reset_index()
    officer_counts.columns = ['Officer', 'Reports']
    fig = px.bar(officer_counts, x='Officer', y='Reports', color='Reports',
                 color_continuous_scale='Greens')
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No officer data yet")

# ============================================
# ROW 9: QUICK LINKS (Footer)
# ============================================
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("📝 [Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
with col2:
    st.markdown("✅ [Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
with col3:
    st.markdown("👥 [Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")
with col4:
    st.markdown(f"🕐 Last Updated: {datetime.now().strftime('%H:%M:%S')}")

st.caption("© 2026 Vanuatu Bureau of Standards | Auto-refreshes every 60 seconds | All 8 Divisions: Provincial, Lab, Packhouse, Standards, Admin, Conformity, General, Timesheet")
