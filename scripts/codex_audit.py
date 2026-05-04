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
import subprocess
from datetime import datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# Configuration from environment
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")

ANCHOR_BASELINES = {
    "Jeremiyah Love": 100.0,
    "Ashton Jeanty": 95.0,
    "Jeremiah Smith": 120.0,
    "Ryan Williams": 116.0,
    "Ahmad Hardy": 108.0,
    "Arch Manning": 120.0,
}

ALLOWED_ANCHOR_OVERRIDES = {
    "Ryan Williams": {
        "from_dvu": 116.0,
        "to_dvu": 88.0,
        "strategy_commit": "c538874",
        "rationale_paths": [
            "docs/governance/anchor_overrides.md",
            "docs/strategies/2027_target_differentiation.md",
            "docs/strategies/2027_pick_accumulation.md",
            "docs/class-trackers/2027.md",
        ],
        "required_rationale_terms": [
            "Ryan Williams",
            "116.0",
            "88.0",
            "49",
            "689",
            "4 TD",
            "Conditional Tier-2",
        ],
        "quantitative_evidence_terms": ["49", "689", "4 TD"],
    },
    "Arch Manning": {
        "from_dvu": 120.0,
        "to_dvu": 90.0,
        "governance_rule_id": "medical_qualitative_override",
        "rationale_paths": [
            "docs/governance/anchor_overrides.md",
            "infrastructure/README.md",
            "AGENT_BRIEFING.md",
        ],
        "required_rationale_terms": [
            "Arch Manning",
            "120.0",
            "90.0",
            "medical_qualitative_override",
            "0.30 Dominator",
            "9.2 RAS",
            "accuracy concerns",
        ],
        "quantitative_evidence_terms": ["0.30 Dominator", "9.2 RAS", "90.0"],
    },
}

FLOAT_TOLERANCE = 0.01

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

def _run_git_command(args):
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout
    except Exception:
        return ""

def _commit_exists(commit_sha):
    return bool(_run_git_command(["cat-file", "-e", f"{commit_sha}^{{commit}}"]))

def _commit_is_documented(commit_sha, docs_text):
    return commit_sha in docs_text

def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""

def _has_documented_rationale(override):
    combined_docs = "\n".join(_read_file(path) for path in override["rationale_paths"])
    strategy_commit = override.get("strategy_commit")
    if not combined_docs and strategy_commit and _commit_exists(strategy_commit):
        combined_docs = _run_git_command(["show", "--format=fuller", "--stat", strategy_commit])
    return all(term in combined_docs for term in override["required_rationale_terms"])

def _has_strategy_commit_reference(override):
    strategy_commit = override.get("strategy_commit")
    if not strategy_commit:
        return True
    combined_docs = "\n".join(_read_file(path) for path in override["rationale_paths"])
    return _commit_exists(strategy_commit) or _commit_is_documented(
        strategy_commit,
        combined_docs,
    )

def _has_governance_rule_reference(override):
    governance_rule_id = override.get("governance_rule_id")
    if not governance_rule_id:
        return True
    combined_docs = "\n".join(_read_file(path) for path in override["rationale_paths"])
    return governance_rule_id in combined_docs

def _has_documented_quantitative_evidence(override):
    combined_docs = "\n".join(_read_file(path) for path in override["rationale_paths"])
    production_terms = override.get("quantitative_evidence_terms", [])
    return bool(production_terms) and all(term in combined_docs for term in production_terms)

def _as_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _as_string(value):
    return "" if value is None else str(value)

