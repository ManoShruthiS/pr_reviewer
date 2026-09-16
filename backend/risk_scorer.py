def calculate_risk_score(issues: list) -> int:
    if not issues:
        return 0

    score = 0
    for issue in issues:
        severity = issue.get("severity", "low").lower()
        itype = issue.get("type", "quality").lower()

        if severity == "high":
            score += 20
        elif severity == "medium":
            score += 10
        else:
            score += 5

        if itype == "security":
            score += 10
        elif itype == "bug":
            score += 5

    return min(score, 100)
