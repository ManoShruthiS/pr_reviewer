'use strict';

// Base URL for FastAPI backend (relative if served directly from FastAPI, otherwise localhost:8000)
const API_BASE = window.location.origin.includes('8000') ? '' : 'http://localhost:8000';

// Default / fallback review dataset
const defaultReview = {
  riskScore: 72,
  repo: 'enterprise/auth-service#14',
  prTitle: 'feat(auth): Add user authentication and token verification',
  author: 'dev-contributor',
  issues: [
    {
      id: 1,
      type: 'security',
      severity: 'high',
      message: 'Hardcoded password / secret detected (CWE-798)',
      file: 'auth_service.py',
      line: 4,
      cwe: '798',
      source: 'Static Tool (Bandit)',
      confidence: 'High',
      explanation: 'Sensitive production credentials and JWT secret keys are hardcoded directly into the repository. Storing secrets in source code risks immediate exposure if the repository is audited or shared.',
      impact: 'Critical: System authentication bypass, privilege escalation, and token forgery allowing full infrastructure compromise.',
      fix: 'import os\nfrom dotenv import load_dotenv\n\nload_dotenv()\nJWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")\nDATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")',
      fixExplanation: 'Extract sensitive credentials into an external .env file and add .env to .gitignore.'
    },
    {
      id: 2,
      type: 'security',
      severity: 'high',
      message: 'Unsafe eval() usage on user payload (CWE-95)',
      file: 'auth_service.py',
      line: 9,
      cwe: '95',
      source: 'Static Tool (Bandit)',
      confidence: 'High',
      explanation: 'Dynamic execution with eval() processes arbitrary Python expressions without sanitization. If an untrusted payload reaches this call, an attacker can achieve Remote Code Execution (RCE).',
      impact: 'Critical: Arbitrary system command execution on the host operating system.',
      fix: 'import ast\n# Safely evaluate literal Python structures\nsafe_user_obj = ast.literal_eval(raw_payload)',
      fixExplanation: 'Use ast.literal_eval for literals, or json.loads for JSON formatted token data.'
    },
    {
      id: 3,
      type: 'bug',
      severity: 'high',
      message: 'Reference to undefined variable (Runtime NameError)',
      file: 'database.py',
      line: 27,
      source: 'Static Tool (Pyflakes)',
      confidence: 'High',
      explanation: "Variable 'undefined_variable_total' is referenced before assignment. At runtime, executing this function will trigger an unhandled NameError terminating the process.",
      impact: 'High: Immediate crash in production analytics pipeline upon request execution.',
      fix: '# Initialize or compute variable before usage\nundefined_variable_total = calculate_total_records()\nresult = undefined_variable_total + 10\nreturn result',
      fixExplanation: 'Define the variable in local scope or import the needed dependency.'
    },
    {
      id: 4,
      type: 'quality',
      severity: 'medium',
      message: "Bare 'except:' intercepts fatal system signals",
      file: 'auth_service.py',
      line: 16,
      source: 'Static Tool (AST Analysis)',
      confidence: 'High',
      explanation: "A bare 'except:' clause catches all exceptions, including KeyboardInterrupt and SystemExit, masking fatal database connection failures and silent bugs.",
      impact: 'Medium: Silent failure leading to orphaned database connections and undiagnosed runtime hangs.',
      fix: 'try:\n    return execute_query(query)\nexcept DatabaseError as err:\n    logger.error(f"Authentication query failed: {err}")\n    raise',
      fixExplanation: 'Specify exact exceptions (e.g. DatabaseError) and log stack traces.'
    },
    {
      id: 5,
      type: 'bug',
      severity: 'medium',
      message: 'Mutable default argument in function definition',
      file: 'database.py',
      line: 23,
      source: 'Static Tool (AST Analysis)',
      confidence: 'High',
      explanation: 'Python evaluates default arguments once at function definition. Mutating cache_list modifies the list for all future calls across independent user requests.',
      impact: 'Medium: Memory leak and state contamination across independent user queries.',
      fix: 'def get_user_records(user_id, cache_list=None):\n    if cache_list is None:\n        cache_list = []\n    cache_list.append(user_id)\n    return cache_list',
      fixExplanation: 'Use None as default sentinel and instantiate a fresh list inside function body.'
    },
    {
      id: 6,
      type: 'quality',
      severity: 'low',
      message: 'Unused import module detected',
      file: 'database.py',
      line: 21,
      source: 'Static Tool (Pyflakes)',
      confidence: 'High',
      explanation: "Module 'math' is imported in the header but never called throughout the module scope.",
      impact: 'Low: Module bloat, slower cold start times, and confusing dependency trees.',
      fix: '# Remove unused import:\n# import math',
      fixExplanation: 'Clean up unused imports to maintain clean code standards.'
    }
  ],
  coverage: {
    total_files: 2,
    analyzed_files: 2,
    skipped_files: 0,
    coverage_percentage: 100,
    languages_detected: ['Python'],
    tools_engaged: ['Bandit v1.9.4', 'Pyflakes v4.0', 'AST Quality', 'AI Contextual Review'],
    file_breakdown: [
      { filename: 'auth_service.py', language: 'Python', category: 'source_code', status: 'Analyzed', methods: ['Bandit', 'Pyflakes', 'AST Quality', 'AI Reviewer'] },
      { filename: 'database.py', language: 'Python', category: 'source_code', status: 'Analyzed', methods: ['Bandit', 'Pyflakes', 'AST Quality', 'AI Reviewer'] }
    ]
  }
};

