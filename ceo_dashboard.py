import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - TOGGLE VIEW
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
# VIEW TOGGLE FUNCTION
# ============================================
def view_selector(section_key, label):
    col1, col2 = st.columns([1, 4])
    with col1:
        return st.radio(label, ["📊 Graph", "📋 Table"], key=section_key, horizontal=True)
    return "📊 Graph"

# ============================================
# QUICK LINKS
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
# REPORTS BY DIVISION (Bar Chart with Table Toggle)
# ============================================
st.subheader("📊 Reports by Division")
view = view_selector("reports_by_div", "View")

div_data = pd.DataFrame([
    {'Division': name, 'Approved': s['approved'], 'Pending': s['pending']} 
    for name, s in stats.items()
])

if view == "📊 Graph":
    fig = px.bar(div_data, x='Division', y=['Approved', 'Pending'], 
                 color_discrete_sequence=['#2c7a4d', '#ffc107'],
                 barmode='group')
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.dataframe(div_data, use_container_width=True, hide_index=True)

st.divider()

# ============================================
# TREND LINE GRAPH with Table Toggle
# ============================================
st.subheader("📈 Reports Trend (Last 30 Days)")
view_trend = view_selector("trend_view", "View")

all_tables = ['provincial_reports', 'laboratory_reports', 'packhouse_reports', 
              'standards_reports', 'administration_reports', 'conformity_assessment']
trend_data = []
for table in all_tables:
    df = load_table(table, 'APPROVED')
    if not df.empty and 'created_at' in df.columns:
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        daily = df.groupby('date').size().reset_index()
        daily['source'] = table.replace('_reports', '').capitalize()
        trend_data.append(daily)

if trend_data:
    trend_df = pd.concat(trend_data, ignore_index=True)
    if view_trend == "📊 Graph":
        fig = px.line(trend_df, x='date', y=0, color='source', 
                      title="Daily Reports by Division",
                      markers=True, line_shape='linear')
        fig.update_layout(height=450, xaxis_title="Date", yaxis_title="Number of Reports")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(trend_df, use_container_width=True, hide_index=True)
else:
    st.info("No trend data available yet")

st.divider()

# ============================================
# TIMESHEET SECTION (COMPLETE ATTENDANCE TABLE)
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

general_activity = load_table('general_activity_log', 'APPROVED')

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
            clock_method = record['clock_method'].iloc[0] if not record.empty and pd.notna(record['clock_method'].iloc[0]) else 'focal_point'
            
            is_late_arrival = is_late(time_in) if time_in else False
            is_early_start = False
            if time_in:
                try:
                    hour = int(str(time_in).split(':')[0])
                    is_early_start = hour < 8
                except:
                    pass
            
            evidence_links = []
            if not general_activity.empty:
                staff_activities = general_activity[general_activity['officer_name'] == staff_name]
                for _, act in staff_activities.iterrows():
                    if 'evidence_urls' in act and act['evidence_urls']:
                        urls = act['evidence_urls']
                        if isinstance(urls, str):
                            try:
                                import json
                                urls = json.loads(urls)
                            except:
                                urls = [urls]
                        if isinstance(urls, list):
                            for url in urls:
                                if url and isinstance(url, str):
                                    evidence_links.append(f'<a href="{url}" target="_blank">📎 View</a>')
            
            attendance_data.append({
                'Staff Name': staff_name,
                'Division': staff['division'],
                'Location': staff.get('location', '-'),
                'Clock In': time_in if time_in else '-',
                'Clock Out': time_out if time_out else '-',
                'Hours': hours if hours else 0,
                'Status': status,
                'Method': '👔 Focal Point' if clock_method == 'focal_point' else '🔓 Self Clock',
                'Late': '⚠️ LATE' if is_late_arrival else ('🌅 EARLY START' if is_early_start else '-'),
                'Late Reason': late_reason if late_reason else '-',
                'Early Reason': early_reason if early_reason else '-',
                'Evidence': ', '.join(evidence_links) if evidence_links else '-'
            })
    
    df_attendance = pd.DataFrame(attendance_data)
    
    present_count = len(df_attendance[df_attendance['Clock In'] != '-'])
    late_count = len(df_attendance[df_attendance['Late'] == '⚠️ LATE'])
    self_clock_count = len(df_attendance[df_attendance['Method'] == '🔓 Self Clock'])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Total Staff", len(df_attendance))
    col2.metric("✅ Present", present_count)
    col3.metric("⚠️ Late", late_count)
    col4.metric("🔓 Self Clock", self_clock_count)
    col5.metric("⏳ Pending", len(df_attendance[df_attendance['Status'] == 'PENDING']))
    
    # Always show table for attendance (this is the raw data CEO wants)
    st.markdown("### 📋 Staff Attendance Details")
    st.dataframe(df_attendance, use_container_width=True, hide_index=True)
    
    csv = df_attendance.to_csv(index=False).encode('utf-8')
    st.download_button("📎 Download Attendance CSV", csv, f"attendance_{selected_date}.csv", "text/csv")
    
else:
    st.info(f"📭 No attendance records for {selected_date}")

st.divider()

# ============================================
# PROVINCIAL DIVISION with Toggle
# ============================================
provincial = load_table('provincial_reports', 'APPROVED')
st.subheader("🌾 Provincial Division")
view_prov = view_selector("provincial_view", "View")

