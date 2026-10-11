import json
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def explain_issues(issues: list, files: list) -> list:
    if not issues:
        return []

    context = ""
    for file in files:
        context += f"\n--- {file['filename']} ---\n{file['patch'][:2000]}\n"

    issues_text = json.dumps(issues, indent=2)

    prompt = f"""You are a code review assistant. Given the following detected issues and code context,
provide for each issue:
1. A clear explanation of what the issue means
2. The potential impact
3. A suggested fix (code snippet)

Code context:
{context}

Detected issues:
{issues_text}

Return a JSON array where each object has:
- "explanation": clear explanation of the issue
- "impact": potential impact
- "fix": suggested code fix
- "severity": confirmed severity (high/medium/low)

Return only valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a code review expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        result = json.loads(response.choices[0].message.content)

        for i, issue in enumerate(issues):
            if i < len(result):
                issue["explanation"] = result[i].get("explanation", "")
                issue["impact"] = result[i].get("impact", "")
                issue["fix"] = result[i].get("fix", "")
                if result[i].get("severity"):
                    issue["severity"] = result[i]["severity"]

    except Exception as e:
        for issue in issues:
            issue["explanation"] = issue.get("message", "")
            issue["fix"] = "Review this issue manually."

    return issues