let currentReview = { ...defaultReview };

// Burgundy & Dark Blue Theme Chart Palette
const palette = {
  type: { security: '#f43f5e', bug: '#f59e0b', quality: '#38bdf8' },
  severity: { high: '#f43f5e', medium: '#f59e0b', low: '#10b981' }
};

let typeChart = null;
let severityChart = null;
let toastTimer = null;
let reviewSequence = 0;

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function escapeHTML(value) {
  return String(value || '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

function showToast(message) {
  const toast = $('#toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('show'), 3800);
}

function getRisk(score) {
  if (score <= 25) return { name: 'LOW RISK', className: 'low', color: '#10b981', caption: 'Only minor stylistic observations. Safe to merge with standard approvals.' };
  if (score <= 50) return { name: 'MEDIUM RISK', className: 'medium', color: '#f59e0b', caption: 'Moderate bug or maintainability risks. Resolve findings prior to release.' };
  if (score <= 75) return { name: 'HIGH RISK', className: 'high', color: '#fb7185', caption: 'High-severity vulnerabilities detected. Fix critical findings before merge.' };
  return { name: 'CRITICAL RISK', className: 'critical', color: '#f43f5e', caption: 'Block merge immediately! Remote code execution or hardcoded secrets found.' };
}

function validatePRUrl(value) {
  if (!value) return false;
  const lower = value.toLowerCase();
  if (lower.includes('demo') || lower.includes('sample')) return true;
  try {
    const url = new URL(value);
    if (url.hostname.toLowerCase() !== 'github.com') return false;
    const parts = url.pathname.split('/').filter(Boolean);
    return parts.length >= 4 && parts[2] === 'pull';
  } catch {
    return false;
  }
}

function repoFromURL(value) {
  try {
    const parts = new URL(value).pathname.split('/').filter(Boolean);
    return `${parts[0]}/${parts[1]}#${parts[3] || '1'}`;
  } catch {
    return 'enterprise/auth-service#14';
  }
}

function countBy(key, values = []) {
  return values.reduce((result, item) => {
    const k = (item[key] || 'quality').toLowerCase();
    result[k] = (result[k] || 0) + 1;
    return result;
  }, {});
}

function updateRiskScore(score) {
  const risk = getRisk(score);
  const scoreEl = $('#riskScore');
  const levelEl = $('#riskLevel');
  const captionEl = $('#riskCaption');
  const gaugeArc = $('#gaugeArc');
  const riskGauge = $('#riskGauge');

  if (scoreEl) {
    scoreEl.textContent = score;
    scoreEl.style.color = risk.color;
  }
  if (levelEl) {
    levelEl.textContent = risk.name;
    levelEl.className = `risk-badge-pill ${risk.className}`;
  }
  if (captionEl) captionEl.textContent = risk.caption;
  if (gaugeArc) {
    gaugeArc.style.stroke = risk.color;
    const totalLength = 282.7;
    gaugeArc.style.strokeDasharray = String(totalLength);
    gaugeArc.style.strokeDashoffset = String(totalLength * (1 - score / 100));
  }
  if (riskGauge) riskGauge.dataset.score = String(score);
}

function updateMetrics(issues = []) {
  const types = countBy('type', issues);
  const secEl = $('#securityCount');
  const bugEl = $('#bugCount');
  const qualEl = $('#qualityCount');
  const totalEl = $('#totalIssueCount');
  const headingEl = $('#issueHeadingCount');

  if (secEl) secEl.textContent = types.security || 0;
  if (bugEl) bugEl.textContent = types.bug || 0;
  if (qualEl) qualEl.textContent = types.quality || 0;
  if (totalEl) totalEl.textContent = issues.length;
  if (headingEl) headingEl.textContent = `${issues.length} Issues Flagged`;
}

function renderCharts(issues = []) {
  if (!window.Chart) {
    showToast('Chart.js library is loading or offline.');
    return;
  }
  const types = countBy('type', issues);
  const severities = countBy('severity', issues);

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 600, easing: 'easeOutQuart' },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(190, 24, 93, 0.4)',
        borderWidth: 1,
        padding: 10,
        titleColor: '#f8fafc',
        bodyColor: '#e2e8f0',
        titleFont: { family: 'Inter', size: 12, weight: '700' },
        bodyFont: { family: 'Inter', size: 11 }
      }
    }
  };

  if (typeChart) typeChart.destroy();
  if (severityChart) severityChart.destroy();

  const typeCanvas = $('#typeChart');
  if (typeCanvas) {
    typeChart = new Chart(typeCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Security', 'Bug', 'Quality'],
        datasets: [{
          data: [types.security || 0, types.bug || 0, types.quality || 0],
          backgroundColor: [palette.type.security, palette.type.bug, palette.type.quality],
          borderColor: '#0f172a',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: { ...commonOptions, cutout: '72%', layout: { padding: 2 } }
    });
  }

  const sevCanvas = $('#severityChart');
  if (sevCanvas) {
    severityChart = new Chart(sevCanvas, {
      type: 'bar',
      data: {
        labels: ['High', 'Medium', 'Low'],
        datasets: [{
          data: [severities.high || 0, severities.medium || 0, severities.low || 0],
          backgroundColor: [palette.severity.high, palette.severity.medium, palette.severity.low],
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 38
        }]
      },
      options: {
        ...commonOptions,
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11, weight: '600' } }
          },
          y: {
            beginAtZero: true,
            suggestedMax: Math.max(3, ...Object.values(severities)),
            ticks: { precision: 0, stepSize: 1, color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } },
            grid: { color: 'rgba(148, 163, 184, 0.08)', drawTicks: false },
            border: { display: false }
          }
        }
      }
    });
  }

  const legendEl = $('#typeLegend');
  if (legendEl) {
    legendEl.innerHTML = [
      ['security', 'Security Flaws'], ['bug', 'Bugs & Errors'], ['quality', 'Code Quality']
    ].map(([key, label]) => `<div><span class="legend-dot" style="background:${palette.type[key]};box-shadow:0 0 8px ${palette.type[key]}"></span><span>${label}</span><strong>${types[key] || 0}</strong></div>`).join('');
  }
}

