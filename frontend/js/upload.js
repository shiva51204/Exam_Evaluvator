const API_BASE = "http://localhost:8080/api";

// ── API health check
async function checkApiStatus() {
  const el = document.getElementById("api-status");
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      el.textContent = "● API Ready";
      el.className = "nav-status ok";
    } else throw new Error();
  } catch {
    el.textContent = "● API Offline";
    el.className = "nav-status err";
  }
}

checkApiStatus();

// ── Drop Zone Setup
function setupDropZone(dropId, inputId, multi = false) {
  const zone = document.getElementById(dropId);
  const input = document.getElementById(inputId);

  if (!zone || !input) return;

  zone.addEventListener("click", () => input.click());

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });

  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));

  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const files = [...e.dataTransfer.files].filter(f => f.type === "application/pdf");
    if (files.length === 0) return;

    // Assign to the input
    const dt = new DataTransfer();
    files.forEach(f => dt.items.add(f));
    input.files = dt.files;
    input.dispatchEvent(new Event("change"));
  });

  input.addEventListener("change", () => {
    if (multi) {
      renderSheetsList(input.files);
    } else {
      renderKeyPreview(input.files[0]);
    }
  });
}

function renderKeyPreview(file) {
  const preview = document.getElementById("key-preview");
  const zone = document.getElementById("key-drop");
  if (!file) return;

  zone.classList.add("has-file");
  preview.innerHTML = `
    <div class="file-chip">
      <span class="chip-icon">📄</span>
      <span>${file.name}</span>
      <span style="color:var(--text-3)">${(file.size / 1024 / 1024).toFixed(1)}MB</span>
      <span class="chip-remove" onclick="clearKeyFile()">×</span>
    </div>
  `;
}

window.clearKeyFile = function () {
  const input = document.getElementById("answer-key-input");
  const preview = document.getElementById("key-preview");
  const zone = document.getElementById("key-drop");
  input.value = "";
  preview.innerHTML = "";
  zone.classList.remove("has-file");
};

function renderSheetsList(files) {
  const list = document.getElementById("sheets-list");
  const zone = document.getElementById("sheets-drop");

  if (!files || files.length === 0) {
    list.innerHTML = "";
    zone.classList.remove("has-file");
    return;
  }

  zone.classList.add("has-file");

  const fileArr = [...files];
  const showing = fileArr.slice(0, 8);
  const extra = fileArr.length - showing.length;

  list.innerHTML = showing.map(f => `
    <div class="sheet-chip">
      <span>📄</span>
      <span>${f.name.length > 24 ? f.name.slice(0, 22) + '…' : f.name}</span>
    </div>
  `).join("");

  if (extra > 0) {
    list.innerHTML += `<div class="sheet-chip"><span class="sheets-count-badge">+${extra} more</span></div>`;
  }
}

setupDropZone("key-drop", "answer-key-input", false);
setupDropZone("sheets-drop", "student-sheets-input", true);

// ── Form Submit
document.getElementById("grade-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const form = e.target;
  const keyInput = document.getElementById("answer-key-input");
  const sheetsInput = document.getElementById("student-sheets-input");
  const totalMarks = document.getElementById("total-marks").value;
  const examTitle = document.getElementById("exam-title").value || "Exam";

  if (!keyInput.files[0]) return alert("Please upload an answer key PDF.");
  if (!sheetsInput.files.length) return alert("Please upload at least one student answer sheet.");
  if (!totalMarks || totalMarks <= 0) return alert("Please enter total marks.");

  const formData = new FormData();
  formData.append("answer_key", keyInput.files[0]);
  for (const file of sheetsInput.files) {
    formData.append("student_sheets", file);
  }
  formData.append("total_marks", totalMarks);
  formData.append("exam_title", examTitle);

  // Disable submit
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;

  // Show progress overlay
  document.getElementById("progress-overlay").hidden = false;
  window._gradingResults = [];
  window._jobId = null;
  window._examTitle = examTitle;

  startGrading(formData, sheetsInput.files.length);
});
