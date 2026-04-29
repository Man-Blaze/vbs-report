import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - WITH DATABASE VIEWER LINK
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
# QUICK LINKS AT THE TOP (CEO NAVIGATION)
# ============================================
st.subheader("🔗 Quick Navigation")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown("[📝 Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
with col2:
    st.markdown("[✅ Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
with col3:
    st.markdown("[👥 Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")
with col4:
    st.markdown("[🔬 Lab Inventory](https://Man-Blaze.github.io/vbs-report/lab_inventory.html)")
with col5:
    st.markdown("[🗄️ Database Viewer](https://Man-Blaze.github.io/vbs-report/supabase_tables.html)")

st.divider()

# ============================================
# DATA FUNCTIONS
# ============================================
@st.cache_data(ttl=30)
def load_table(table_name, status_filter=None):
    try:
        query = supabase.table(table_name).select("*")
        if status_filter:
            query = query.eq("status", status_filter)
        response = query.execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_stats():
    tables = {
        '🌾 Provincial': 'provincial_reports',
        '🔬 Laboratory': 'laboratory_reports',
        '📦 Packhouse': 'packhouse_reports',
        '📜 Standards': 'standards_reports',
        '📋 Administration': 'administration_reports',
        '✅ Conformity': 'conformity_assessment',
        '📝 General': 'general_activity_log',
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
                'pending': pending.count or 0
            }
        except:
            stats[name] = {'total': 0, 'approved': 0, 'pending': 0}
    return stats

def is_late(time_in):
    if not time_in:
        return False
    try:
        parts = str(time_in).split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return hour > 8 or (hour == 8 and minute > 15)
    except:
        return False

def is_early(time_out):
    if not time_out:
        return False
    try:
        parts = str(time_out).split(':')
        hour = int(parts[0])
        return hour < 17
    except:
        return False

# ============================================
# TOP METRICS
# ============================================
stats = get_stats()
total_reports = sum(s['total'] for s in stats.values())
total_pending = sum(s['pending'] for s in stats.values())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📊 TOTAL REPORTS", f"{total_reports:,}")
col2.metric("✅ APPROVED", f"{sum(s['approved'] for s in stats.values()):,}")
col3.metric("⏳ PENDING", f"{total_pending:,}", delta="Needs approval" if total_pending > 0 else None)
col4.metric("📂 ACTIVE", f"{len([s for s in stats.values() if s['total'] > 0])} Divisions")

timesheet_df = load_table('timesheet', 'APPROVED')
if not timesheet_df.empty:
    total_hours = timesheet_df['hours_worked'].sum() if 'hours_worked' in timesheet_df.columns else 0
    col5.metric("⏰ TOTAL HOURS", f"{total_hours:.1f}")
else:
    col5.metric("⏰ TOTAL HOURS", "0")

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
# TIMESHEET SECTION (LIVE ATTENDANCE)
# ============================================
st.subheader("⏰ STAFF ATTENDANCE - TODAY'S CLOCK IN/OUT")

selected_date = st.date_input("Select Date", datetime.now().date())

timesheet = load_table('timesheet', None)
timesheet_today = timesheet[timesheet['report_date'] == str(selected_date)] if not timesheet.empty else pd.DataFrame()

staff_list = []
try:
    staff_response = supabase.table('staff_list').select("*").eq("is_active", True).execute()
    staff_list = pd.DataFrame(staff_response.data)
except:
    staff_list = pd.DataFrame()

if not timesheet_today.empty or not staff_list.empty:
    attendance_data = []
    
    if not staff_list.empty:
        for _, staff in staff_list.iterrows():
            staff_name = staff['staff_name']
            record = timesheet_today[timesheet_today['officer_name'] == staff_name]
            
            time_in = record['time_in'].iloc[0] if not record.empty and pd.notna(record['time_in'].iloc[0]) else None
            time_out = record['time_out'].iloc[0] if not record.empty and pd.notna(record['time_out'].iloc[0]) else None
            hours = record['hours_worked'].iloc[0] if not record.empty and pd.notna(record['hours_worked'].iloc[0]) else 0
            late_reason = record['late_reason'].iloc[0] if not record.empty and pd.notna(record['late_reason'].iloc[0]) else None
            early_reason = record['early_reason'].iloc[0] if not record.empty and pd.notna(record['early_reason'].iloc[0]) else None
            status = record['status'].iloc[0] if not record.empty and pd.notna(record['status'].iloc[0]) else 'PENDING'
            
            is_late_arrival = is_late(time_in) if time_in else False
            is_early_start = False
            if time_in:
                try:
                    hour = int(str(time_in).split(':')[0])
                    is_early_start = hour < 8
                except:
                    pass
            
            attendance_data.append({
                'Staff Name': staff_name,
                'Division': staff['division'],
                'Location': staff.get('location', '-'),
                'Clock In': time_in if time_in else '-',
                'Clock Out': time_out if time_out else '-',
                'Hours': hours if hours else 0,
                'Status': status,
                'Late': '⚠️ LATE' if is_late_arrival else ('🌅 EARLY START' if is_early_start else '-'),
                'Late Reason': late_reason if late_reason else '-',
                'Early Reason': early_reason if early_reason else '-'
            })
    
    df_attendance = pd.DataFrame(attendance_data)
    
    present_count = len(df_attendance[df_attendance['Clock In'] != '-'])
    late_count = len(df_attendance[df_attendance['Late'] == '⚠️ LATE'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Staff", len(df_attendance))
    col2.metric("✅ Present", present_count)
    col3.metric("⚠️ Late", late_count)
    col4.metric("⏳ Pending Approval", len(df_attendance[df_attendance['Status'] == 'PENDING']))
    
    st.dataframe(
        df_attendance[['Staff Name', 'Division', 'Location', 'Clock In', 'Clock Out', 'Hours', 'Late', 'Late Reason', 'Early Reason']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info(f"📭 No attendance records for {selected_date}")

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
    
    if 'location' in provincial.columns:
        locations = provincial['location'].value_counts().head(5).reset_index()
        locations.columns = ['Location', 'Count']
        fig = px.bar(locations, x='Location', y='Count', title="Top 5 Inspection Locations")
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
        fig = go.Figure(go.Indicator(mode="gauge+number", value=pass_rate,
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
# CONFORMITY ASSESSMENT
# ============================================
conformity = load_table('conformity_assessment', 'APPROVED')
st.subheader("✅ Conformity Assessment")
if not conformity.empty:
    compliant = (conformity['assessment_result'] == 'Compliant').sum()
    non_compliant = len(conformity) - compliant
    fig = go.Figure(go.Pie(labels=['Compliant', 'Non-Compliant'],
                           values=[compliant, non_compliant],
                           marker_colors=['#2c7a4d', '#dc3545'], hole=0.4))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No approved conformity data yet")
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
# QUICK LINKS SECTION (Bottom Navigation)
# ============================================
st.subheader("🔗 Resources & Links")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📝 Staff Tools")
    st.markdown("- [Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
    st.markdown("- [Timesheet Login](https://Man-Blaze.github.io/vbs-report/login.html)")
    st.markdown("- [Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")
    st.markdown("- [Leave Application](https://Man-Blaze.github.io/vbs-report/leave.html)")

with col2:
    st.markdown("### 👔 Management")
    st.markdown("- [Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
    st.markdown("- [Admin Report](https://Man-Blaze.github.io/vbs-report/admin_report.html)")
    st.markdown("- [Lab Inventory](https://Man-Blaze.github.io/vbs-report/lab_inventory.html)")
    st.markdown("- [Activity Tracker](https://Man-Blaze.github.io/vbs-report/tracking.html)")

with col3:
    st.markdown("### 👑 CEO Tools")
    st.markdown("- [🗄️ Database Viewer](https://Man-Blaze.github.io/vbs-report/supabase_tables.html)")
    st.markdown("- [Staff Attendance Report](https://Man-Blaze.github.io/vbs-report/ceo_attendance.html)")
    st.markdown("- [Power BI Dashboard](https://Man-Blaze.github.io/vbs-report/)")
    st.markdown("- [Central Hub](https://Man-Blaze.github.io/vbs-report/)")

st.divider()

# ============================================
# FOOTER
# ============================================
st.caption(f"© 2026 Vanuatu Bureau of Standards | Data from Supabase | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