function createIssueCard(issue, index) {
  const rawType = (issue.type || 'quality').toLowerCase();
  const rawSev = (issue.severity || 'low').toLowerCase();
  const typeName = rawType === 'quality' ? 'Quality' : rawType[0].toUpperCase() + rawType.slice(1);
  const severityName = rawSev[0].toUpperCase() + rawSev.slice(1);
  const fileStr = issue.file || 'source.py';
  const lineStr = issue.line ? ` · Line ${issue.line}` : '';
  const cweStr = issue.cwe ? ` · CWE-${issue.cwe}` : '';
  const sourceStr = issue.source || 'AI Contextual Review';
  const isAi = sourceStr.toLowerCase().includes('ai');
  const confidenceStr = issue.confidence || (isAi ? 'Medium' : 'High');

  return `<article class="issue-card severity-${escapeHTML(rawSev)}" style="animation-delay:${Math.min(index * 0.05, 0.4)}s" data-issue-id="${issue.id}">
    <div class="issue-topline">
      <div class="issue-badges">
        <span class="type-badge type-${escapeHTML(rawType)}">${escapeHTML(typeName)}</span>
        <span class="severity-badge">${escapeHTML(severityName)}</span>
        <span class="source-badge ${isAi ? 'ai' : ''}">${isAi ? '✦' : '🛡️'} ${escapeHTML(sourceStr)}</span>
        <span class="confidence-badge">${escapeHTML(confidenceStr)} Conf.</span>
      </div>
      <span class="issue-file-chip">${escapeHTML(fileStr)}${lineStr}${cweStr}</span>
    </div>
    <h3 class="issue-title">${escapeHTML(issue.message || 'Issue detected')}</h3>
    <p class="issue-explanation">${escapeHTML(issue.explanation || '')}</p>
    ${issue.impact ? `<div class="issue-impact-callout"><strong>Security Impact:</strong> ${escapeHTML(issue.impact)}</div>` : ''}
    <div class="fix-label">
      <span>✦</span> Recommended AI Code Fix ${issue.fixExplanation ? `— <span style="font-weight:400;color:var(--text-secondary);">${escapeHTML(issue.fixExplanation)}</span>` : ''}
    </div>
    <div class="fix-block">
      <code>${escapeHTML(issue.fix || '# Review and refactor manually')}</code>
      <button class="copy-button" type="button" data-copy-issue="${issue.id}">Copy Fix</button>
    </div>
  </article>`;
}

