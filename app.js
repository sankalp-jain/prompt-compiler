let currentData = {};
let hasGenerated = false;

const generateBtn  = document.getElementById("generate-btn");
const useCaseEl    = document.getElementById("use-case");
const modelSelect  = document.getElementById("model-select");
const outputEl     = document.getElementById("output");
const errorEl      = document.getElementById("error");
const hintEl       = document.getElementById("hint");

// ── Render ────────────────────────────────────────────────────────────────────

function renderResult(data) {
  currentData = data;
  document.getElementById("system-prompt-body").innerHTML  = marked.parse(data.system_prompt);
  document.getElementById("user-prompt-body").textContent  = data.user_prompt;
  document.getElementById("reviewer-prompt-body").textContent = data.reviewer_prompt;
  outputEl.classList.remove("hidden");
  outputEl.classList.add("flex");
}

// ── Copy buttons ──────────────────────────────────────────────────────────────

document.querySelectorAll(".btn-copy").forEach(btn => {
  btn.addEventListener("click", () => {
    const text = currentData[btn.dataset.key];
    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
      const isDark = btn.dataset.variant === "dark";
      btn.textContent = "Copied ✓";
      btn.classList.add(isDark ? "!text-[#4ade80]" : "!text-[#16A34A]",
                        isDark ? "!border-[#4ade80]" : "!border-[#16A34A]");
      setTimeout(() => {
        btn.textContent = "Copy";
        btn.classList.remove("!text-[#4ade80]", "!border-[#4ade80]",
                             "!text-[#16A34A]", "!border-[#16A34A]");
      }, 2000);
    });
  });
});

// ── History ───────────────────────────────────────────────────────────────────

function getHistory() {
  return JSON.parse(sessionStorage.getItem("ph") || "[]");
}

function pushHistory(entry) {
  const h = getHistory();
  h.unshift(entry);
  sessionStorage.setItem("ph", JSON.stringify(h.slice(0, 10)));
}

function renderHistory() {
  const h       = getHistory();
  const section = document.getElementById("history-section");
  const list    = document.getElementById("history-list");

  if (!h.length) {
    section.classList.add("hidden");
    section.classList.remove("flex");
    return;
  }

  section.classList.remove("hidden");
  section.classList.add("flex");
  list.innerHTML = "";

  h.forEach(entry => {
    const el = document.createElement("div");
    el.className   = "px-3.5 py-2.5 bg-white border border-[#E4E4E2] rounded-lg text-[13px] " +
                     "text-[#8C8C88] hover:text-[#1A1A18] hover:border-[#BBBBB8] cursor-pointer " +
                     "truncate transition-colors";
    el.textContent = entry.use_case;
    el.addEventListener("click", () => {
      useCaseEl.value = entry.use_case;
      renderResult(entry);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    list.appendChild(el);
  });
}

document.getElementById("clear-btn").addEventListener("click", () => {
  sessionStorage.removeItem("ph");
  renderHistory();
});

// ── Generate ──────────────────────────────────────────────────────────────────

generateBtn.addEventListener("click", async () => {
  const useCase = useCaseEl.value.trim();
  if (!useCase) return;

  generateBtn.disabled    = true;
  generateBtn.textContent = "Generating…";
  errorEl.classList.add("hidden");

  try {
    const res  = await fetch("http://localhost:8000/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ use_case: useCase, model: modelSelect.value }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        res.status === 422
          ? "Enter at least two words describing what you want to build or solve."
          : "Something went wrong. Please try again."
      );
    }

    if (!hasGenerated) {
      hintEl.classList.add("hidden");
      hasGenerated = true;
    }

    renderResult(data);
    pushHistory({ use_case: useCase, ...data });
    renderHistory();

  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    generateBtn.disabled    = false;
    generateBtn.textContent = "Generate Prompt";
  }
});

// ── Models ────────────────────────────────────────────────────────────────────

async function loadModels() {
  try {
    const res    = await fetch("http://localhost:8000/models");
    const models = await res.json();
    models.forEach(({ id, label }) => {
      const opt   = document.createElement("option");
      opt.value   = id;
      opt.textContent = label;
      if (id === "gpt-4o-mini") opt.selected = true;
      modelSelect.appendChild(opt);
    });
  } catch {
    // fallback: backend unreachable, leave select empty
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

loadModels();
renderHistory();
