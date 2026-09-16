let typeChart = null;
let severityChart = null;

const dummyReview = {
    riskScore: 72,
    issues: [
        {
            type: "security",
            severity: "high",
            file: "config.py",
            line: 15,
            message: "Hardcoded password detected",
            explanation: "A password is written directly in the code. Anyone who views the repository can see it, which is a major security risk.",
            fix: "Use environment variables:\nimport os\npassword = os.environ.get('DB_PASSWORD')"
        },
        {
            type: "security",
            severity: "medium",
            file: "utils.py",
            line: 42,
            message: "Use of eval() detected",
            explanation: "eval() can execute arbitrary code and is a common attack vector for code injection.",
            fix: "Use ast.literal_eval() instead of eval()"
        },
        {
            type: "bug",
            severity: "medium",
            file: "main.py",
            line: 8,
            message: "Unused import 'os'",
            explanation: "The module 'os' is imported but never used in this file.",
            fix: "Remove the unused import: import os"
        },
        {
            type: "bug",
            severity: "low",
            file: "handler.py",
            line: 23,
            message: "Variable 'result' referenced before assignment",
            explanation: "The variable 'result' may be used before it has been assigned a value, causing a runtime error.",
            fix: "Initialize result = None before the if block"
        },
        {
            type: "quality",
            severity: "low",
            file: "api.py",
            line: 55,
            message: "Function too long (58 lines)",
            explanation: "Long functions are harder to read, test, and maintain. Consider breaking it into smaller functions.",
            fix: "Split into smaller helper functions"
        }
    ]
};

function runReview() {
    const prUrl = document.getElementById('prUrl').value.trim();
    if (!prUrl) {
        alert('Please enter a GitHub Pull Request URL');
        return;
    }

    document.getElementById('results').classList.add('hidden');
    document.getElementById('loading').classList.remove('hidden');

    // Phase 1: Using dummy data. Phase 2: Replace with actual API call
    // fetch('http://localhost:8000/review', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ pr_url: prUrl })
    // })
    //     .then(res => res.json())
    //     .then(data => displayResults(data))
    //     .catch(err => alert('Error: ' + err));

    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
        displayResults(dummyReview);
    }, 1500);
}

function displayResults(review) {
    document.getElementById('results').classList.remove('hidden');

    // Risk score
    const score = review.riskScore;
    const scoreEl = document.getElementById('riskScore');
    const levelEl = document.getElementById('riskLevel');
    scoreEl.textContent = score;

    scoreEl.className = 'risk-score';
    levelEl.className = 'risk-level';

    if (score <= 25) {
        scoreEl.classList.add('risk-low');
        levelEl.textContent = 'LOW RISK';
        levelEl.classList.add('risk-low');
    } else if (score <= 50) {
        scoreEl.classList.add('risk-medium');
        levelEl.textContent = 'MEDIUM RISK';
        levelEl.classList.add('risk-medium');
    } else if (score <= 75) {
        scoreEl.classList.add('risk-high');
        levelEl.textContent = 'HIGH RISK';
        levelEl.classList.add('risk-high');
    } else {
        scoreEl.classList.add('risk-critical');
        levelEl.textContent = 'CRITICAL RISK';
        levelEl.classList.add('risk-critical');
    }

    // Issues list
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';

    review.issues.forEach(issue => {
        const card = document.createElement('div');
        card.className = `issue-card severity-${issue.severity}`;
        card.innerHTML = `
            <div class="issue-header">
                <span class="issue-type type-${issue.type}">${issue.type}</span>
                <span class="issue-severity severity-${issue.severity}">${issue.severity.toUpperCase()}</span>
            </div>
            <div class="issue-message"><strong>${issue.message}</strong></div>
            <div class="issue-explanation">${issue.explanation}</div>
            <div class="issue-fix">${issue.fix}</div>
        `;
        issuesList.appendChild(card);
    });

    // Charts
    drawTypeChart(review.issues);
    drawSeverityChart(review.issues);
}

function drawTypeChart(issues) {
    const counts = { security: 0, bug: 0, quality: 0 };
    issues.forEach(i => counts[i.type]++);

    if (typeChart) typeChart.destroy();
    typeChart = new Chart(document.getElementById('typeChart'), {
        type: 'doughnut',
        data: {
            labels: ['Security', 'Bug', 'Quality'],
            datasets: [{
                data: [counts.security, counts.bug, counts.quality],
                backgroundColor: ['#ef4444', '#eab308', '#3b82f6']
            }]
        },
        options: {
            plugins: { legend: { labels: { color: '#94a3b8' } } }
        }
    });
}

function drawSeverityChart(issues) {
    const counts = { high: 0, medium: 0, low: 0 };
    issues.forEach(i => counts[i.severity]++);

    if (severityChart) severityChart.destroy();
    severityChart = new Chart(document.getElementById('severityChart'), {
        type: 'bar',
        data: {
            labels: ['High', 'Medium', 'Low'],
            datasets: [{
                label: 'Issues',
                data: [counts.high, counts.medium, counts.low],
                backgroundColor: ['#ef4444', '#eab308', '#22c55e']
            }]
        },
        options: {
            scales: {
                y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
            },
            plugins: { legend: { display: false } }
        }
    });
}
