const API_BASE_PROG = "http://localhost:8080/api";

function addLog(msg, type = "") {
  const log = document.getElementById("feed-log");
  const now = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.innerHTML = `<span class="log-time">${now}</span><span class="log-msg ${type}">${msg}</span>`;
  log.appendChild(entry);
  log.scrollTop = log.scrollHeight;
}

function updateProgressStats(done, total, flagged, results) {
  document.getElementById("stat-done").textContent = done;
  document.getElementById("stat-total").textContent = total;
  document.getElementById("stat-flagged").textContent = flagged;

  const valid = results.filter(r => r.ocr_success);
  if (valid.length > 0) {
    const avg = valid.reduce((s, r) => s + r.percentage, 0) / valid.length;
    document.getElementById("stat-avg").textContent = avg.toFixed(1) + "%";
  }

  const pct = total > 0 ? (done / total) * 100 : 0;
  document.getElementById("progress-bar").style.width = pct + "%";
  document.getElementById("progress-meta").textContent = `${done} of ${total} students processed`;
}

function showRubricInfo(rubric) {
  const box = document.getElementById("rubric-info");
  box.classList.add("visible");
  box.innerHTML = `
    <div class="rubric-row"><span class="rubric-key">Exam Type</span><span class="rubric-val">${rubric.exam_type || "—"}</span></div>
    <div class="rubric-row"><span class="rubric-key">Questions</span><span class="rubric-val">${rubric.total_questions || rubric.questions?.length || "—"}</span></div>
    <div class="rubric-row"><span class="rubric-key">Total Marks</span><span class="rubric-val">${rubric.total_marks || "—"}</span></div>
  `;
}

async function startGrading(formData, totalStudents) {
  let done = 0;
  let flagged = 0;
  const allResults = [];

  document.getElementById("stat-total").textContent = totalStudents;
  addLog(`Starting grading for ${totalStudents} student(s)...`, "info");

  try {
    const response = await fetch(`${API_BASE_PROG}/grade/stream`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      addLog(`Error: ${err.detail || "Request failed"}`, "error");
      document.getElementById("submit-btn").disabled = false;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done: streamDone, value } = await reader.read();
      if (streamDone) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep incomplete

      for (const line of lines) {
        if (!line.trim().startsWith("data:")) continue;
        const raw = line.replace(/^data:\s*/, "").trim();
        if (!raw) continue;

        let event;
        try { event = JSON.parse(raw); }
        catch { continue; }

        handleSSEEvent(event, allResults, () => {
          done++;
          if (event.result?.needs_review) flagged++;
          updateProgressStats(done, totalStudents, flagged, allResults);
        });
      }
    }

  } catch (err) {
    addLog(`Connection error: ${err.message}`, "error");
    document.getElementById("submit-btn").disabled = false;
  }
}

function handleSSEEvent(event, allResults, onProgress) {
  const { type: _t, event: evtType } = event;
  const evt = evtType || event.event;

  if (evt === "rubric") {
    addLog(`Rubric detected: ${event.rubric?.exam_type} — ${event.rubric?.total_questions} questions`, "info");
    showRubricInfo(event.rubric);
    return;
  }

  if (evt === "start") {
    addLog(`Processing: ${event.student_name}...`);
    return;
  }

  if (evt === "progress") {
    if (event.result) allResults.push(event.result);
    const icon = event.result?.needs_review ? "⚠" : "✓";
    const cls = event.result?.needs_review ? "error" : "success";
    addLog(`${icon} ${event.student_name} — ${event.message}`, cls);
    onProgress();
    return;
  }

  if (evt === "error") {
    if (event.result) allResults.push(event.result);
    addLog(`✗ ${event.student_name} — ${event.message}`, "error");
    onProgress();
    return;
  }

  if (evt === "done") {
    window._gradingResults = event.results || allResults;
    window._jobId = event.job_id;

    const s = event.summary;
    addLog(`✓ Grading complete! Avg: ${s?.class_average}% | High: ${s?.highest}% | Low: ${s?.lowest}%`, "success");

    // Redirect to results after a short delay
    setTimeout(() => {
      sessionStorage.setItem("examResults", JSON.stringify(event.results || allResults));
      sessionStorage.setItem("examSummary", JSON.stringify(event.summary || {}));
      sessionStorage.setItem("jobId", event.job_id || "");
      sessionStorage.setItem("examTitle", window._examTitle || "Exam");
      window.location.href = "results.html";
    }, 1200);
  }
}
