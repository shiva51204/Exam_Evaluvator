const API_BASE_RES = "http://localhost:8080/api";

// ── Load data from session storage
let allResults = [];
let summary = {};
let jobId = "";
let examTitle = "Exam";
let activeFilter = "all";
let searchQuery = "";
let sortMode = "score-desc";

try {
  allResults = JSON.parse(sessionStorage.getItem("examResults") || "[]");
  summary = JSON.parse(sessionStorage.getItem("examSummary") || "{}");
  jobId = sessionStorage.getItem("jobId") || "";
  examTitle = sessionStorage.getItem("examTitle") || "Exam";
} catch (e) {
  console.error("Failed to load session data", e);
}

if (!allResults.length) {
  document.querySelector(".summary-title").textContent = "No Results";
  document.getElementById("results-tbody").innerHTML = `
    <tr><td colspan="8" style="text-align:center;padding:60px;color:var(--text-3)">
      No grading results found. <a href="index.html" style="color:var(--amber)">Start a new exam →</a>
    </td></tr>
  `;
} else {
  initResults();
}

function initResults() {
  // Summary banner
  document.getElementById("summary-title").textContent = examTitle;
  document.getElementById("m-avg").textContent = (summary.class_average ?? calcAvg()) + "%";
  document.getElementById("m-high").textContent = (summary.highest ?? calcHigh()) + "%";
  document.getElementById("m-low").textContent = (summary.lowest ?? calcLow()) + "%";
  document.getElementById("m-flag").textContent = summary.flagged ?? allResults.filter(r => r.needs_review).length;

  const tags = document.getElementById("summary-tags");
  tags.innerHTML = `
    <span class="tag amber">${summary.exam_type || "Mixed"}</span>
    <span class="tag">${allResults.length} Students</span>
    <span class="tag">${summary.processed ?? allResults.filter(r => r.ocr_success).length} Processed</span>
  `;

  renderDistribution();
  renderTable();
  setupControls();
  setupDownloads();
}

// ── Stats helpers
function calcAvg() {
  const v = allResults.filter(r => r.ocr_success);
  if (!v.length) return "—";
  return (v.reduce((s, r) => s + r.percentage, 0) / v.length).toFixed(1);
}

function calcHigh() {
  const v = allResults.filter(r => r.ocr_success);
  if (!v.length) return "—";
  return Math.max(...v.map(r => r.percentage)).toFixed(1);
}

function calcLow() {
  const v = allResults.filter(r => r.ocr_success);
  if (!v.length) return "—";
  return Math.min(...v.map(r => r.percentage)).toFixed(1);
}

// ── Distribution Chart
function renderDistribution() {
  const dist = { A: 0, B: 0, C: 0, D: 0, F: 0 };
  allResults.forEach(r => {
    if (r.grade && dist[r.grade] !== undefined) dist[r.grade]++;
  });

  const max = Math.max(...Object.values(dist), 1);
  const chart = document.getElementById("dist-chart");
  const colors = { A: "#4ade80", B: "#f5a623", C: "#60a5fa", D: "#fbbf24", F: "#f87171" };

  chart.innerHTML = Object.entries(dist).map(([grade, count]) => {
    const heightPct = (count / max) * 64;
    return `
      <div class="dist-bar-wrap">
        <div class="dist-bar" data-count="${count} students"
             style="height:${Math.max(heightPct, 4)}px; background:${colors[grade]}; opacity:${count > 0 ? 1 : 0.2}">
        </div>
        <div class="dist-label" style="color:${colors[grade]}">${grade}</div>
        <div class="dist-count">${count}</div>
      </div>
    `;
  }).join("");
}

// ── Table Rendering
function getFilteredSorted() {
  let results = [...allResults];

  // Filter
  if (activeFilter === "flagged") results = results.filter(r => r.needs_review);
  else if (activeFilter === "pass") results = results.filter(r => r.percentage >= 45 && r.ocr_success);
  else if (activeFilter === "fail") results = results.filter(r => r.percentage < 45 || !r.ocr_success);

  // Search
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    results = results.filter(r =>
      (r.student_name || "").toLowerCase().includes(q) ||
      (r.filename || "").toLowerCase().includes(q)
    );
  }

  // Sort
  if (sortMode === "score-desc") results.sort((a, b) => b.percentage - a.percentage);
  else if (sortMode === "score-asc") results.sort((a, b) => a.percentage - b.percentage);
  else if (sortMode === "name") results.sort((a, b) => (a.student_name || "").localeCompare(b.student_name || ""));
  else if (sortMode === "flagged") results.sort((a, b) => (b.needs_review ? 1 : 0) - (a.needs_review ? 1 : 0));

  return results;
}

