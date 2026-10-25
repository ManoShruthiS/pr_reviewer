'use strict';

// Base URL for FastAPI backend (relative if served directly from FastAPI, otherwise localhost:8000)
const API_BASE = window.location.origin.includes('8000') ? '' : 'http://localhost:8000';

let currentReview = null;
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
  toastTimer = window.setTimeout(() => toast.classList.remove('show'), 3500);
}

function showReviewError(title, message) {
  const errCard = $('#reviewError');
  const errTitle = $('#reviewErrorTitle');
  const errMsg = $('#reviewErrorMsg');
  if (errTitle) errTitle.textContent = title || 'Analysis Failed';
  if (errMsg) errMsg.textContent = message || 'An error occurred while fetching the pull request.';
  if (errCard) {
    errCard.hidden = false;
    errCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function hideReviewError() {
  const errCard = $('#reviewError');
  if (errCard) errCard.hidden = true;
}

function getRisk(score) {
  if (score <= 25) return { name: 'LOW RISK', className: 'low', color: '#3fb950', caption: 'Only minor observations. Safe to merge with standard peer approval.' };
  if (score <= 50) return { name: 'MEDIUM RISK', className: 'medium', color: '#d29922', caption: 'Moderate bug or maintainability risks. Resolve findings prior to release.' };
  if (score <= 75) return { name: 'HIGH RISK', className: 'high', color: '#f85149', caption: 'High-severity vulnerabilities detected. Fix critical findings before merge.' };
  return { name: 'CRITICAL RISK', className: 'critical', color: '#f85149', caption: 'Block merge immediately! Severe security flaws or fatal bugs detected.' };
}

function validatePRUrl(value) {
  if (!value) return false;
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
    return 'github/repository';
  }
}

function countBy(key, values = []) {
  return values.reduce((result, item) => {
    const k = (item[key] || 'quality').toLowerCase();
    result[k] = (result[k] || 0) + 1;
    return result;
  }, {});
}

let scoreAnimationId = null;

// Magic UI: Number Ticker with cubic ease-out
function animateNumberTicker(element, target, duration = 900) {
  if (!element) return;
  const start = parseInt(element.textContent, 10) || 0;
  if (start === target) return;
  const startTime = performance.now();

  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (target - start) * ease);
    element.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      element.textContent = target;
    }
  }
  requestAnimationFrame(step);
}

function animateScoreCounter(targetScore, color) {
  const scoreEl = $('#riskScore');
  if (!scoreEl) return;
  if (scoreAnimationId) cancelAnimationFrame(scoreAnimationId);

  const startScore = parseInt(scoreEl.textContent, 10) || 0;
  const duration = 1200;
  const startTime = performance.now();

  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(startScore + (targetScore - startScore) * ease);
    scoreEl.textContent = current;
    scoreEl.style.color = color;
    if (progress < 1) {
      scoreAnimationId = requestAnimationFrame(step);
    } else {
      scoreEl.textContent = targetScore;
      scoreAnimationId = null;
    }
  }
  scoreAnimationId = requestAnimationFrame(step);
}