function renderIssues() {
  const issues = currentReview.issues || [];
  const sevFilter = $('#severityFilter') ? $('#severityFilter').value : 'all';
  const typeFilter = $('#typeFilter') ? $('#typeFilter').value : 'all';

  const filtered = issues.filter(issue => {
    const matchesSev = sevFilter === 'all' || (issue.severity || '').toLowerCase() === sevFilter;
    const matchesType = typeFilter === 'all' || (issue.type || '').toLowerCase() === typeFilter;
    return matchesSev && matchesType;
  });

  const listEl = $('#issuesList');
  const emptyEl = $('#emptyState');
  if (listEl) {
    listEl.innerHTML = filtered.map(createIssueCard).join('');
  }
  if (emptyEl) {
    emptyEl.hidden = filtered.length !== 0;
  }
}

function updateSummary(issues = [], repo = '', title = '') {
  const summaryEl = $('#aiSummary');
  if (!summaryEl) return;
  if (!issues.length) {
    summaryEl.innerHTML = `<strong>Clean pull request!</strong> No critical security vulnerabilities, bugs, or quality violations detected in <code>${escapeHTML(repo)}</code>. Approved for merge.`;
    return;
  }
  const critical = issues.filter(i => (i.severity || '').toLowerCase() === 'high');
  const types = countBy('type', issues);
  const first = critical[0] || issues[0];

  summaryEl.innerHTML = `Automated analysis of <strong>${escapeHTML(title || repo)}</strong> identified <strong>${issues.length} potential issue${issues.length === 1 ? '' : 's'}</strong> across ${Object.keys(types).length} security &amp; defect categories. ${first ? `Highest risk item: <code>${escapeHTML(first.message)}</code> located in <code>${escapeHTML(first.file)}</code>.` : ''} Verify security compliance and apply suggested fixes before merging into production.`;
}

