import pg8000
import pandas as pd
from datetime import datetime
import os

# ============================================
# VBS CEO DASHBOARD - PYTHON VERSION
# Connect directly to Supabase PostgreSQL
# ============================================

# Supabase connection details
# Get your password from: Supabase → Project Settings → Database → Connection string
DB_HOST = "db.pdwctzueksfuspwwumdy.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "G7#r&2kL$9mP@qR"  # ← CHANGE THIS

def connect_to_db():
    """Connect to Supabase PostgreSQL"""
    try:
        conn = pg8000.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✅ Connected to Supabase database")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n📌 To get your password:")
        print("   1. Go to https://supabase.com/dashboard")
        print("   2. Click on your project")
        print("   3. Project Settings → Database")
        print("   4. Copy the connection password")
        return None

def load_all_approved_data(conn):
    """Load all approved reports from all tables"""
    print("\n📥 Loading approved reports...")
    
    tables = {
        'provincial': 'provincial_reports',
        'laboratory': 'laboratory_reports',
        'packhouse': 'packhouse_reports',
        'standards': 'standards_reports',
        'administration': 'administration_reports',
        'conformity': 'conformity_assessment',
        'general': 'general_activity_log'
    }
    
    all_data = []
    
    for name, table in tables.items():
        try:
            query = f"SELECT * FROM {table} WHERE status = 'APPROVED'"
            df = pd.read_sql(query, conn)
            df['source_table'] = name
            all_data.append(df)
            print(f"   ✅ {name}: {len(df)} records")
        except Exception as e:
            print(f"   ⚠️ {name}: table not ready yet - {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()

def generate_ceo_report(df):
    """Generate CEO dashboard report"""
    print("\n" + "=" * 60)
    print("📊 VBS CEO DASHBOARD")
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if df.empty:
        print("\n❌ No approved reports yet.")
        print("   Managers need to approve pending reports first.")
        return
    
    # Total reports
    print(f"\n📈 OVERALL STATISTICS")
    print(f"   Total approved reports: {len(df)}")
    print(f"   Divisions reporting: {df['source_table'].nunique()}")
    print(f"   Active officers: {df['officer_name'].nunique()}")
    
    # Reports by division
    print(f"\n📋 REPORTS BY DIVISION")
    division_counts = df['source_table'].value_counts()
    for div, count in division_counts.items():
        print(f"   {div}: {count}")
    
    # Provincial inspection results
    provincial = df[df['source_table'] == 'provincial']
    if not provincial.empty and 'inspection_result' in provincial.columns:
        print(f"\n🌾 PROVINCIAL DIVISION")
        pass_count = (provincial['inspection_result'] == 'Pass').sum()
        pass_rate = (pass_count / len(provincial)) * 100
        print(f"   Total inspections: {len(provincial)}")
        print(f"   Pass rate: {pass_rate:.1f}%")
        print(f"   Non-compliance cases: {provincial['non_compliance_cases'].sum()}")
    
    # Laboratory results
    laboratory = df[df['source_table'] == 'laboratory']
    if not laboratory.empty:
        print(f"\n🔬 LABORATORY")
        print(f"   Total tests: {len(laboratory)}")
        if 'test_result' in laboratory.columns:
            pass_count = (laboratory['test_result'] == 'Pass').sum()
            pass_rate = (pass_count / len(laboratory)) * 100 if len(laboratory) > 0 else 0
            print(f"   Pass rate: {pass_rate:.1f}%")
        if 'lab_tests_conducted' in laboratory.columns:
            print(f"   Total tests conducted: {laboratory['lab_tests_conducted'].sum()}")
    
    # Packhouse performance
    packhouse = df[df['source_table'] == 'packhouse']
    if not packhouse.empty:
        print(f"\n📦 PACKHOUSE")
        if 'volume_processed_kg' in packhouse.columns:
            print(f"   Volume processed: {packhouse['volume_processed_kg'].sum():,.0f} kg")
        if 'waste_percent' in packhouse.columns:
            print(f"   Average waste: {packhouse['waste_percent'].mean():.1f}%")
        if 'rejection_rate_percent' in packhouse.columns:
            print(f"   Average rejection rate: {packhouse['rejection_rate_percent'].mean():.1f}%")
    
    # Standards & Certification
    standards = df[df['source_table'] == 'standards']
    if not standards.empty:
        print(f"\n📜 STANDARDS & CERTIFICATION")
        if 'standards_developed' in standards.columns:
            print(f"   Standards developed: {standards['standards_developed'].sum()}")
        if 'certifications_issued' in standards.columns:
            print(f"   Certifications issued: {standards['certifications_issued'].sum()}")
    
    # Administration
    admin = df[df['source_table'] == 'administration']
    if not admin.empty:
        print(f"\n📋 ADMINISTRATION")
        if 'budget_utilization_percent' in admin.columns:
            print(f"   Budget utilization: {admin['budget_utilization_percent'].mean():.1f}%")
        if 'revenue_collected_vt' in admin.columns:
            print(f"   Revenue collected: VT {admin['revenue_collected_vt'].sum():,.0f}")
    
    # Conformity Assessment
    conformity = df[df['source_table'] == 'conformity']
    if not conformity.empty:
        print(f"\n✅ CONFORMITY ASSESSMENT")
        if 'assessment_result' in conformity.columns:
            compliant = (conformity['assessment_result'] == 'Compliant').sum()
            print(f"   Total assessments: {len(conformity)}")
            print(f"   Compliant: {compliant}")
            print(f"   Non-compliant: {len(conformity) - compliant}")
    
    # Staff performance
    print(f"\n👥 STAFF PERFORMANCE (Top 10 by reports)")
    if 'officer_name' in df.columns:
        staff_summary = df.groupby('officer_name').size().sort_values(ascending=False).head(10)
        for officer, count in staff_summary.items():
            print(f"   {officer}: {count} reports")
    
    print("\n" + "=" * 60)
    print("✅ End of report")

def main():
    print("=" * 60)
    print("🚀 VBS CEO Dashboard - Python Edition")
    print("=" * 60)
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        return
    
    # Load data
    df = load_all_approved_data(conn)
    conn.close()
    
    # Generate report
    generate_ceo_report(df)

if __name__ == "__main__":
    main()