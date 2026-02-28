const API_BASE = window.ENV_API_URL || "http://localhost:8000";

let currentData = {};
let hasGenerated = false;
let iterationCount = 0;
let currentHistoryId = null;
let apiKey = sessionStorage.getItem("oai_key") || "";
let refinementHistory = [];
let currentWeaknesses = [];

const generateBtn = document.getElementById("generate-btn");
const useCaseEl = document.getElementById("use-case");
const modelSelect = document.getElementById("model-select");
const outputEl = document.getElementById("output");
const errorEl = document.getElementById("error");
const hintEl = document.getElementById("hint");
const refineSectionEl = document.getElementById("refine-section");
const refineBtn = document.getElementById("refine-btn");
const refineInputEl = document.getElementById("refine-input");
const refineErrorEl = document.getElementById("refine-error");
const iterationBadge = document.getElementById("iteration-badge");


// ── API Key ───────────────────────────────────────────────────────────────────

function renderApiKeyState() {
  const unset = document.getElementById("apikey-unset");
  const set = document.getElementById("apikey-set");
  const preview = document.getElementById("apikey-preview");
  if (apiKey) {
    unset.classList.add("hidden");
    set.classList.remove("hidden");
    set.classList.add("flex");
    preview.textContent = apiKey.slice(0, 7) + "..." + apiKey.slice(-4);
  } else {
    unset.classList.remove("hidden");
    set.classList.add("hidden");
    set.classList.remove("flex");
  }
}

document.getElementById("apikey-save-btn").addEventListener("click", () => {
  const val = document.getElementById("apikey-input").value.trim();
  if (!val) return;
  apiKey = val;
  sessionStorage.setItem("oai_key", apiKey);
  document.getElementById("apikey-input").value = "";
  renderApiKeyState();
});

document.getElementById("apikey-input").addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("apikey-save-btn").click();
});

document.getElementById("apikey-clear-btn").addEventListener("click", () => {
  apiKey = "";
  sessionStorage.removeItem("oai_key");
  renderApiKeyState();
});

// ── Render ────────────────────────────────────────────────────────────────────

function renderResult(data) {
  currentData = data;
  document.getElementById("system-prompt-body").innerHTML = DOMPurify.sanitize(marked.parse(data.system_prompt));
  document.getElementById("user-prompt-body").textContent = data.user_prompt;
  document.getElementById("reviewer-prompt-body").textContent = data.reviewer_prompt;
  outputEl.classList.remove("hidden");
  outputEl.classList.add("flex");
  refineSectionEl.classList.remove("hidden");
  refineSectionEl.classList.add("flex");
}

// ── Suggestions ───────────────────────────────────────────────────────────────

function showSuggestionsLoading() {
  const section = document.getElementById("suggestions-section");
  const list = document.getElementById("suggestions-list");
  list.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    const row = document.createElement("div");
    row.className = "h-[42px] bg-white border border-[#E4E4E2] rounded-lg animate-pulse";
    list.appendChild(row);
  }
  section.classList.remove("hidden");
  section.classList.add("flex");
}

function hideSuggestions() {
  const section = document.getElementById("suggestions-section");
  section.classList.add("hidden");
  section.classList.remove("flex");
}