function renderCoverage(coverage) {
  if (!coverage) {
    coverage = defaultReview.coverage;
  }
  if (!coverage) return;

  const ratePill = $('#coverageRatePill');
  if (ratePill) {
    ratePill.textContent = `${coverage.coverage_percentage}% Analyzed`;
    ratePill.style.color = coverage.coverage_percentage >= 80 ? '#34d399' : '#f59e0b';
  }

  const analyzedEl = $('#coverageAnalyzedCount');
  if (analyzedEl) analyzedEl.textContent = `${coverage.analyzed_files} / ${coverage.total_files}`;

  const skippedEl = $('#coverageSkippedCount');
  if (skippedEl) skippedEl.textContent = coverage.skipped_files || 0;

  const langCountEl = $('#coverageLangCount');
  if (langCountEl) langCountEl.textContent = (coverage.languages_detected || []).length;

  const langsList = $('#detectedLanguagesList');
  if (langsList) {
    const langs = coverage.languages_detected || [];
    langsList.innerHTML = langs.length
      ? langs.map(l => `<span class="lang-chip">${escapeHTML(l)}</span>`).join('')
      : '<span class="lang-chip">None detected</span>';
  }

  const toolsList = $('#engagedToolsList');
  if (toolsList) {
    const tools = coverage.tools_engaged || [];
    toolsList.innerHTML = tools.length
      ? tools.map(t => `<span class="tool-chip">${escapeHTML(t)}</span>`).join('')
      : '<span class="tool-chip">AI Reviewer</span>';
  }

  const manifestBody = $('#fileManifestBody');
  if (manifestBody) {
    const breakdown = coverage.file_breakdown || [];
    if (!breakdown.length) {
      manifestBody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:12px;color:var(--text-muted);">No file breakdown available.</td></tr>';
    } else {
      manifestBody.innerHTML = breakdown.map(f => {
        const isAnalyzed = f.status === 'Analyzed';
        const methodsStr = Array.isArray(f.methods) ? f.methods.join(', ') : (f.methods || 'AI Reviewer');
        return `<tr>
          <td class="file-name-cell">${escapeHTML(f.filename)}</td>
          <td>${escapeHTML(f.language || 'Unknown')}</td>
          <td><span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">${escapeHTML(f.category || 'code')}</span></td>
          <td>
            <span class="${isAnalyzed ? 'status-tag-analyzed' : 'status-tag-skipped'}">
              ${escapeHTML(f.status || 'Analyzed')}
            </span>
          </td>
          <td><small style="color:var(--text-secondary);">${escapeHTML(methodsStr)}</small></td>
        </tr>`;
      }).join('');
    }
  }
}