function updateRiskScore(score) {
  const risk = getRisk(score);
  const scoreEl = $('#riskScore');
  const levelEl = $('#riskLevel');
  const captionEl = $('#riskCaption');
  const gaugeArc = $('#gaugeArc');
  const riskGauge = $('#riskGauge');

  if (scoreEl) {
    animateScoreCounter(score, risk.color);
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
  const headingEl = $('#issueHeadingCount');

  if (secEl) animateNumberTicker(secEl, types.security || 0);
  if (bugEl) animateNumberTicker(bugEl, types.bug || 0);
  if (qualEl) animateNumberTicker(qualEl, types.quality || 0);
  if (headingEl) headingEl.textContent = `${issues.length} Issues Flagged`;
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

  return `
    <article class="issue-card" data-type="${rawType}" data-severity="${rawSev}" style="animation-delay: ${index * 60}ms;">
      <div class="issue-card-header">
        <div class="issue-tags-row">
          <span class="issue-type-badge ${rawType}">${typeName}</span>
          <span class="issue-sev-badge ${rawSev}">${severityName}</span>
          <span class="issue-source-tag">${escapeHTML(sourceStr)}</span>
          <span class="issue-confidence-tag">Confidence: ${confidenceStr}</span>
        </div>
      </div>

      <div class="issue-card-body">
        <h4 class="issue-title">${escapeHTML(issue.message)}</h4>
        <div class="issue-location">
          <span class="file-icon">📄</span>
          <code>${escapeHTML(fileStr)}${lineStr}${cweStr}</code>
        </div>
        ${issue.explanation ? `<p class="issue-explanation">${escapeHTML(issue.explanation)}</p>` : ''}
        ${issue.impact ? `<div class="issue-impact-box"><strong>Impact:</strong> ${escapeHTML(issue.impact)}</div>` : ''}

        ${issue.fix ? `
          <div class="code-fix-block">
            <div class="code-fix-header">
              <span class="fix-label">RECOMMENDED REMEDIATION</span>
              <button class="btn-copy-fix" data-copy-issue="${issue.id || index}">
                Copy Fix
              </button>
            </div>
            <pre><code>${escapeHTML(issue.fix)}</code></pre>
            ${issue.fixExplanation ? `<div class="fix-tip">💡 ${escapeHTML(issue.fixExplanation)}</div>` : ''}
          </div>
        ` : ''}
      </div>
    </article>
  `;
}

function renderIssues() {
  const container = $('#issuesList');
  if (!container) return;

  const issues = currentReview ? currentReview.issues || [] : [];
  const sevFilter = $('#severityFilter') ? $('#severityFilter').value.toLowerCase() : 'all';
  const typeFilter = $('#typeFilter') ? $('#typeFilter').value.toLowerCase() : 'all';

  const filtered = issues.filter(issue => {
    const sevMatch = sevFilter === 'all' || (issue.severity || '').toLowerCase() === sevFilter;
    const typeMatch = typeFilter === 'all' || (issue.type || '').toLowerCase() === typeFilter;
    return sevMatch && typeMatch;
  });

  const headingEl = $('#issueHeadingCount');
  if (headingEl) {
    headingEl.textContent = `${filtered.length} of ${issues.length} Issues Flagged`;
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="no-issues-placeholder">
        <div class="check-icon">✓</div>
        <h3>No matching issues detected</h3>
        <p>No findings correspond to the selected severity and category filters.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map((issue, index) => createIssueCard(issue, index)).join('');
}

function updateSummary(issues = [], repo = '', prTitle = '') {
  const summaryEl = $('#aiSummary');
  if (!summaryEl) return;

  const count = issues.length;
  const criticals = issues.filter(i => (i.severity || '').toLowerCase() === 'high').length;
  const mediums = issues.filter(i => (i.severity || '').toLowerCase() === 'medium').length;

  if (count === 0) {
    summaryEl.innerHTML = `Analysis of <strong>${escapeHTML(prTitle)}</strong> identified zero security vulnerabilities or critical bugs. The changes follow standard coding practices and are considered safe for merge review.`;
  } else {
    summaryEl.innerHTML = `Automated analysis of <strong>${escapeHTML(prTitle)}</strong> identified <strong>${count} potential issues</strong> across security, runtime reliability, and maintainability. Found <strong>${criticals} high-severity</strong> and <strong>${mediums} medium-severity</strong> findings requiring inspection before merge integration.`;
  }
}

function renderCoverage(coverage) {
  if (!coverage) return;

  const analyzedCount = $('#coverageAnalyzedCount');
  const skippedCount = $('#coverageSkippedCount');
  const langCount = $('#coverageLangCount');
  const ratePill = $('#coverageRatePill');
  const langChips = $('#langChips');
  const toolChips = $('#toolChips');
  const manifestBody = $('#fileManifestBody');

  if (analyzedCount) animateNumberTicker(analyzedCount, coverage.analyzed_files ?? 0);
  if (skippedCount) animateNumberTicker(skippedCount, coverage.skipped_files ?? 0);
  if (langCount) animateNumberTicker(langCount, (coverage.languages_detected || []).length);

  if (ratePill) {
    const rate = coverage.coverage_percentage ?? 100;
    ratePill.textContent = `${rate}% Analyzed`;
    ratePill.className = `coverage-rate-pill ${rate === 100 ? 'full' : 'partial'}`;
  }

  if (langChips) {
    const langs = coverage.languages_detected || [];
    langChips.innerHTML = langs.length
      ? langs.map(l => `<span class="lang-chip">${escapeHTML(l)}</span>`).join('')
      : '<span class="lang-chip">Generic / Diff</span>';
  }

  if (toolChips) {
    const tools = coverage.tools_engaged || ['Bandit v1.9.4', 'Pyflakes v4.0', 'AST Analysis', 'AI Reviewer'];
    toolChips.innerHTML = tools.map(t => `<span class="tool-chip">${escapeHTML(t)}</span>`).join('');
  }

  if (manifestBody) {
    const breakdown = coverage.file_breakdown || [];
    if (breakdown.length === 0) {
      manifestBody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:12px;color:var(--text-muted);">No modified source files recorded in pull request.</td></tr>';
    } else {
      manifestBody.innerHTML = breakdown.map(f => {
        const isAnalyzed = f.status === 'Analyzed';
        const methodsStr = Array.isArray(f.methods) ? f.methods.join(', ') : (f.methods || 'Static Analyzers');
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
  const repo = reviewData.repo || 'github/repository';
  const prTitle = reviewData.prTitle || 'GitHub Pull Request';
  const issues = reviewData.issues || [];
  const score = Number(reviewData.riskScore) || 0;

  updateRiskScore(score);
  updateMetrics(issues);
  updateSummary(issues, repo, prTitle);
  renderCoverage(reviewData.coverage);

  // Magic UI Confetti on Low Risk / Clean merge safety
  if (score <= 35) {
    window.setTimeout(() => fireMagicConfetti(), 500);
  }

  const titleEl = $('#resultsHeadingTitle');
  if (titleEl) titleEl.textContent = prTitle;

  renderIssues();

  const resultsSection = $('#results');
  if (resultsSection) {
    resultsSection.hidden = false;
    resultsSection.style.opacity = '1';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Perform real API review
async function performReview(url) {
  const thisSequence = ++reviewSequence;
  hideReviewError();

  const loading = $('#loadingState');
  const results = $('#results');
  const readyPrompt = $('#readyPrompt');
  const submitBtn = $('#reviewForm button');
  const scannerSection = $('#analyzerSection');

  if (readyPrompt) readyPrompt.hidden = true;
  if (scannerSection) scannerSection.classList.add('scanning-active');
  if (loading) loading.hidden = false;
  if (results && !results.hidden) results.style.opacity = '0.35';

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-sparkle">◌</span> Scanning…';
  }

  // Dynamic rotating inspection stages
  const scanStages = [
    { title: 'Fetching GitHub Diff & Patch Metadata…', sub: 'Streaming modified source files and parsing unified diffs.' },
    { title: 'Executing Static Vulnerability Analyzers…', sub: 'Running Bandit security rules and AST code smell detectors.' },
    { title: 'Evaluating Cyclomatic Complexity & Quality…', sub: 'Profiling code maintainability, docstrings, and dead branches.' },
    { title: 'Consulting Contextual AI Reviewer…', sub: 'Synthesizing line-by-line remediation patches and explanations.' },
    { title: 'Computing Overall PR Risk Score…', sub: 'Aggregating security weights, bug metrics, and test coverage.' }
  ];
  let stageIdx = 0;
  const loadingTitle = $('#loadingState .loading-title');
  const loadingSubtitle = $('#loadingState .loading-subtitle');
  const stageTimer = setInterval(() => {
    stageIdx = (stageIdx + 1) % scanStages.length;
    if (loadingTitle) loadingTitle.textContent = scanStages[stageIdx].title;
    if (loadingSubtitle) loadingSubtitle.textContent = scanStages[stageIdx].sub;
  }, 500);

  try {
    const response = await fetch(`${API_BASE}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pr_url: url })
    });

    if (!response.ok) {
      let errDetail = `Server returned HTTP ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errDetail = errJson.detail;
      } catch {}
      throw new Error(errDetail);
    }

    const data = await response.json();
    if (thisSequence !== reviewSequence) return;

    renderReview({
      riskScore: data.riskScore,
      repo: data.repo || repoFromURL(url),
      prTitle: data.prTitle || 'Pull Request Analysis',
      author: data.author || 'Contributor',
      issues: data.issues || [],
      coverage: data.coverage
    });

    const badge = $('#dataSourceBadge');
    if (badge) badge.textContent = 'Live GitHub Scan';

    showToast(`Scan complete: ${data.issues ? data.issues.length : 0} findings recorded (Risk: ${data.riskScore}/100)`);

  } catch (err) {
    console.error('API review failed:', err);
    if (thisSequence !== reviewSequence) return;

    // Show genuine error alert without falling back to fake review
    if (!currentReview) {
      if (results) results.hidden = true;
      if (readyPrompt) readyPrompt.hidden = false;
    }
    showReviewError('Pull Request Analysis Failed', err.message);
    showToast(`Analysis failed: ${err.message}`);

  } finally {
    clearInterval(stageTimer);
    if (scannerSection) scannerSection.classList.remove('scanning-active');
    if (thisSequence === reviewSequence) {
      if (loading) loading.hidden = true;
      if (results && !results.hidden) results.style.opacity = '1';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="btn-sparkle">✦</span> Run Analysis <span class="btn-arrow">→</span>';
      }
    }
  }
}

// Check backend status
async function checkSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (res.ok) {
      const data = await res.json();
      const dot = $('#liveStatusDot');
      if (dot) dot.style.background = '#3fb950';
      const aiBadge = $('#aiModelBadge');
      if (aiBadge) aiBadge.textContent = data.ai_engine;
      const dataBadge = $('#dataSourceBadge');
      if (dataBadge) dataBadge.textContent = 'Backend Online';
    }
  } catch {
    const dot = $('#liveStatusDot');
    if (dot) dot.style.background = '#d29922';
    const dataBadge = $('#dataSourceBadge');
    if (dataBadge) dataBadge.textContent = 'Backend Offline';
  }
}

// Setup Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Do NOT render fake reviews on load - start clean in ready state
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

  // Dismiss Error Alert
  const dismissBtn = $('#dismissErrorBtn');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', hideReviewError);
  }


  // Export / Print Report Button
  const exportBtn = $('#exportReportBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      if (!currentReview) {
        showToast('Please analyze a pull request first before exporting.');
        return;
      }
      window.print();
    });
  }

  // Clear Input Error on typing
  const prInput = $('#prUrl');
  if (prInput) {
    prInput.addEventListener('input', () => {
      const error = $('#urlError');
      if (error) error.hidden = true;
      prInput.removeAttribute('aria-invalid');
    });
  }

  // Severity & Category Filters
  const sevFilter = $('#severityFilter');
  if (sevFilter) sevFilter.addEventListener('change', renderIssues);
  const typeFilter = $('#typeFilter');
  if (typeFilter) typeFilter.addEventListener('change', renderIssues);

  // Copy Code Fix Button with Feedback Pulse
  const listEl = $('#issuesList');
  if (listEl) {
    listEl.addEventListener('click', async event => {
      const button = event.target.closest('[data-copy-issue]');
      if (!button) return;
      const issue = (currentReview && currentReview.issues ? currentReview.issues : []).find(item => String(item.id) === String(button.dataset.copyIssue));
      if (!issue || !issue.fix) return;
      try {
        await navigator.clipboard.writeText(issue.fix);
        button.classList.add('copied');
        button.innerHTML = '<span>✓</span> Copied!';
        showToast('Suggested fix copied to clipboard.');
        window.setTimeout(() => { 
          button.classList.remove('copied');
          button.textContent = 'Copy Fix'; 
        }, 1800);
      } catch {
        showToast('Clipboard access unavailable.');
      }
    });
  }

  // Navigation Links Handling
  $$('.nav-link').forEach(link => {
    link.addEventListener('click', event => {
      const targetId = link.getAttribute('href');
      if (targetId && targetId !== '#analyzerSection') {
        if (!currentReview) {
          event.preventDefault();
          showToast('Please run an analysis first to view risk metrics.');
          const input = $('#prUrl');
          if (input) input.focus();
          return;
        }
      }
      $$('.nav-link').forEach(item => item.classList.toggle('active', item === link));
    });
  });

  // Magic UI Avatar Circles Interactive Team Widget
  const teamWidget = $('#teamWidget');
  const teamPopover = $('#teamPopover');
  if (teamWidget && teamPopover) {
    teamWidget.addEventListener('click', (e) => {
      e.stopPropagation();
      teamPopover.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!teamWidget.contains(e.target)) {
        teamPopover.classList.remove('open');
      }
    });

    $$('.avatar-circle-item').forEach(circle => {
      circle.addEventListener('mouseenter', () => {
        const idx = circle.dataset.memberIdx;
        $$('.member-mini-card').forEach(card => {
          if (idx === 'all' || card.dataset.cardIdx === idx) {
            card.classList.add('active');
          } else {
            card.classList.remove('active');
          }
        });
      });
      circle.addEventListener('mouseleave', () => {
        $$('.member-mini-card').forEach((card, i) => {
          card.classList.toggle('active', i === 0);
        });
      });
    });
  }

  // =========================================================================
  // Magic UI Components Suite Runtime
  // =========================================================================

  // 1. Magic UI: Scroll Progress
  function initScrollProgress() {
    const bar = $('#scrollProgress');
    if (!bar) return;
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const progress = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
      bar.style.width = `${progress}%`;
    }, { passive: true });
  }

  // 2. Magic UI: Magic Card Glare / Mouse Spotlight
  function initMagicCardSpotlight() {
    const cards = $$('.kpi-card, .ai-summary-card, .coverage-card');
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    });
  }

  // Initialize Magic UI Interactive Suite
  initScrollProgress();
  initMagicCardSpotlight();
});