if not provincial.empty:
    if view_prov == "📊 Graph":
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
        st.dataframe(provincial, use_container_width=True, hide_index=True)
else:
    st.info("No approved provincial data yet")
st.divider()

# ============================================
# PACKHOUSE with Toggle
# ============================================
packhouse = load_table('packhouse_reports', 'APPROVED')
st.subheader("📦 Packhouse")
view_pack = view_selector("packhouse_view", "View")

if not packhouse.empty:
    if view_pack == "📊 Graph":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Processed", f"{packhouse['volume_processed_kg'].sum():,.0f} kg")
        with col2:
            st.metric("Avg Waste", f"{packhouse['waste_percent'].mean():.1f}%")
        with col3:
            st.metric("Avg Rejection", f"{packhouse['rejection_rate_percent'].mean():.1f}%")
    else:
        st.dataframe(packhouse, use_container_width=True, hide_index=True)
else:
    st.info("No approved packhouse data yet")
st.divider()

# ============================================
# LABORATORY with Toggle
# ============================================
laboratory = load_table('laboratory_reports', 'APPROVED')
st.subheader("🔬 Laboratory")
view_lab = view_selector("laboratory_view", "View")

if not laboratory.empty:
    if view_lab == "📊 Graph":
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
        st.dataframe(laboratory, use_container_width=True, hide_index=True)
else:
    st.info("No approved laboratory data yet")
st.divider()

# ============================================
# STANDARDS with Toggle
# ============================================
standards = load_table('standards_reports', 'APPROVED')
st.subheader("📜 Standards & Certification")
view_std = view_selector("standards_view", "View")

if not standards.empty:
    if view_std == "📊 Graph":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Standards Developed", standards['standards_developed'].sum())
        with col2:
            st.metric("Certifications Issued", standards['certifications_issued'].sum())
    else:
        st.dataframe(standards, use_container_width=True, hide_index=True)
else:
    st.info("No approved standards data yet")
st.divider()

# ============================================
# CONFORMITY ASSESSMENT with Toggle
# ============================================
conformity = load_table('conformity_assessment', 'APPROVED')
st.subheader("✅ Conformity Assessment")
view_conf = view_selector("conformity_view", "View")

if not conformity.empty:
    if view_conf == "📊 Graph":
        compliant = (conformity['assessment_result'] == 'Compliant').sum()
        non_compliant = len(conformity) - compliant
        fig = go.Figure(go.Pie(labels=['Compliant', 'Non-Compliant'],
                               values=[compliant, non_compliant],
                               marker_colors=['#2c7a4d', '#dc3545'], hole=0.4))
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(conformity, use_container_width=True, hide_index=True)
else:
    st.info("No approved conformity data yet")
st.divider()

# ============================================
# TOP OFFICERS (TABLE Only - CEO wants names)
# ============================================
st.subheader("👥 Staff Activity Summary")

all_officers = []
for table in ['provincial_reports', 'laboratory_reports', 'packhouse_reports', 'standards_reports']:
    df = load_table(table, 'APPROVED')
    if not df.empty and 'officer_name' in df.columns:
        all_officers.extend(df['officer_name'].tolist())

if not timesheet.empty and 'officer_name' in timesheet.columns:
    all_officers.extend(timesheet[timesheet['status'] == 'APPROVED']['officer_name'].tolist())

if all_officers:
    officer_counts = pd.Series(all_officers).value_counts().reset_index()
    officer_counts.columns = ['Officer Name', 'Total Reports']
    st.dataframe(officer_counts, use_container_width=True, hide_index=True)
    
    # Simple bar chart for top 10
    top10 = officer_counts.head(10)
    fig = px.bar(top10, x='Officer Name', y='Total Reports', 
                 color='Total Reports', color_continuous_scale='Greens',
                 title="Top 10 Officers by Activity")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No officer data yet")

st.divider()

# ============================================
# GENERAL ACTIVITY WITH EVIDENCE
# ============================================
st.subheader("📎 General Activity Reports with Evidence")

general = load_table('general_activity_log', 'APPROVED')
if not general.empty:
    # Show as table first, then expandable details
    st.dataframe(general[['officer_name', 'activity_type', 'activity_name', 'report_date']].head(20), 
                 use_container_width=True, hide_index=True)
    
    with st.expander("View Detailed Activity with Evidence"):
        for _, activity in general.head(20).iterrows():
            st.write(f"**{activity['activity_name']}** - {activity['officer_name']} ({activity['report_date']})")
            st.write(f"Type: {activity['activity_type']}")
            st.write(f"Description: {activity['activity_description']}")
            if 'evidence_urls' in activity and activity['evidence_urls']:
                urls = activity['evidence_urls']
                if isinstance(urls, str):
                    try:
                        import json
                        urls = json.loads(urls)
                    except:
                        urls = [urls]
                if isinstance(urls, list):
                    for url in urls:
                        if url and isinstance(url, str):
                            st.markdown(f'<a href="{url}" target="_blank">📎 View Evidence</a>', unsafe_allow_html=True)
            st.divider()
else:
    st.info("No general activity reports yet")

st.divider()

# ============================================
# QUICK LINKS SECTION
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
    st.markdown("- [Central Hub](https://Man-Blaze.github.io/vbs-report/)")

st.divider()

st.caption(f"© 2026 Vanuatu Bureau of Standards | Data from Supabase | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