function renderTable() {
  const results = getFilteredSorted();
  const tbody = document.getElementById("results-tbody");
  const empty = document.getElementById("empty-state");

  if (!results.length) {
    tbody.innerHTML = "";
    empty.hidden = false;
    return;
  }

  empty.hidden = true;
  const gradeColor = { A: "#4ade80", B: "#f5a623", C: "#60a5fa", D: "#fbbf24", F: "#f87171" };

  tbody.innerHTML = results.map((r, i) => {
    const pctColor = r.percentage >= 75 ? "#4ade80" : r.percentage >= 45 ? "#f5a623" : "#f87171";
    const statusHtml = !r.ocr_success
      ? `<span class="status-badge status-fail">OCR Failed</span>`
      : r.needs_review
      ? `<span class="status-badge status-flag">⚠ Review</span>`
      : `<span class="status-badge status-ok">✓ OK</span>`;

    const origIdx = allResults.indexOf(r);

    return `
      <tr class="${r.needs_review ? 'flagged' : ''}">
        <td style="color:var(--text-3);font-size:11px">${i + 1}</td>
        <td>
          <div class="student-name-cell">${r.student_name || "—"}</div>
          <div style="font-size:10px;color:var(--text-3);margin-top:2px">${r.filename || ""}</div>
        </td>
        <td class="score-cell">${r.ocr_success ? `${r.total_score}/${r.max_score}` : "—"}</td>
        <td class="pct-cell" style="color:${pctColor}">${r.ocr_success ? r.percentage.toFixed(1) + "%" : "N/A"}</td>
        <td><span class="grade-pill grade-${r.grade}">${r.grade}</span></td>
        <td>${statusHtml}</td>
        <td style="color:var(--text-3);font-size:11px">${r.processing_time_seconds?.toFixed(1) || "—"}s</td>
        <td><button class="btn-detail" onclick="openDrawer(${origIdx})">View →</button></td>
      </tr>
    `;
  }).join("");
}

// ── Controls
function setupControls() {
  document.getElementById("search-input").addEventListener("input", (e) => {
    searchQuery = e.target.value;
    renderTable();
  });

  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.filter;
      renderTable();
    });
  });

  document.getElementById("sort-select").addEventListener("change", (e) => {
    sortMode = e.target.value;
    renderTable();
  });
}

// ── Downloads
function setupDownloads() {
  document.getElementById("btn-csv").addEventListener("click", () => {
    if (!jobId) return alert("Job ID not found. Please re-run grading.");
    window.open(`${API_BASE_RES}/download/csv/${encodeURIComponent(jobId)}`);
  });

  document.getElementById("btn-flagged-csv").addEventListener("click", () => {
    if (!jobId) return alert("Job ID not found.");
    window.open(`${API_BASE_RES}/download/flagged/${encodeURIComponent(jobId)}`);
  });
}

// ── Detail Drawer
window.openDrawer = function (idx) {
  const r = allResults[idx];
  if (!r) return;

  document.getElementById("drawer-name").textContent = r.student_name || "Unknown";
  document.getElementById("drawer-meta").textContent = `${r.filename} · ${r.processing_time_seconds?.toFixed(1)}s · ${r.ocr_success ? "OCR OK" : "OCR Failed"}`;
  document.getElementById("drawer-score-big").textContent = r.ocr_success ? `${r.total_score}/${r.max_score}` : "—/—";

  const badge = document.getElementById("drawer-grade-badge");
  badge.textContent = r.grade;
  badge.className = `grade-badge grade-${r.grade}`;
  badge.style.background = "";
  const colors = { A: "rgba(74,222,128,0.15)", B: "rgba(245,166,35,0.15)", C: "rgba(96,165,250,0.15)", D: "rgba(251,191,36,0.1)", F: "rgba(248,113,113,0.15)" };
  badge.style.background = colors[r.grade] || "var(--bg-4)";

  const qContainer = document.getElementById("drawer-questions");

  if (!r.question_results || r.question_results.length === 0) {
    qContainer.innerHTML = `<div style="color:var(--text-3);font-size:12px;padding:20px 0">${r.review_reason || r.error || "No question details available."}</div>`;
  } else {
    qContainer.innerHTML = r.question_results.map(q => {
      const cls = q.correct ? "correct" : q.marks_awarded > 0 ? "partial" : "incorrect";
      return `
        <div class="q-card ${cls} ${q.needs_review ? "flagged" : ""}">
          <div class="q-header">
            <span class="q-num">Question ${q.q_no} · ${q.question_type || ""}</span>
            <span class="q-score">${q.marks_awarded}/${q.marks_possible}</span>
          </div>
          <div class="q-row">
            <span class="q-label">Student</span>
            <span class="q-value">${q.student_answer || "(blank)"}</span>
          </div>
          <div class="q-row">
            <span class="q-label">Expected</span>
            <span class="q-value">${q.correct_answer || "—"}</span>
          </div>
          ${q.confidence < 80 ? `<div class="q-row"><span class="q-label">Confidence</span><span class="q-value" style="color:var(--amber)">${q.confidence}%</span></div>` : ""}
          ${q.feedback ? `<div class="q-feedback">${q.feedback}</div>` : ""}
          ${q.needs_review ? `<div class="review-flag">⚠ Needs Manual Review</div>` : ""}
        </div>
      `;
    }).join("");
  }

  document.getElementById("detail-drawer").hidden = false;
  document.body.style.overflow = "hidden";
};

function closeDrawer() {
  document.getElementById("detail-drawer").hidden = true;
  document.body.style.overflow = "";
}

document.getElementById("drawer-close").addEventListener("click", closeDrawer);
document.getElementById("drawer-backdrop").addEventListener("click", closeDrawer);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDrawer();
});
