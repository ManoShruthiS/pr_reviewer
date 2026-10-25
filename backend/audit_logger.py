"""
PR-Doc Audit Logger & Compliance Tracking Module.

Provides structured auditing for code review events, risk score tracking,
and security policy evaluation across GitHub pull requests.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup dedicated logger
logger = logging.getLogger("pr_doc.audit")

AUDIT_LOG_DIR = Path(__file__).resolve().parent / "logs"
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "pr_review_audit.jsonl"


def ensure_audit_dir() -> Path:
    """Ensure the audit log directory exists."""
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_LOG_FILE


def log_review_event(
    pr_url: str,
    risk_score: int,
    issue_count: int,
    critical_count: int = 0,
    coverage_summary: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record a completed pull request review event into the audit trail.

    Args:
        pr_url: Target GitHub PR URL.
        risk_score: Computed composite risk score (0-100).
        issue_count: Total issues detected.
        critical_count: Number of critical security vulnerabilities.
        coverage_summary: Language coverage metrics.
        client_ip: Optional origin IP of the review request.

    Returns:
        The serialized audit entry dict.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Classify verdict risk level
    if risk_score >= 70:
        risk_level = "CRITICAL"
        merge_verdict = "BLOCK"
    elif risk_score >= 35:
        risk_level = "MODERATE"
        merge_verdict = "CAUTION"
    else:
        risk_level = "LOW"
        merge_verdict = "APPROVE"

    entry: Dict[str, Any] = {
        "timestamp": timestamp,
        "pr_url": pr_url,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "merge_verdict": merge_verdict,
        "issue_count": issue_count,
        "critical_count": critical_count,
        "coverage": coverage_summary or {},
        "client_ip": client_ip or "local"
    }

    try:
        log_file = ensure_audit_dir()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("Recorded audit log for %s with risk score %d", pr_url, risk_score)
    except Exception as exc:
        logger.error("Failed to write audit log entry: %s", exc)

    return entry


def get_recent_audit_logs(limit: int = 25) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent review audit log entries.

    Args:
        limit: Maximum number of recent log entries to return.

    Returns:
        List of audit log dictionaries in reverse-chronological order.
    """
    if not AUDIT_LOG_FILE.exists():
        return []

    entries: List[Dict[str, Any]] = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as exc:
        logger.warning("Error reading audit logs: %s", exc)
        return []

    return entries[-limit:][::-1]


def get_audit_metrics() -> Dict[str, Any]:
    """Calculate aggregate audit statistics across all logged inspections."""
    logs = get_recent_audit_logs(limit=1000)
    if not logs:
        return {
            "total_inspections": 0,
            "avg_risk_score": 0.0,
            "blocked_count": 0,
            "approved_count": 0
        }

    total = len(logs)
    avg_score = round(sum(item.get("risk_score", 0) for item in logs) / total, 1)
    blocked = sum(1 for item in logs if item.get("merge_verdict") == "BLOCK")
    approved = sum(1 for item in logs if item.get("merge_verdict") == "APPROVE")

    return {
        "total_inspections": total,
        "avg_risk_score": avg_score,
        "blocked_count": blocked,
        "approved_count": approved
    }
