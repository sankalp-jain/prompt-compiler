# Project Progress

## 2026-02-26

### Done
- Built a minimal AI-powered prompt generator MVP.
- User can input a plain-English coding use case.
- The app generates:
  - A **System Prompt** defining role, expertise, and expectations.
  - A **User Prompt** with clear, actionable instructions.
- Initial focus is on **backend / coding use cases**.
- Output is immediately usable in ChatGPT, Claude, or coding assistants.
- Implemented end-to-end flow:
  - Frontend input → backend API → LLM → rendered output.
- Prioritized speed and clarity over polish; MVP built in ~30 minutes using Claude Code.

### Plan
- Improve prompt quality by enforcing a clearer response structure
  - e.g. architecture → API design → data models → example code → production considerations.
- Add a small "follow-up / iteration prompt" section to help refine LLM outputs.
- Make output formatting more copy-friendly (clear sections, better spacing).
- Test generated prompts against 3–5 different coding use cases to validate consistency.
- Minor UI improvements only if they directly improve readability (no feature expansion).

---

## 2026-02-27

### Done
- Upgraded meta-prompt with intent summarisation step and enforced 5-section system prompt structure.
- Added Reviewer Prompt (fixed senior architect checklist) as a third output.
- Identified and fixed 6 meta-prompt failure cases (stack invention, weak objectives, non-constraining bullets, etc.).
- Added input validation — rejects gibberish without an LLM call.
- Added model selection dropdown: 6 OpenAI models, fetched dynamically from `GET /models`.
- Measured real token usage (~1,245/query) and calculated per-query cost across all models.
- Full UI redesign using Tailwind CDN + Inter + JetBrains Mono.
- Three visually differentiated output cards (inverted header, standard, dashed border).
- Markdown rendering, copy buttons, session history, user-facing error messages.
- Fixed native select/button height alignment cross-browser.
- Refactored codebase: `main.py`, `prompts.py`, `index.html`, `app.js` cleanly separated.

### Known issues (resolved in next session)
- `required_output_structure` occasionally renders as raw dict strings. ✓ fixed via `_to_str()`
- No `Cmd+Enter` keyboard shortcut. ✓ fixed
- History doesn't record which model was used.
- No in-app iteration loop for the reviewer prompt. ✓ fixed
- Frontend hardcodes `localhost:8000` — not deployable as-is.

### Plan
- Store model used in session history.
- Explore persistence layer (accounts, saved prompts) as path to monetisation.

---

## 2026-02-27 (evening)

### Done
- Added **prompt refinement loop** — user can iterate on generated prompts without leaving the app.
  - New `POST /refine` endpoint: accepts current prompts + feedback, applies changes via `REFINE_PROMPT`, returns updated prompts.
  - `REFINE_PROMPT` preserves 5-section structure, applies only what feedback requests, prevents quality regression.
  - Refine section appears below output after first generation (hidden until then).
  - Iteration counter shows current refinement depth (e.g. "iteration 2").
  - Refine input clears and page scrolls to top after each successful refinement.
- Added **`Cmd+Enter` / `Ctrl+Enter`** keyboard shortcut — works for both generate and refine inputs.

### Known issues
- History doesn't record which model was used.
- Frontend hardcodes `localhost:8000` — not deployable as-is.

### Plan
- Store model used in session history.
- Explore persistence layer (accounts, saved prompts) as path to monetisation.