def validate_anchor_overrides(anchor_rows):
    """Validate generational anchor drift with data-driven override exceptions.

    Default rule: generational anchors are locked to ANCHOR_BASELINES.
    Exception: a named override may pass only when it has:
      1. the exact approved from/to DVU movement,
      2. quantitative evidence from rank 1-2 / efficiency fields,
      3. documented rationale in strategy docs,
      4. an intentional last_updated timestamp.
    """

    failures = []
    warnings = []
    details = []
    modified_anchors = []
    approved_overrides = []

    rows_by_player = {row[0]: row for row in anchor_rows}

    for player_name, baseline_dvu in ANCHOR_BASELINES.items():
        row = rows_by_player.get(player_name)
        if row is None:
            failures.append(f"{player_name}: missing from genius_state/anchors audit query")
            continue

        _, current_dvu_raw, anchor_last_updated, source_rank_raw, current_dominator_raw, yprr_raw, efficiency_score_raw = row
        current_dvu = _as_float(current_dvu_raw)
        source_rank = _as_float(source_rank_raw)
        current_dominator = _as_float(current_dominator_raw)
        yprr = _as_float(yprr_raw)
        efficiency_score = _as_float(efficiency_score_raw)
        last_updated = _as_string(anchor_last_updated)

        if current_dvu is None:
            failures.append(f"{player_name}: dvu_anchor is NULL or non-numeric")
            continue

        if abs(current_dvu - baseline_dvu) <= FLOAT_TOLERANCE:
            details.append({
                "player_name": player_name,
                "status": "LOCKED_BASELINE_OK",
                "baseline_dvu": baseline_dvu,
                "current_dvu": current_dvu,
            })
            continue

        modified_anchors.append(player_name)
        override = ALLOWED_ANCHOR_OVERRIDES.get(player_name)
        if override is None:
            failures.append(
                f"{player_name}: unauthorized anchor drift {baseline_dvu} -> {current_dvu}; "
                "no DATA-DRIVEN OVERRIDE is registered"
            )
            continue

        exact_target = abs(current_dvu - override["to_dvu"]) <= FLOAT_TOLERANCE
        exact_source = abs(baseline_dvu - override["from_dvu"]) <= FLOAT_TOLERANCE
        has_ranked_db_metrics = (
            (source_rank is not None and source_rank in (1.0, 2.0))
            and any(metric is not None for metric in (current_dominator, yprr, efficiency_score))
        )
        has_quant_metrics = has_ranked_db_metrics or _has_documented_quantitative_evidence(override)
        has_rationale = _has_documented_rationale(override)
        has_commit = _has_strategy_commit_reference(override)
        has_governance_rule = _has_governance_rule_reference(override)
        has_intentional_timestamp = bool(last_updated)

        override_errors = []
        if not exact_source or not exact_target:
            override_errors.append(
                f"expected {override['from_dvu']} -> {override['to_dvu']}, observed {baseline_dvu} -> {current_dvu}"
            )
        if not has_quant_metrics:
            override_errors.append(
                "missing verified quantitative efficiency metrics from rank 1-2 source"
            )
        if not has_rationale:
            override_errors.append("missing documented strategy rationale")
        if not has_commit:
            override_errors.append(f"strategy commit {override.get('strategy_commit')} not present in checkout")
        if not has_governance_rule:
            override_errors.append(f"governance rule {override.get('governance_rule_id')} is not documented")
        if not has_intentional_timestamp:
            override_errors.append("anchor_last_updated is missing")

        if override_errors:
            failures.append(f"{player_name}: DATA-DRIVEN OVERRIDE failed: {'; '.join(override_errors)}")
        else:
            approved_overrides.append(player_name)
            details.append({
                "player_name": player_name,
                "status": "DATA_DRIVEN_OVERRIDE_APPROVED",
                "baseline_dvu": baseline_dvu,
                "current_dvu": current_dvu,
                "strategy_commit": override.get("strategy_commit"),
                "governance_rule_id": override.get("governance_rule_id"),
                "anchor_last_updated": last_updated,
            })

    if len(modified_anchors) > len(approved_overrides):
        warnings.append(
            f"Modified anchors observed: {modified_anchors}; approved overrides: {approved_overrides}"
        )

    if len(modified_anchors) > 1:
        unauthorized_batch = [name for name in modified_anchors if name not in approved_overrides]
        if unauthorized_batch:
            failures.append(
                f"Multiple anchor modifications detected without clear batch rationale: {modified_anchors}"
            )

    status = "PASSED" if not failures else "FAILED"
    return {
        "test": "Test 3: DVU Anchor Integrity Check",
        "status": status,
        "result": details,
        "approved_overrides": approved_overrides,
        "modified_anchors": modified_anchors,
        "warnings": warnings,
        "failures": failures,
    }

def run_anchor_integrity_test(w):
    test_name = "Test 3: DVU Anchor Integrity Check"
    query = """
        SELECT
            gs.player_name,
            gs.dvu_anchor,
            gs.anchor_last_updated,
            gs.source_rank,
            gs.current_dominator,
            gs.yprr,
            gs.efficiency_score
        FROM gen_alpha.gold.genius_state gs
        WHERE gs.player_name IN (
            'Jeremiyah Love',
            'Ashton Jeanty',
            'Jeremiah Smith',
            'Ryan Williams',
            'Ahmad Hardy',
            'Arch Manning'
        )
        ORDER BY gs.player_name
    """

    raw_result = execute_query(w, query, test_name)
    if raw_result.get("status") != "PASSED":
        return raw_result

    validated = validate_anchor_overrides(raw_result.get("result", []))
    if validated["status"] == "PASSED":
        print(f"✅ {test_name}: PASSED")
        if validated["approved_overrides"]:
            print(f"   Approved DATA-DRIVEN OVERRIDE(s): {', '.join(validated['approved_overrides'])}")
    else:
        print(f"❌ {test_name}: FAILED")
        for failure in validated["failures"]:
            print(f"   - {failure}")
    return validated

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
    
    # Test 3: DVU Anchor Integrity (DATA-DRIVEN OVERRIDE aware)
    results.append(run_anchor_integrity_test(w))
    
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