function renderReview(reviewData) {
  currentReview = reviewData;
  const repo = reviewData.repo || 'example/repository';
  const prTitle = reviewData.prTitle || 'GitHub Pull Request';
  const issues = reviewData.issues || [];
  const score = Number(reviewData.riskScore) || 0;

  updateRiskScore(score);
  updateMetrics(issues);
  updateSummary(issues, repo, prTitle);
  renderCoverage(reviewData.coverage);

  const repoEl = $('#reviewedRepo');
  if (repoEl) repoEl.textContent = repo;

  const titleEl = $('#resultsHeadingTitle');
  if (titleEl) titleEl.textContent = prTitle;

  renderCharts(issues);
  renderIssues();

  const resultsSection = $('#results');
  if (resultsSection) {
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Perform real API review with fallback
async function performReview(url) {
  const thisSequence = ++reviewSequence;
  const loading = $('#loadingState');
  const results = $('#results');
  const submitBtn = $('#reviewForm button');

  if (loading) loading.hidden = false;
  if (results) results.style.opacity = '0.35';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-sparkle">◌</span> Scanning…';
  }

  const steps = $$('.pipeline-step');
  const animateStep = (idx) => {
    steps.forEach((step, sIdx) => {
      step.classList.toggle('done', sIdx <= idx);
      const spinner = $('.step-spinner', step);
      if (spinner) spinner.remove();
      if (sIdx === idx + 1 && sIdx < steps.length) {
        const sp = document.createElement('span');
        sp.className = 'step-spinner';
        step.append(sp);
      }
    });
  };

  animateStep(0);

  try {
    // Step 1: Fetch
    animateStep(1);
    const response = await fetch(`${API_BASE}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pr_url: url })
    });

    animateStep(3);

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    animateStep(4);

    if (thisSequence !== reviewSequence) return;

    // Mark all steps done
    steps.forEach(step => {
      step.classList.add('done');
      const sp = $('.step-spinner', step);
      if (sp) sp.remove();
    });

    renderReview({
      riskScore: data.riskScore,
      repo: data.repo || repoFromURL(url),
      prTitle: data.prTitle || 'Pull Request Analysis',
      author: data.author || 'Contributor',
      issues: data.issues || [],
      coverage: data.coverage
    });

    const badge = $('#dataSourceBadge');
    if (badge) badge.textContent = 'Live Backend Scan';

    showToast(`Scan complete! Found ${data.issues ? data.issues.length : 0} issues (Risk: ${data.riskScore}/100).`);
    loadHistory();

  } catch (err) {
    console.warn('API review request failed, running offline fallback:', err);
    // Graceful offline fallback
    await new Promise(r => setTimeout(r, 1000));
    if (thisSequence !== reviewSequence) return;

    steps.forEach(step => step.classList.add('done'));

    const isSecurityDemo = url.includes('auth') || url.includes('security') || url.includes('/1');
    const isCleanDemo = url.includes('clean') || url.includes('/3');

    let fallbackIssues = defaultReview.issues;
    let fallbackScore = 72;

    if (isCleanDemo) {
      fallbackIssues = [
        {
          id: 1,
          type: 'quality',
          severity: 'low',
          message: 'Minor whitespace and naming consistency',
          file: 'config.py',
          line: 12,
          source: 'Static Tool (AST Analysis)',
          confidence: 'High',
          explanation: 'Function naming adheres to standard conventions. No security flaws or syntax bugs detected.',
          impact: 'None. Safe for production deployment.',
          fix: 'def get_database_url() -> str:\n    return os.getenv("DATABASE_URL", "sqlite:///app.db")',
          fixExplanation: 'Adheres to PEP 8 standards.'
        }
      ];
      fallbackScore = 15;
    } else if (!isSecurityDemo) {
      fallbackIssues = defaultReview.issues.slice(2, 6);
      fallbackScore = 45;
    }

    renderReview({
      riskScore: fallbackScore,
      repo: repoFromURL(url),
      prTitle: isCleanDemo ? 'Clean Feature PR' : (isSecurityDemo ? 'Critical Security Vulnerabilities PR' : 'Runtime Bugs & Warnings PR'),
      author: 'dev-contributor',
      issues: fallbackIssues,
      coverage: defaultReview.coverage
    });

    const badge = $('#dataSourceBadge');
    if (badge) badge.textContent = 'Offline Demo Mode';

    showToast('Offline demo simulation loaded successfully.');
  } finally {
    if (thisSequence === reviewSequence) {
      if (loading) loading.hidden = true;
      if (results) results.style.opacity = '1';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="btn-sparkle">✦</span> Run Analysis <span class="btn-arrow">→</span>';
      }
    }
  }
}

// Load past reviews from SQLite via FastAPI
async function loadHistory() {
  const tbody = $('#historyTableBody');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/history`);
    if (!res.ok) throw new Error('History endpoint error');
    const items = await res.json();

    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding:16px;text-align:center;color:#64748b;">No reviews stored in database yet. Run an analysis above!</td></tr>';
      return;
    }

    tbody.innerHTML = items.map(item => {
      const risk = getRisk(item.risk_score || 0);
      const dateStr = item.created_at ? new Date(item.created_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : 'Recently';
      return `<tr>
        <td style="font-family:var(--font-mono);color:#93c5fd;font-weight:600;">#${item.id}</td>
        <td>
          <div style="font-weight:600;color:var(--text-white);">${escapeHTML(item.pr_title || 'PR Review')}</div>
          <small style="color:#64748b;font-family:var(--font-mono);">${escapeHTML(item.pr_url)}</small>
        </td>
        <td>
          <span class="risk-badge-pill ${risk.className}">
            ${item.risk_score}/100 · ${risk.name}
          </span>
        </td>
        <td style="color:#94a3b8;font-size:11px;">${dateStr}</td>
        <td class="text-right">
          <button type="button" class="view-history-item-btn" data-history-id="${item.id}">View Report</button>
        </td>
      </tr>`;
    }).join('');

  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding:16px;text-align:center;color:#64748b;">Start FastAPI backend (<code>python -m uvicorn main:app</code>) to sync SQLite review history.</td></tr>';
  }
}

// Fetch single review from history
async function loadReviewById(id) {
  try {
    showToast(`Loading review #${id} from SQLite database...`);
    const res = await fetch(`${API_BASE}/review/${id}`);
    if (!res.ok) throw new Error('Failed to load review');
    const data = await res.json();
    renderReview({
      riskScore: data.riskScore,
      repo: repoFromURL(data.prUrl),
      prTitle: data.prTitle,
      author: 'Stored Review',
      issues: data.issues || []
    });
    showToast(`Loaded review #${id} (${data.prTitle})`);
  } catch (err) {
    showToast(`Could not load review #${id}: ${err.message}`);
  }
}

// Check backend status
async function checkSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (res.ok) {
      const data = await res.json();
      const dot = $('#liveStatusDot');
      if (dot) dot.style.background = '#10b981';
      const aiBadge = $('#aiModelBadge');
      if (aiBadge) aiBadge.textContent = data.ai_engine;
      const dataBadge = $('#dataSourceBadge');
      if (dataBadge) dataBadge.textContent = 'Backend Online';
    }
  } catch {
    const dot = $('#liveStatusDot');
    if (dot) dot.style.background = '#f59e0b';
    const dataBadge = $('#dataSourceBadge');
    if (dataBadge) dataBadge.textContent = 'Demo Mode (Offline)';
  }
}