function renderSuggestions(suggestions) {
  const list = document.getElementById("suggestions-list");
  list.innerHTML = "";
  suggestions.forEach(text => {
    const row = document.createElement("div");
    row.className = "flex items-start gap-3 px-3.5 py-2.5 bg-white border border-[#E4E4E2] rounded-lg";

    const span = document.createElement("span");
    span.className = "flex-1 text-[13px] text-[#52524E] leading-relaxed";
    span.textContent = text;

    const btn = document.createElement("button");
    btn.className = "shrink-0 text-[11px] font-medium text-[#8C8C88] border border-[#E4E4E2] " +
      "rounded px-2 py-1 hover:text-[#1A1A18] hover:border-[#BBBBB8] transition-colors";
    btn.textContent = "Use";
    btn.addEventListener("click", () => {
      refineInputEl.value = text;
      refineInputEl.focus();
      refineInputEl.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    row.appendChild(span);
    row.appendChild(btn);
    list.appendChild(row);
  });
}

async function fetchSuggestions(systemPrompt, userPrompt, weaknesses) {
  showSuggestionsLoading();
  try {
    const res = await fetch(`${API_BASE}/suggestions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system_prompt: systemPrompt, user_prompt: userPrompt, api_key: apiKey, weaknesses: weaknesses || [] }),
    });
    if (!res.ok) { hideSuggestions(); return; }
    const data = await res.json();
    renderSuggestions(data.suggestions);
  } catch {
    hideSuggestions();
  }
}

function updateIterationBadge() {
  iterationBadge.textContent = iterationCount > 0 ? `iteration ${iterationCount}` : "";
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
  const id = Date.now();
  h.unshift({ id, ...entry, refinements: [] });
  sessionStorage.setItem("ph", JSON.stringify(h.slice(0, 10)));
  return id;
}

function updateCurrentHistory(feedback, data) {
  const h = getHistory();
  const idx = h.findIndex(e => e.id === currentHistoryId);
  if (idx === -1) return;
  h[idx].refinements.push(feedback);
  h[idx].system_prompt = data.system_prompt;
  h[idx].user_prompt = data.user_prompt;
  h[idx].reviewer_prompt = data.reviewer_prompt;
  sessionStorage.setItem("ph", JSON.stringify(h));
}

function renderHistory() {
  const h = getHistory();
  const section = document.getElementById("history-section");
  const list = document.getElementById("history-list");

  if (!h.length) {
    section.classList.add("hidden");
    section.classList.remove("flex");
    return;
  }

  section.classList.remove("hidden");
  section.classList.add("flex");
  list.innerHTML = "";

  h.forEach(entry => {
    const wrapper = document.createElement("div");
    wrapper.className = "flex flex-col";

    const el = document.createElement("div");
    el.className = "px-3.5 py-2.5 bg-white border border-[#E4E4E2] rounded-lg text-[13px] " +
      "text-[#8C8C88] hover:text-[#1A1A18] hover:border-[#BBBBB8] cursor-pointer " +
      "truncate transition-colors";
    el.textContent = entry.use_case;
    el.addEventListener("click", () => {
      useCaseEl.value = entry.use_case;
      currentHistoryId = entry.id;
      iterationCount = entry.refinements.length;
      updateIterationBadge();
      hideSuggestions();
      renderResult(entry);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    wrapper.appendChild(el);

    if (entry.refinements && entry.refinements.length > 0) {
      entry.refinements.forEach(r => {
        const sub = document.createElement("div");
        sub.className = "ml-4 pl-3 border-l border-[#E4E4E2] py-1 text-[12px] text-[#AAAAA6] truncate cursor-pointer hover:text-[#8C8C88] transition-colors";
        sub.textContent = `↳ ${r}`;
        sub.addEventListener("click", () => el.click());
        wrapper.appendChild(sub);
      });
    }

    list.appendChild(wrapper);
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

  if (!apiKey) {
    errorEl.textContent = "Enter your OpenAI API key first.";
    errorEl.classList.remove("hidden");
    return;
  }

  generateBtn.disabled = true;
  errorEl.classList.add("hidden");

  const stages = ["Generating candidates…", "Selecting best…", "Refining…"];
  let stageIdx = 0;
  generateBtn.textContent = stages[0];
  const stageTimer = setInterval(() => {
    stageIdx = Math.min(stageIdx + 1, stages.length - 1);
    generateBtn.textContent = stages[stageIdx];
  }, 5000);

  try {
    const res = await fetch(`${API_BASE}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ use_case: useCase, model: modelSelect.value, api_key: apiKey }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        res.status === 401
          ? "Invalid API key. Check your key and try again."
          : res.status === 422
            ? (data.detail || "Enter at least two words describing what you want to build or solve.")
            : "Something went wrong. Please try again."
      );
    }

    if (!hasGenerated) {
      hintEl.classList.add("hidden");
      hasGenerated = true;
    }

    iterationCount = 0;
    refinementHistory = [];
    currentWeaknesses = data.weaknesses || [];
    updateIterationBadge();
    renderResult(data);
    currentHistoryId = pushHistory({ use_case: useCase, ...data });
    renderHistory();
    fetchSuggestions(data.system_prompt, data.user_prompt, currentWeaknesses);

  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    clearInterval(stageTimer);
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate Prompt";
  }
});

// ── Refine ────────────────────────────────────────────────────────────────────

refineBtn.addEventListener("click", async () => {
  const feedback = refineInputEl.value.trim();
  if (!feedback) return;

  refineBtn.disabled = true;
  refineBtn.textContent = "Refining…";
  refineErrorEl.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_prompt: currentData.system_prompt,
        user_prompt: currentData.user_prompt,
        raw_fields: currentData.raw_fields || {},
        feedback,
        use_case: useCaseEl.value.trim(),
        refinement_history: refinementHistory,
        model: modelSelect.value,
        api_key: apiKey,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        res.status === 401
          ? "Invalid API key. Check your key and try again."
          : "Something went wrong. Please try again."
      );
    }

    refinementHistory.push(feedback);
    currentWeaknesses = data.weaknesses || [];
    iterationCount++;
    updateIterationBadge();
    updateCurrentHistory(feedback, data);
    renderHistory();
    renderResult(data);
    refineInputEl.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
    fetchSuggestions(data.system_prompt, data.user_prompt, currentWeaknesses);

  } catch (err) {
    refineErrorEl.textContent = err.message;
    refineErrorEl.classList.remove("hidden");
  } finally {
    refineBtn.disabled = false;
    refineBtn.textContent = "Refine Prompt";
  }
});

// ── Cmd+Enter ─────────────────────────────────────────────────────────────────

document.addEventListener("keydown", e => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    if (document.activeElement === refineInputEl && refineInputEl.value.trim()) {
      refineBtn.click();
    } else if (useCaseEl.value.trim()) {
      generateBtn.click();
    }
  }
});

// ── Models ────────────────────────────────────────────────────────────────────

async function loadModels() {
  try {
    const res = await fetch(`${API_BASE}/models`);
    const models = await res.json();
    models.forEach(({ id, label }) => {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = label;
      if (id === "gpt-4o-mini") opt.selected = true;
      modelSelect.appendChild(opt);
    });
  } catch {
    // fallback: backend unreachable, leave select empty
  }
}

// ── Cost hint ─────────────────────────────────────────────────────────────────

const COST_HINTS = {
  "gpt-4.1":  "~$0.015–0.020 per generate (5 calls)",
  "gpt-4o":   "~$0.020–0.030 per generate (5 calls)",
  "o4-mini":  "Reasoning model — 5 parallel calls, ~$0.05+ per generate",
};

function updateCostHint() {
  const hint = document.getElementById("cost-hint");
  const msg = COST_HINTS[modelSelect.value];
  if (msg) {
    hint.textContent = msg;
    hint.classList.remove("hidden");
  } else {
    hint.classList.add("hidden");
  }
}

modelSelect.addEventListener("change", updateCostHint);

// ── Init ──────────────────────────────────────────────────────────────────────

renderApiKeyState();
loadModels();
renderHistory();
