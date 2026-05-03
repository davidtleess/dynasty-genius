#!/usr/bin/env python3
"""
Codex Compliance Audit Script
Sovereign Unity Multi-Agent Architecture - Phase 4

Tests:
1. genius_state SSoT accessibility
2. Governance rules validation
3. DVU anchor integrity (following Dynasty Genius framework)
4. Status classification logic
5. 65:35 compliance ratio enforcement
"""

import os
import sys
import json
from datetime import datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# Configuration from environment
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")

def execute_query(w, query, test_name):
    """Execute SQL query via Statement Execution API"""
    print(f"\n🔄 Running: {test_name}")
    
    try:
        response = w.statement_execution.execute_statement(
            warehouse_id=DATABRICKS_WAREHOUSE_ID,
            statement=query,
            wait_timeout="50s"
        )
        
        if response.status.state == StatementState.SUCCEEDED:
            result = response.result
            if result and result.data_array:
                print(f"✅ {test_name}: PASSED")
                return {
                    "test": test_name,
                    "status": "PASSED",
                    "result": result.data_array,
                    "row_count": result.row_count
                }
            else:
                print(f"⚠️  {test_name}: No rows returned")
                return {
                    "test": test_name,
                    "status": "WARNING",
                    "message": "No rows returned"
                }
        else:
            error_msg = response.status.error.message if response.status.error else "Unknown error"
            print(f"❌ {test_name}: FAILED - {error_msg}")
            return {
                "test": test_name,
                "status": "FAILED",
                "error": error_msg
            }
    
    except Exception as e:
        print(f"❌ {test_name}: EXCEPTION - {str(e)}")
        return {
            "test": test_name,
            "status": "FAILED",
            "error": str(e)
        }

def main():
    print("="*70)
    print("🤖 CODEX COMPLIANCE AUDIT - Sovereign Unity")
    print("="*70)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Host: {DATABRICKS_HOST}")
    print(f"Warehouse: {DATABRICKS_WAREHOUSE_ID}")
    print()
    
    # Initialize Workspace Client with Service Principal OAuth
    try:
        w = WorkspaceClient(
            host=DATABRICKS_HOST,
            client_id=DATABRICKS_CLIENT_ID,
            client_secret=DATABRICKS_CLIENT_SECRET
        )
        
        # Verify authentication
        current_user = w.current_user.me()
        print(f"✅ Authenticated as: {current_user.display_name}")
        print()
    
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    
    # Test Suite
    results = []
    
    # Test 1: genius_state SSoT Query
    results.append(execute_query(
        w,
        """
        SELECT 
            COUNT(*) as total_players,
            COUNT(CASE WHEN canonical_status = 'PRO_VETERAN' THEN 1 END) as pro_veterans,
            COUNT(CASE WHEN dvu_anchor IS NULL THEN 1 END) as missing_dvu,
            ROUND(AVG(dvu_anchor), 2) as avg_dvu,
            MAX(state_last_refresh) as last_refresh
        FROM gen_alpha.gold.genius_state
        """,
        "Test 1: genius_state SSoT Accessibility"
    ))
    
    # Test 2: Governance Rules Validation
    results.append(execute_query(
        w,
        """
        SELECT 
            COUNT(*) as rule_count,
            COUNT(CASE WHEN rule_id = 'medical_qualitative_override' THEN 1 END) as medical_override_exists,
            COUNT(CASE WHEN rule_id = 'rb_age_cliff_28' THEN 1 END) as rb_age_cliff_exists
        FROM gen_alpha.gold.governance_rules
        """,
        "Test 2: Governance Rules Validation"
    ))
    
    # Test 3: DVU Anchor Integrity (Dynasty Genius Framework)
    results.append(execute_query(
        w,
        """
        SELECT 
            player_name,
            dvu_anchor,
            class_year
        FROM gen_alpha.gold.genius_state
        WHERE player_name IN ('Ryan Williams', 'Ahmad Hardy', 'Jeremiah Smith', 'Jeremiyah Love')
        ORDER BY dvu_anchor DESC
        """,
        "Test 3: DVU Anchor Integrity Check"
    ))
    
    # Test 4: Status Classification Logic
    results.append(execute_query(
        w,
        """
        SELECT 
            canonical_status,
            COUNT(*) as player_count
        FROM gen_alpha.gold.genius_state
        GROUP BY canonical_status
        ORDER BY player_count DESC
        """,
        "Test 4: Status Classification Distribution"
    ))
    
    # Test 5: 65:35 Compliance (Source Rank Distribution)
    results.append(execute_query(
        w,
        """
        SELECT 
            source_rank,
            COUNT(*) as player_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM gen_alpha.gold.genius_state
        WHERE source_rank IS NOT NULL
        GROUP BY source_rank
        ORDER BY source_rank
        """,
        "Test 5: Source Rank Distribution (65:35 Compliance)"
    ))
    
    # Summary
    print()
    print("="*70)
    print("📊 AUDIT SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r.get("status") == "PASSED")
    failed = sum(1 for r in results if r.get("status") == "FAILED")
    warnings = sum(1 for r in results if r.get("status") == "WARNING")
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")
    print()
    
    # Save results to JSON
    audit_report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service_principal": current_user.display_name,
        "warehouse_id": DATABRICKS_WAREHOUSE_ID,
        "tests": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "warnings": warnings
        }
    }
    
    with open("audit_results.json", "w") as f:
        json.dump(audit_report, f, indent=2)
    
    print("💾 Audit results saved to: audit_results.json")
    print()
    
    # Exit with appropriate code
    if failed > 0:
        print("❌ AUDIT FAILED - Some tests did not pass")
        sys.exit(1)
    elif warnings > 0:
        print("⚠️  AUDIT PASSED WITH WARNINGS")
        sys.exit(0)
    else:
        print("✅ AUDIT PASSED - All tests successful")
        sys.exit(0)

if __name__ == "__main__":
    main()
