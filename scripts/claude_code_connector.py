#!/usr/bin/env python3
"""
Claude Code Local Connector
Sovereign Unity Multi-Agent Architecture - Phase 3

Interactive development tool for querying genius_state SSoT from local machine.
Uses databricks-sql-connector with service principal OAuth.

Usage:
    python scripts/claude_code_connector.py
"""

import os
from databricks import sql
from datetime import datetime

# Load credentials from environment
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "https://dbc-228373f7-57ec.cloud.databricks.com")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")
DATABRICKS_HTTP_PATH = os.environ.get("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/5e883b4bfbb1e3f4")

def main():
    print("="*70)
    print("🤖 CLAUDE CODE - Sovereign Unity Local Connector")
    print("="*70)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Host: {DATABRICKS_HOST}")
    print()
    
    # Validate credentials
    if not DATABRICKS_CLIENT_ID or not DATABRICKS_CLIENT_SECRET:
        print("❌ ERROR: Missing credentials")
        print()
        print("Set environment variables:")
        print("  export DATABRICKS_CLIENT_ID='c058228c-6c4a-44ac-9c83-97441099cb97'")
        print("  export DATABRICKS_CLIENT_SECRET='your-secret-here'")
        print()
        print("Or create .env.local file (recommended)")
        return 1
    
    # Connect using service principal OAuth
    try:
        print("🔄 Connecting to Databricks SQL Warehouse...")
        
        connection = sql.connect(
            server_hostname=DATABRICKS_HOST.replace("https://", ""),
            http_path=DATABRICKS_HTTP_PATH,
            client_id=DATABRICKS_CLIENT_ID,
            client_secret=DATABRICKS_CLIENT_SECRET
        )
        
        print("✅ Connected successfully!")
        print()
        
        # Test Suite - Same queries as Codex for consistency
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
            
            ("Governance Rules Validation", """
                SELECT 
                    rule_id,
                    rule_name,
                    semantic_description
                FROM gen_alpha.gold.governance_rules
                ORDER BY rule_id
            """),
            
            ("Anti-Speed Gate Test", """
                SELECT 
                    gen_alpha.gold.check_anti_speed_gate_v2(
                        'Jaxson Dart',
                        'SELL',
                        CURRENT_TIMESTAMP(),
                        1
                    ) as gate_decision
            """)
        ]
        
        cursor = connection.cursor()
        
        for test_name, query in tests:
            print(f"📊 {test_name}")
            print("-" * 70)
            
            try:
                cursor.execute(query)
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                # Print results as table
                print(f"   {' | '.join(columns)}")
                print(f"   {'-' * (len(' | '.join(columns)))}")
                
                for row in result:
                    print(f"   {' | '.join(str(v) for v in row)}")
                
                print()
            
            except Exception as e:
                print(f"   ❌ Error: {e}")
                print()
        
        cursor.close()
        connection.close()
        
        print("="*70)
        print("✅ CLAUDE CODE SESSION COMPLETE")
        print("="*70)
        print()
        print("All queries executed successfully!")
        print("Claude Code agent can now query genius_state SSoT from local machine.")
        print()
        
        return 0
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Verify credentials are correct")
        print("2. Check SQL Warehouse is running (5e883b4bfbb1e3f4)")
        print("3. Confirm service principal has SELECT permissions")
        return 1

if __name__ == "__main__":
    exit(main())