// Setup Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Initial demo rendering
  renderReview(defaultReview);
  loadHistory();
  checkSystemStatus();

  // Review Form Submit
  const form = $('#reviewForm');
  if (form) {
    form.addEventListener('submit', event => {
      event.preventDefault();
      const input = $('#prUrl');
      const url = input.value.trim();
      const error = $('#urlError');
      if (!validatePRUrl(url)) {
        if (error) error.hidden = false;
        input.setAttribute('aria-invalid', 'true');
        input.focus();
        return;
      }
      if (error) error.hidden = true;
      input.removeAttribute('aria-invalid');
      performReview(url);
    });
  }

  // Quick Demo Preset Pills (.preset-chip and .preset-btn)
  $$('.preset-chip, .preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const url = btn.dataset.url;
      const input = $('#prUrl');
      if (input) input.value = url;
      const error = $('#urlError');
      if (error) error.hidden = true;
      performReview(url);
    });
  });

  // History Table Clicks
  const historyTable = $('#historyTableBody');
  if (historyTable) {
    historyTable.addEventListener('click', event => {
      const btn = event.target.closest('[data-history-id]');
      if (!btn) return;
      loadReviewById(btn.dataset.historyId);
    });
  }

  // Refresh History Button
  const refreshBtn = $('#refreshHistoryBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadHistory();
      showToast('Review history refreshed.');
    });
  }

  // Export / Print Report Button
  const exportBtn = $('#exportReportBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      window.print();
    });
  }

  // Input Clear Error on typing
  const prInput = $('#prUrl');
  if (prInput) {
    prInput.addEventListener('input', () => {
      const error = $('#urlError');
      if (error) error.hidden = true;
      prInput.removeAttribute('aria-invalid');
    });
  }

  // Filters
  const sevFilter = $('#severityFilter');
  if (sevFilter) sevFilter.addEventListener('change', renderIssues);
  const typeFilter = $('#typeFilter');
  if (typeFilter) typeFilter.addEventListener('change', renderIssues);

  // Copy code fix button
  const listEl = $('#issuesList');
  if (listEl) {
    listEl.addEventListener('click', async event => {
      const button = event.target.closest('[data-copy-issue]');
      if (!button) return;
      const issue = (currentReview.issues || []).find(item => String(item.id) === String(button.dataset.copyIssue));
      if (!issue || !issue.fix) return;
      try {
        await navigator.clipboard.writeText(issue.fix);
        button.textContent = 'Copied ✓';
        showToast('Suggested fix copied to clipboard.');
        window.setTimeout(() => { button.textContent = 'Copy Fix'; }, 1800);
      } catch {
        showToast('Clipboard access unavailable.');
      }
    });
  }

  // Sidebar navigation smooth scroll / active state
  $$('.nav-link').forEach(link => link.addEventListener('click', () => {
    $$('.nav-link').forEach(item => item.classList.toggle('active', item === link));
  }));
});
