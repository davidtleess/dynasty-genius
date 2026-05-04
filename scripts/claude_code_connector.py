#!/usr/bin/env python3
"""
Claude Code Local Connector - Phase 6 Enhanced
Sovereign Unity Four-Agent Architecture

Full CRUD operations via databricks-sql-connector with service principal OAuth.
Supports: CREATE, INSERT, UPDATE, DELETE, MERGE operations.

Developer Agents:
  1. Claude Code (this script) - Local development
  2. Codex - GitHub CI/CD automation
  3. Genie - Workspace native queries
  4. Gemini - Product Manager (read-only oversight)

Usage:
    python scripts/claude_code_connector.py [--mode read|write|demo]
"""

import os
import sys
from databricks import sql
from datetime import datetime

# Load credentials from environment
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "https://dbc-228373f7-57ec.cloud.databricks.com")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")
DATABRICKS_HTTP_PATH = os.environ.get("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/5e883b4bfbb1e3f4")

def read_tests(cursor):
    """Read-only validation tests (Phase 3-5)"""
    
    tests = [
        ("genius_state SSoT Overview", """
            SELECT 
                COUNT(*) as total_players,
                COUNT(CASE WHEN canonical_status = 'PRO_VETERAN' THEN 1 END) as pro_veterans,
                COUNT(CASE WHEN canonical_status = 'DRAFT_ELIGIBLE' THEN 1 END) as draft_eligible,
                COUNT(CASE WHEN canonical_status = 'EARLY_PROSPECT' THEN 1 END) as early_prospects,
                COUNT(CASE WHEN dvu_anchor IS NULL THEN 1 END) as missing_dvu,
                ROUND(AVG(dvu_anchor), 2) as avg_dvu,
                MAX(state_last_refresh) as last_refresh
            FROM gen_alpha.gold.genius_state
        """),
        
        ("DVU Anchors - Dynasty Genius Framework", """
            SELECT 
                player_name,
                position,
                dvu_anchor,
                dominator_rating_target,
                ras_target,
                class_year
            FROM gen_alpha.gold.genius_state
            WHERE player_name IN ('Ryan Williams', 'Ahmad Hardy', 'Jeremiah Smith', 'Jeremiyah Love')
            ORDER BY dvu_anchor DESC
        """),
    ]
    
    for test_name, query in tests:
        print(f"📊 {test_name}")
        print("-" * 70)
        
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            print(f"   {' | '.join(columns)}")
            print(f"   {'-' * (len(' | '.join(columns)))}")
            
            for row in result:
                print(f"   {' | '.join(str(v) for v in row)}")
            
            print()
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

def write_demo(cursor):
    """Write operation examples (Phase 6)"""
    
    print()
    print("="*70)
    print("PHASE 6: WRITE OPERATIONS DEMO")
    print("="*70)
    print()
    
    demos = [
        ("CREATE staging table", """
            CREATE TABLE IF NOT EXISTS gen_alpha.silver.claude_code_staging (
                player_name STRING,
                dvu_projection DOUBLE,
                analysis_notes STRING,
                created_timestamp TIMESTAMP,
                agent_source STRING
            )
            USING DELTA
            COMMENT 'Claude Code local development staging table'
        """),
        
        ("INSERT test data", """
            INSERT INTO gen_alpha.silver.claude_code_staging VALUES
            ('Test Player A', 125.0, 'Synthetic connector write demo fixture - class 2099', CURRENT_TIMESTAMP(), 'Claude Code'),
            ('Test Player B', 118.0, 'Synthetic connector write demo fixture - class 2099', CURRENT_TIMESTAMP(), 'Claude Code')
        """),
        
        ("SELECT inserted data", """
            SELECT 
                player_name,
                dvu_projection,
                analysis_notes,
                agent_source
            FROM gen_alpha.silver.claude_code_staging
            ORDER BY dvu_projection DESC
        """),
        
        ("UPDATE example", """
            UPDATE gen_alpha.silver.claude_code_staging
            SET dvu_projection = 120.0,
                analysis_notes = 'Updated projection based on combine results'
            WHERE player_name = 'Test Player B'
        """),
        
        ("DELETE example", """
            DELETE FROM gen_alpha.silver.claude_code_staging
            WHERE created_timestamp < CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
        """),
    ]
    
    for demo_name, query in demos:
        print(f"🔧 {demo_name}")
        print("-" * 70)
        
        try:
            cursor.execute(query)
            
            # If SELECT, show results
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                print(f"   {' | '.join(columns)}")
                print(f"   {'-' * (len(' | '.join(columns)))}")
                
                for row in result:
                    print(f"   {' | '.join(str(v) for v in row)}")
            else:
                print(f"   ✅ Executed successfully")
            
            print()
        
        except Exception as e:
            print(f"   ⚠️  {str(e)[:100]}")
            print()

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'read'
    
    print("="*70)
    print("🤖 CLAUDE CODE - Sovereign Unity Four-Agent Connector")
    print("="*70)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Host: {DATABRICKS_HOST}")
    print(f"Mode: {mode.upper()}")
    print()
    
    # Validate credentials
    if not DATABRICKS_CLIENT_ID or not DATABRICKS_CLIENT_SECRET:
        print("❌ ERROR: Missing credentials")
        print()
        print("Set environment variables:")
        print("  export DATABRICKS_CLIENT_ID='c058228c-6c4a-44ac-9c83-97441099cb97'")
        print("  export DATABRICKS_CLIENT_SECRET='your-secret-here'")
        print()
        print("Or source .env.local: export $(cat .env.local | xargs)")
        return 1
    
    # Connect using service principal OAuth
    try:
        print("🔄 Connecting to Databricks SQL Warehouse...")
        
        connection = sql.connect(
            server_hostname=DATABRICKS_HOST.replace("https://", ""),
            http_path=DATABRICKS_HTTP_PATH,
            auth_type="databricks-oauth",
            client_id=DATABRICKS_CLIENT_ID,
            client_secret=DATABRICKS_CLIENT_SECRET
        )
        
        print("✅ Connected successfully!")
        print()
        
        cursor = connection.cursor()
        
        # Execute based on mode
        if mode == 'read':
            read_tests(cursor)
        elif mode == 'write' or mode == 'demo':
            write_demo(cursor)
        else:
            print(f"❌ Unknown mode: {mode}")
            print("Usage: python claude_code_connector.py [read|write|demo]")
            return 1
        
        cursor.close()
        connection.close()
        
        print("="*70)
        print("✅ CLAUDE CODE SESSION COMPLETE")
        print("="*70)
        print()
        print("Developer Agents:")
        print("  1. Claude Code (Mac Desktop) - Local development ✅")
        print("  2. Codex (GitHub Actions) - CI/CD automation")
        print("  3. Genie (Databricks) - Workspace native")
        print("  4. Gemini (Product Manager) - Strategy oversight")
        print()
        
        return 0
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