// Magic UI: Lightweight Canvas Confetti
function fireMagicConfetti() {
  const canvas = $('#confettiCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const colors = ['#2f81f7', '#3fb950', '#a855f7', '#58a6ff', '#e3b341', '#f0883e'];
  const count = 90;

  for (let i = 0; i < count; i++) {
    particles.push({
      x: window.innerWidth * (0.35 + Math.random() * 0.3),
      y: window.innerHeight * 0.45,
      vx: (Math.random() - 0.5) * 16,
      vy: (Math.random() - 0.9) * 18,
      size: Math.random() * 7 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      rotationSpeed: (Math.random() - 0.5) * 12,
      opacity: 1,
      gravity: 0.35
    });
  }

  let animationFrame;
  const startTime = performance.now();

  function render(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = 0;

    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += p.gravity;
      p.vx *= 0.98;
      p.rotation += p.rotationSpeed;
      p.opacity = Math.max(0, 1 - (now - startTime) / 2800);

      if (p.opacity > 0 && p.y < canvas.height + 20) {
        alive++;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.65);
        ctx.restore();
      }
    }

    if (alive > 0) {
      animationFrame = requestAnimationFrame(render);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      cancelAnimationFrame(animationFrame);
    }
  }

  animationFrame = requestAnimationFrame(render);
}
