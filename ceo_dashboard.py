import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD - SIMPLE WITH TOGGLE
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="VBS CEO Dashboard", page_icon="📊", layout="wide")
st.title("📊 VBS CEO Dashboard")
st.caption(f"Live Data | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# DATA LOADING
# ============================================
@st.cache_data(ttl=30)
def load_table(table_name):
    try:
        return pd.DataFrame(supabase.table(table_name).select("*").execute().data)
    except:
        return pd.DataFrame()

# Load all data
provincial = load_table('provincial_reports')
laboratory = load_table('laboratory_reports')
packhouse = load_table('packhouse_reports')
standards = load_table('standards_reports')
administration = load_table('administration_reports')
conformity = load_table('conformity_assessment')
general = load_table('general_activity_log')
timesheet = load_table('timesheet')
leave = load_table('leave_requests')
staff_list = load_table('staff_list')

# ============================================
# SIDEBAR FILTERS
# ============================================
st.sidebar.header("🔍 Filters")
show_approved = st.sidebar.checkbox("Show Approved Only", value=True)
selected_date = st.sidebar.date_input("Select Date", datetime.now().date())

# ============================================
# TOP METRICS
# ============================================
total_reports = len(provincial) + len(laboratory) + len(packhouse) + len(standards) + len(administration) + len(conformity)
total_approved = len(provincial[provincial['status'] == 'APPROVED']) if not provincial.empty else 0
total_pending = len(timesheet[timesheet['status'] == 'PENDING']) if not timesheet.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 TOTAL REPORTS", total_reports)
col2.metric("✅ APPROVED", total_approved)
col3.metric("⏳ PENDING TIMESHEETS", total_pending)
col4.metric("👥 TOTAL STAFF", len(staff_list))

st.divider()

# ============================================
# TIMESHEET - STAFF ATTENDANCE (RAW TABLE)
# ============================================
st.subheader("⏰ STAFF ATTENDANCE - RAW DATA")

if not timesheet.empty:
    timesheet_filtered = timesheet if not show_approved else timesheet[timesheet['status'] == 'APPROVED']
    timesheet_today = timesheet_filtered[timesheet_filtered['report_date'] == str(selected_date)]
    
    if not timesheet_today.empty:
        # Merge with staff list to get all staff
        all_staff = staff_list[['staff_name', 'division', 'location']] if not staff_list.empty else pd.DataFrame()
        
        if not all_staff.empty:
            merged = all_staff.merge(timesheet_today[['officer_name', 'time_in', 'time_out', 'hours_worked', 'late_reason', 'early_reason', 'status']], 
                                      left_on='staff_name', right_on='officer_name', how='left')
            merged = merged.rename(columns={'staff_name': 'Staff Name', 'division': 'Division', 'location': 'Location',
                                            'time_in': 'Clock In', 'time_out': 'Clock Out', 'hours_worked': 'Hours',
                                            'late_reason': 'Late Reason', 'early_reason': 'Early Reason'})
            merged['Clock In'] = merged['Clock In'].fillna('-')
            merged['Clock Out'] = merged['Clock Out'].fillna('-')
            merged['Hours'] = merged['Hours'].fillna(0)
            
            st.dataframe(merged[['Staff Name', 'Division', 'Location', 'Clock In', 'Clock Out', 'Hours', 'Late Reason', 'Early Reason']], 
                         use_container_width=True, hide_index=True)
            
            # Download button
            csv = merged.to_csv(index=False).encode('utf-8')
            st.download_button("📎 Download CSV", csv, f"attendance_{selected_date}.csv", "text/csv")
        else:
            st.dataframe(timesheet_today, use_container_width=True, hide_index=True)
    else:
        st.info(f"No timesheet records for {selected_date}")
else:
    st.info("No timesheet data yet")

st.divider()

# ============================================
# PROVINCIAL SECTION (Toggle)
# ============================================
st.subheader("🌾 Provincial Division")

col_view, _ = st.columns([1, 4])
with col_view:
    view_prov = st.radio("View", ["📊 Graph", "📋 Table"], key="prov_view", horizontal=True)

if not provincial.empty:
    prov_approved = provincial[provincial['status'] == 'APPROVED'] if show_approved else provincial
    
    if view_prov == "📊 Graph":
        col1, col2, col3 = st.columns(3)
        with col1:
            pass_rate = (prov_approved['inspection_result'] == 'Pass').mean() * 100 if not prov_approved.empty else 0
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        with col2:
            st.metric("Total Inspections", len(prov_approved))
        with col3:
            st.metric("Non-Compliance", prov_approved['non_compliance_cases'].sum() if not prov_approved.empty else 0)
        
        if 'location' in prov_approved.columns and not prov_approved.empty:
            locations = prov_approved['location'].value_counts().head(5).reset_index()
            locations.columns = ['Location', 'Count']
            fig = px.bar(locations, x='Location', y='Count', title="Top 5 Locations")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(prov_approved, use_container_width=True, hide_index=True)
else:
    st.info("No provincial data yet")

st.divider()

# ============================================
# LABORATORY SECTION (Toggle)
# ============================================
st.subheader("🔬 Laboratory Division")

col_view, _ = st.columns([1, 4])
with col_view:
    view_lab = st.radio("View", ["📊 Graph", "📋 Table"], key="lab_view", horizontal=True)

if not laboratory.empty:
    lab_approved = laboratory[laboratory['status'] == 'APPROVED'] if show_approved else laboratory
    
    if view_lab == "📊 Graph":
        col1, col2 = st.columns(2)
        with col1:
            pass_rate = (lab_approved['test_result'] == 'Pass').mean() * 100 if not lab_approved.empty else 0
            fig = go.Figure(go.Indicator(mode="gauge+number", value=pass_rate, title={'text': "Pass Rate (%)"}))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            if 'test_type' in lab_approved.columns and not lab_approved.empty:
                test_counts = lab_approved['test_type'].value_counts().reset_index()
                test_counts.columns = ['Test Type', 'Count']
                fig = px.pie(test_counts, values='Count', names='Test Type', title="Tests by Type")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(lab_approved, use_container_width=True, hide_index=True)
else:
    st.info("No laboratory data yet")

st.divider()

# ============================================
# PACKHOUSE SECTION (Toggle)
# ============================================
st.subheader("📦 Packhouse Division")

col_view, _ = st.columns([1, 4])
with col_view:
    view_pack = st.radio("View", ["📊 Graph", "📋 Table"], key="pack_view", horizontal=True)

if not packhouse.empty:
    pack_approved = packhouse[packhouse['status'] == 'APPROVED'] if show_approved else packhouse
    
    if view_pack == "📊 Graph":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Processed", f"{pack_approved['volume_processed_kg'].sum():,.0f} kg" if not pack_approved.empty else "0")
        with col2:
            st.metric("Avg Waste", f"{pack_approved['waste_percent'].mean():.1f}%" if not pack_approved.empty else "0")
        with col3:
            st.metric("Avg Rejection", f"{pack_approved['rejection_rate_percent'].mean():.1f}%" if not pack_approved.empty else "0")
    else:
        st.dataframe(pack_approved, use_container_width=True, hide_index=True)
else:
    st.info("No packhouse data yet")

st.divider()

# ============================================
# STANDARDS SECTION (Toggle)
# ============================================
st.subheader("📜 Standards & Certification")

col_view, _ = st.columns([1, 4])
with col_view:
    view_std = st.radio("View", ["📊 Graph", "📋 Table"], key="std_view", horizontal=True)

if not standards.empty:
    std_approved = standards[standards['status'] == 'APPROVED'] if show_approved else standards
    
    if view_std == "📊 Graph":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Standards Developed", std_approved['standards_developed'].sum() if not std_approved.empty else 0)
        with col2:
            st.metric("Certifications Issued", std_approved['certifications_issued'].sum() if not std_approved.empty else 0)
    else:
        st.dataframe(std_approved, use_container_width=True, hide_index=True)
else:
    st.info("No standards data yet")

st.divider()

# ============================================
# CONFORMITY SECTION (Toggle)
# ============================================
st.subheader("✅ Conformity Assessment")

col_view, _ = st.columns([1, 4])
with col_view:
    view_conf = st.radio("View", ["📊 Graph", "📋 Table"], key="conf_view", horizontal=True)

if not conformity.empty:
    conf_approved = conformity[conformity['status'] == 'APPROVED'] if show_approved else conformity
    
    if view_conf == "📊 Graph":
        compliant = (conf_approved['assessment_result'] == 'Compliant').sum() if not conf_approved.empty else 0
        non_compliant = len(conf_approved) - compliant
        fig = go.Figure(go.Pie(labels=['Compliant', 'Non-Compliant'], values=[compliant, non_compliant], hole=0.4))
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(conf_approved, use_container_width=True, hide_index=True)
else:
    st.info("No conformity data yet")

st.divider()

# ============================================
# GENERAL ACTIVITY (Raw Table)
# ============================================
st.subheader("📝 General Activity Log")

if not general.empty:
    gen_approved = general[general['status'] == 'APPROVED'] if show_approved else general
    st.dataframe(gen_approved[['officer_name', 'activity_type', 'activity_name', 'report_date', 'location']].head(20), 
                 use_container_width=True, hide_index=True)
    
    with st.expander("View Details with Evidence"):
        for _, activity in gen_approved.head(10).iterrows():
            st.write(f"**{activity['activity_name']}** - {activity['officer_name']}")
            st.write(f"Description: {activity['activity_description']}")
            if 'evidence_urls' in activity and activity['evidence_urls']:
                st.write(f"Evidence: {activity['evidence_urls']}")
            st.divider()
else:
    st.info("No general activity yet")

st.divider()

# ============================================
# LEAVE REQUESTS
# ============================================
st.subheader("📋 Leave Requests")

if not leave.empty:
    leave_approved = leave[leave['status'] == 'APPROVED'] if show_approved else leave
    st.dataframe(leave_approved[['officer_name', 'leave_type', 'start_date', 'end_date', 'total_days', 'reason']], 
                 use_container_width=True, hide_index=True)
else:
    st.info("No leave requests yet")

st.divider()

# ============================================
# TOP OFFICERS
# ============================================
st.subheader("👥 Top Officers")

all_officers = []
if not provincial.empty:
    all_officers.extend(provincial[provincial['status'] == 'APPROVED']['officer_name'].tolist())
if not laboratory.empty:
    all_officers.extend(laboratory[laboratory['status'] == 'APPROVED']['officer_name'].tolist())

if all_officers:
    officer_counts = pd.Series(all_officers).value_counts().head(10).reset_index()
    officer_counts.columns = ['Officer Name', 'Reports']
    st.dataframe(officer_counts, use_container_width=True, hide_index=True)
    
    fig = px.bar(officer_counts, x='Officer Name', y='Reports', color='Reports', color_continuous_scale='Greens')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No officer data yet")

st.divider()

# ============================================
# QUICK LINKS
# ============================================
st.subheader("🔗 Quick Links")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("[📝 Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
    st.markdown("[⏰ Timesheet Login](https://Man-Blaze.github.io/vbs-report/login.html)")
with col2:
    st.markdown("[✅ Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
    st.markdown("[👥 Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")
with col3:
    st.markdown("[🗄️ Database Viewer](https://Man-Blaze.github.io/vbs-report/supabase_tables.html)")
    st.markdown("[🔬 Lab Inventory](https://Man-Blaze.github.io/vbs-report/lab_inventory.html)")

st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
