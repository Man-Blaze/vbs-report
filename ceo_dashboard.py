import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# VBS CEO DASHBOARD
# ============================================

SUPABASE_URL = "https://pdwctzueksfuspwwumdy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBkd2N0enVla3NmdXNwd3d1bWR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4MTA3NDQsImV4cCI6MjA5MjM4Njc0NH0.Xi7MH3MLuxDx1FK6BKLJi-n47SQn-gPgWxq35NuRpZY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="VBS CEO Dashboard", page_icon="📊", layout="wide")
st.title("📊 VBS CEO Dashboard")
st.caption(f"Vanuatu Bureau of Standards | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@st.cache_data(ttl=60)
def load_table_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_table_stats():
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
    
    results = {}
    for name, table in tables.items():
        try:
            total = supabase.table(table).select("id", count="exact").execute()
            approved = supabase.table(table).select("id", count="exact").eq("status", "APPROVED").execute()
            pending = supabase.table(table).select("id", count="exact").eq("status", "PENDING").execute()
            
            results[name] = {
                'total': total.count or 0,
                'approved': approved.count or 0,
                'pending': pending.count or 0
            }
        except:
            results[name] = {'total': 0, 'approved': 0, 'pending': 0}
    return results

# Display stats
stats = get_table_stats()

st.subheader("📋 Database Status")

table_data = []
for name, s in stats.items():
    status = "✅ Active" if s['total'] > 0 else "⚠️ EMPTY"
    table_data.append({
        'Table': name,
        'Total': s['total'],
        'Approved': s['approved'],
        'Pending': s['pending'],
        'Status': status
    })

df_stats = pd.DataFrame(table_data)
st.dataframe(df_stats, use_container_width=True)

empty_tables = [t for t, s in stats.items() if s['total'] == 0]
if empty_tables:
    st.error(f"⚠️ {len(empty_tables)} tables have NO data: {', '.join(empty_tables)}")

# Pending reports
total_pending = sum(s['pending'] for s in stats.values())
if total_pending > 0:
    st.warning(f"⏳ {total_pending} reports pending manager approval")
    st.markdown("👉 [Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")

# Quick links
st.subheader("🔗 Quick Links")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("[📝 Staff Forms](https://Man-Blaze.github.io/vbs-report/)")
with col2:
    st.markdown("[✅ Manager Dashboard](https://Man-Blaze.github.io/vbs-report/manager_dashboard.html)")
with col3:
    st.markdown("[👥 Team Reports](https://Man-Blaze.github.io/vbs-report/my_reports.html)")

# Active divisions chart
active = [(n, s['total']) for n, s in stats.items() if s['total'] > 0]
if active:
    st.subheader("📊 Reports by Division")
    df_active = pd.DataFrame(active, columns=['Division', 'Reports'])
    fig = px.bar(df_active, x='Division', y='Reports', title="Active Divisions")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📭 No data yet. Staff must start submitting reports.")

st.caption("© 2026 Vanuatu Bureau of Standards")
