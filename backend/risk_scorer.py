# ==============================================================================
# FILE: risk_scorer.py
# PURPOSE: Calculates a "Health & Risk Score" (from 0 to 100) for a Pull Request.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like a traffic police officer giving penalty points on a driver's license:
# - If you commit a dangerous crime (Security flaw) -> Huge penalty (+35 points)
# - If you break a road rule (Bug/error)            -> Medium penalty (+25 points)
# - If your car is slightly dusty (Code style smell) -> Small penalty (+2 to +8 points)
# - The higher the points (closer to 100), the more dangerous the code is!
# ==============================================================================


# This function takes in a list of all problems found in the code ("issues")
# and gives back a single number between 0 and 100 ("score").
def calculate_risk_score(issues: list) -> int:
    """
    Computes an authentic, defensible risk score from 0 to 100.
    - Security vulnerabilities (CWE/CVEs): major risk driver (10-35 pts)
    - Functional bugs & exceptions: moderate-high risk driver (5-25 pts)
    - Quality & maintainability smells (unused imports, line count): minor risk (2-8 pts)
    """
    # STEP 1: Check if there are no problems at all.
    # If the list of issues is empty, the code is 100% clean, so risk is 0!
    if not issues:
        return 0

    # STEP 2: Start our penalty counter at 0.
    score = 0

    # STEP 3: Go through each problem in the list, one by one.
    for issue in issues:
        # Check how dangerous this problem is: 'critical', 'high', 'medium', or 'low'.
        # We use .lower() to convert text to lowercase so 'High' and 'high' work the same.
        severity = issue.get("severity", "low").lower()

        # Check what category this problem belongs to: 'security', 'bug', or 'quality'.
        itype = issue.get("type", "quality").lower()

        # --- CATEGORY A: SECURITY VULNERABILITIES ---
        # These are dangerous hacker entry points (like SQL injection or password leaks).
        if itype == "security":
            # Very dangerous security issue -> add 35 penalty points
            if severity in ["critical", "high"]:
                score += 35
            # Moderate security risk -> add 20 penalty points
            elif severity == "medium":
                score += 20
            # Minor security notice -> add 10 penalty points
            else:
                score += 10

        # --- CATEGORY B: FUNCTIONAL BUGS ---
        # These are mistakes that will make the software crash or give wrong output.
        elif itype == "bug":
            # Serious bug that will crash the application -> add 25 points
            if severity in ["critical", "high"]:
                score += 25
            # Moderate bug (e.g. unexpected variable value) -> add 15 points
            elif severity == "medium":
                score += 15
            # Minor bug -> add 6 points
            else:
                score += 6

        # --- CATEGORY C: CODE QUALITY & CLEANLINESS ---
        # These don't break the code, but make it messy (e.g. unused imports, long functions).
        else:
            # Messy structure that needs attention -> add 8 points
            if severity in ["critical", "high"]:
                score += 8
            # Slightly disorganized code -> add 4 points
            elif severity == "medium":
                score += 4
            # Tiny cleanliness warning -> add 2 points
            else:
                score += 2

    # STEP 4: Cap the maximum score at 100.
    # Even if there are 50 issues that add up to 200 points,
    # the maximum risk percentage is always 100%.
    return min(score, 100)
