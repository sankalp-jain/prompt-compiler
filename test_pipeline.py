# """
# Test suite for AI Prompt Generator — all flows, 10 cases.
# """
# import os, json, time, textwrap
# import urllib.request, urllib.error
#
# BASE = "http://localhost:8000"
# KEY  = os.environ["OPENAI_API_KEY"]
# MODEL = "gpt-4o-mini"
#
# PASS = "PASS"
# FAIL = "FAIL"
#
# results = []
#
#
# # ── helpers ──────────────────────────────────────────────────────────────────
#
# def post(path, payload):
#     data = json.dumps(payload).encode()
#     req  = urllib.request.Request(
#         f"{BASE}{path}", data=data,
#         headers={"Content-Type": "application/json"}, method="POST"
#     )
#     with urllib.request.urlopen(req, timeout=120) as r:
#         return json.loads(r.read())
#
#
# def check_generate(resp):
#     """Return list of failure reasons, empty = valid."""
#     issues = []
#     for field in ("system_prompt", "user_prompt", "reviewer_prompt", "raw_fields"):
#         if not resp.get(field):
#             issues.append(f"missing {field}")
#     sp = resp.get("system_prompt", "")
#     for section in ("Role & expertise", "Task objective", "Constraints & assumptions",
#                     "Required output structure", "Quality bar"):
#         if section not in sp:
#             issues.append(f"system_prompt missing section '{section}'")
#     rf = resp.get("raw_fields", {})
#     for key in ("role_and_expertise","task_objective","constraints_and_assumptions",
#                 "required_output_structure","quality_bar","user_prompt"):
#         if not rf.get(key):
#             issues.append(f"raw_fields missing key '{key}'")
#     return issues
#
#
# def _to_str(v):
#     if isinstance(v, list):
#         return " ".join(str(i) for i in v)
#     return str(v) if v else ""
#
# def check_targeted(orig_rf, new_rf, targeted_field, feedback):
#     """Unchanged fields should be preserved; targeted field should differ."""
#     issues = []
#     for key in orig_rf:
#         orig_val = _to_str(orig_rf[key])
#         new_val  = _to_str(new_rf.get(key, ""))
#         if key == targeted_field:
#             if orig_val.strip() == new_val.strip():
#                 issues.append(f"targeted field '{key}' was not changed")
#         else:
#             orig_words = set(orig_val.lower().split())
#             new_words  = set(new_val.lower().split())
#             if orig_words and new_words:
#                 overlap = len(orig_words & new_words) / len(orig_words)
#                 if overlap < 0.6:
#                     issues.append(f"untargeted field '{key}' changed significantly (overlap {overlap:.0%})")
#     return issues
#
#
# def check_scope_change(orig_rf, new_rf):
#     """After scope change: quality bar should no longer be senior-dev, constraints should shrink."""
#     issues = []
#     orig_qb = _to_str(orig_rf.get("quality_bar", "")).lower()
#     new_qb  = _to_str(new_rf.get("quality_bar",  "")).lower()
#     if "reader is a senior developer" in new_qb:
#         issues.append("quality_bar still says 'reader is a senior developer' after scope change")
#     orig_con = _to_str(orig_rf.get("constraints_and_assumptions", ""))
#     new_con  = _to_str(new_rf.get("constraints_and_assumptions",  ""))
#     orig_bullets = orig_con.count("- ")
#     new_bullets  = new_con.count("- ")
#     if orig_bullets > 0 and new_bullets >= orig_bullets:
#         issues.append(
#             f"constraints not simplified after scope change "
#             f"(was {orig_bullets} bullets, now {new_bullets})"
#         )
#     return issues
#
#
# def check_suggestions(resp):
#     issues = []
#     items = resp.get("suggestions", [])
#     if len(items) < 3:
#         issues.append(f"expected 3 suggestions, got {len(items)}")
#     for i, s in enumerate(items):
#         if len(s.split()) < 5:
#             issues.append(f"suggestion {i+1} is too short: '{s}'")
#     return issues
#
#
# def record(name, flow, use_case, feedback, verdict, issues, resp=None):
#     results.append({
#         "name": name, "flow": flow, "use_case": use_case,
#         "feedback": feedback, "verdict": verdict, "issues": issues,
#         "resp_snippet": (resp or {}).get("user_prompt", "")[:120] if resp else "",
#     })
#     status = "✓" if verdict == PASS else "✗"
#     print(f"  {status}  {name} [{flow}] — {verdict}"
#           + (f"\n       issues: {issues}" if issues else ""))
#
#
# # ── test cases ────────────────────────────────────────────────────────────────
#
# print("\n=== Running 10 test cases ===\n")
#
# # ── TC1: Generate — Backend ───────────────────────────────────────────────────
# name = "TC1 · Generate · Backend"
# uc   = "design a rate limiter for a REST API using Redis and Node.js"
# print(f"[{name}]")
# try:
#     r = post("/generate", {"use_case": uc, "model": MODEL, "api_key": KEY})
#     issues = check_generate(r)
#     tc1_rf = r.get("raw_fields", {})
#     tc1_sp = r.get("system_prompt", "")
#     tc1_up = r.get("user_prompt", "")
#     record(name, "generate", uc, "", PASS if not issues else FAIL, issues, r)
# except Exception as e:
#     record(name, "generate", uc, "", FAIL, [str(e)])
#     tc1_rf = {}; tc1_sp = ""; tc1_up = ""
#
#
# # ── TC2: Generate — Frontend ──────────────────────────────────────────────────
# name = "TC2 · Generate · Frontend"
# uc   = "build an accessible autocomplete search component in React with keyboard navigation"
# print(f"[{name}]")
# try:
#     r = post("/generate", {"use_case": uc, "model": MODEL, "api_key": KEY})
#     issues = check_generate(r)
#     tc2_rf = r.get("raw_fields", {})
#     tc2_sp = r.get("system_prompt", "")
#     tc2_up = r.get("user_prompt", "")
#     record(name, "generate", uc, "", PASS if not issues else FAIL, issues, r)
# except Exception as e:
#     record(name, "generate", uc, "", FAIL, [str(e)])
#     tc2_rf = {}; tc2_sp = ""; tc2_up = ""
#
#
# # ── TC3: Generate — ML ────────────────────────────────────────────────────────
# name = "TC3 · Generate · ML"
# uc   = "fine-tune a BERT model for multi-label text classification using Hugging Face"
# print(f"[{name}]")
# try:
#     r = post("/generate", {"use_case": uc, "model": MODEL, "api_key": KEY})
#     issues = check_generate(r)
#     tc3_rf = r.get("raw_fields", {})
#     record(name, "generate", uc, "", PASS if not issues else FAIL, issues, r)
# except Exception as e:
#     record(name, "generate", uc, "", FAIL, [str(e)])
#     tc3_rf = {}
#
#
# # ── TC4: Generate — DevOps ────────────────────────────────────────────────────
# name = "TC4 · Generate · DevOps"
# uc   = "set up a blue-green deployment pipeline for a containerised service on Kubernetes"
# print(f"[{name}]")
# try:
#     r = post("/generate", {"use_case": uc, "model": MODEL, "api_key": KEY})
#     issues = check_generate(r)
#     tc4_rf = r.get("raw_fields", {})
#     record(name, "generate", uc, "", PASS if not issues else FAIL, issues, r)
# except Exception as e:
#     record(name, "generate", uc, "", FAIL, [str(e)])
#     tc4_rf = {}
#
#
# # ── TC5: Generate — General ───────────────────────────────────────────────────
# name = "TC5 · Generate · General"
# uc   = "write a technical design document for a URL shortener service"
# print(f"[{name}]")
# try:
#     r = post("/generate", {"use_case": uc, "model": MODEL, "api_key": KEY})
#     issues = check_generate(r)
#     tc5_rf = r.get("raw_fields", {})
#     tc5_sp = r.get("system_prompt", "")
#     tc5_up = r.get("user_prompt", "")
#     tc5_wk = r.get("weaknesses", [])
#     record(name, "generate", uc, "", PASS if not issues else FAIL, issues, r)
# except Exception as e:
#     record(name, "generate", uc, "", FAIL, [str(e)])
#     tc5_rf = {}; tc5_sp = ""; tc5_up = ""; tc5_wk = []
#
#
# # ── TC6: Refine — Targeted (add section) ─────────────────────────────────────
# name = "TC6 · Refine · Targeted — add section"
# fb   = "add a section on circuit breaker behaviour when Redis is unavailable"
# print(f"[{name}]")
# if tc1_rf:
#     try:
#         r = post("/refine", {
#             "system_prompt": tc1_sp, "user_prompt": tc1_up,
#             "raw_fields": tc1_rf, "feedback": fb,
#             "use_case": "design a rate limiter for a REST API using Redis and Node.js",
#             "refinement_history": [], "model": MODEL, "api_key": KEY,
#         })
#         base_issues = check_generate(r)
#         new_rf = r.get("raw_fields", {})
#         # targeted field: required_output_structure (adding a section)
#         targeted_issues = check_targeted(tc1_rf, new_rf, "required_output_structure", fb)
#         issues = base_issues + targeted_issues
#         record(name, "refine", "rate limiter (TC1 output)", fb,
#                PASS if not issues else FAIL, issues, r)
#     except Exception as e:
#         record(name, "refine", "rate limiter (TC1 output)", fb, FAIL, [str(e)])
# else:
#     record(name, "refine", "rate limiter (TC1 output)", fb, FAIL, ["TC1 failed, no base output"])
#
#
# # ── TC7: Refine — Targeted (change a field) ───────────────────────────────────
# name = "TC7 · Refine · Targeted — change role seniority"
# fb   = "change the role to a junior backend engineer, not senior"
# print(f"[{name}]")
# if tc2_rf:
#     try:
#         r = post("/refine", {
#             "system_prompt": tc2_sp, "user_prompt": tc2_up,
#             "raw_fields": tc2_rf, "feedback": fb,
#             "use_case": "build an accessible autocomplete search component in React with keyboard navigation",
#             "refinement_history": [], "model": MODEL, "api_key": KEY,
#         })
#         base_issues = check_generate(r)
#         new_rf = r.get("raw_fields", {})
#         targeted_issues = check_targeted(tc2_rf, new_rf, "role_and_expertise", fb)
#         # Also check the role actually says junior now
#         if "junior" not in new_rf.get("role_and_expertise", "").lower():
#             targeted_issues.append("role_and_expertise doesn't contain 'junior' after feedback")
#         issues = base_issues + targeted_issues
#         record(name, "refine", "autocomplete (TC2 output)", fb,
#                PASS if not issues else FAIL, issues, r)
#     except Exception as e:
#         record(name, "refine", "autocomplete (TC2 output)", fb, FAIL, [str(e)])
# else:
#     record(name, "refine", "autocomplete (TC2 output)", fb, FAIL, ["TC2 failed, no base output"])
#
#
# # ── TC8: Refine — Targeted (tech swap) ───────────────────────────────────────
# name = "TC8 · Refine · Targeted — tech swap"
# fb   = "use Memcached instead of Redis"
# print(f"[{name}]")
# if tc1_rf:
#     try:
#         r = post("/refine", {
#             "system_prompt": tc1_sp, "user_prompt": tc1_up,
#             "raw_fields": tc1_rf, "feedback": fb,
#             "use_case": "design a rate limiter for a REST API using Redis and Node.js",
#             "refinement_history": [], "model": MODEL, "api_key": KEY,
#         })
#         base_issues = check_generate(r)
#         new_rf = r.get("raw_fields", {})
#         # constraints should mention Memcached now
#         issues = base_issues
#         constraints_text = _to_str(new_rf.get("constraints_and_assumptions", "")).lower()
#         if "memcached" not in constraints_text and "redis" in constraints_text:
#             issues.append("constraints still mention Redis but not Memcached after tech swap")
#         # untargeted fields should be mostly preserved
#         for key in ("task_objective", "required_output_structure", "quality_bar"):
#             orig_val = _to_str(tc1_rf.get(key, ""))
#             new_val  = _to_str(new_rf.get(key, ""))
#             orig_words = set(orig_val.lower().split())
#             new_words  = set(new_val.lower().split())
#             if orig_words and new_words:
#                 overlap = len(orig_words & new_words) / len(orig_words)
#                 if overlap < 0.6:
#                     issues.append(f"untargeted field '{key}' changed significantly (overlap {overlap:.0%})")
#         record(name, "refine", "rate limiter (TC1 output)", fb,
#                PASS if not issues else FAIL, issues, r)
#     except Exception as e:
#         record(name, "refine", "rate limiter (TC1 output)", fb, FAIL, [str(e)])
# else:
#     record(name, "refine", "rate limiter (TC1 output)", fb, FAIL, ["TC1 failed, no base output"])
#
#
# # ── TC9: Refine — Targeted (constraint removal) ───────────────────────────────
# name = "TC9 · Refine · Targeted — constraint removal"
# fb   = "remove the section on deployment, I don't need that"
# print(f"[{name}]")
# if tc5_rf:
#     try:
#         r = post("/refine", {
#             "system_prompt": tc5_sp, "user_prompt": tc5_up,
#             "raw_fields": tc5_rf, "feedback": fb,
#             "use_case": "write a technical design document for a URL shortener service",
#             "refinement_history": [], "model": MODEL, "api_key": KEY,
#         })
#         base_issues = check_generate(r)
#         new_rf = r.get("raw_fields", {})
#         issues = base_issues
#         # required_output_structure should not mention deployment
#         ros = _to_str(new_rf.get("required_output_structure", "")).lower()
#         if "deployment" in ros or "deploy" in ros:
#             issues.append("required_output_structure still mentions deployment after removal request")
#         # role, task_objective, quality_bar should be preserved
#         for key in ("role_and_expertise", "task_objective", "quality_bar"):
#             orig_val = _to_str(tc5_rf.get(key, ""))
#             new_val  = _to_str(new_rf.get(key, ""))
#             orig_words = set(orig_val.lower().split())
#             new_words  = set(new_val.lower().split())
#             if orig_words and new_words:
#                 overlap = len(orig_words & new_words) / len(orig_words)
#                 if overlap < 0.6:
#                     issues.append(f"untargeted field '{key}' changed significantly (overlap {overlap:.0%})")
#         record(name, "refine", "URL shortener (TC5 output)", fb,
#                PASS if not issues else FAIL, issues, r)
#     except Exception as e:
#         record(name, "refine", "URL shortener (TC5 output)", fb, FAIL, [str(e)])
# else:
#     record(name, "refine", "URL shortener (TC5 output)", fb, FAIL, ["TC5 failed, no base output"])
#
#
# # ── TC10: Suggestions ─────────────────────────────────────────────────────────
# name = "TC10 · Suggestions"
# print(f"[{name}]")
# if tc5_sp:
#     try:
#         r = post("/suggestions", {
#             "system_prompt": tc5_sp, "user_prompt": tc5_up,
#             "weaknesses": tc5_wk, "api_key": KEY,
#         })
#         issues = check_suggestions(r)
#         record(name, "suggestions", "URL shortener (TC5 output)", "", PASS if not issues else FAIL, issues, r)
#     except Exception as e:
#         record(name, "suggestions", "URL shortener (TC5 output)", "", FAIL, [str(e)])
# else:
#     record(name, "suggestions", "URL shortener (TC5 output)", "", FAIL, ["TC5 failed, no base output"])
#
#
# # ── report ────────────────────────────────────────────────────────────────────
#
# passed = sum(1 for r in results if r["verdict"] == PASS)
# failed = len(results) - passed
#
# print("\n" + "="*70)
# print(f"  RESULTS: {passed}/{len(results)} passed   {failed} failed")
# print("="*70)
#
# flow_groups = {}
# for r in results:
#     flow_groups.setdefault(r["flow"], []).append(r)
#
# for flow, cases in flow_groups.items():
#     print(f"\n  [{flow.upper()}]")
#     for c in cases:
#         verdict_icon = "✓" if c["verdict"] == PASS else "✗"
#         print(f"    {verdict_icon} {c['name']}")
#         if c["feedback"]:
#             print(f"       feedback : {c['feedback'][:80]}")
#         if c["issues"]:
#             for iss in c["issues"]:
#                 print(f"       issue    : {iss}")
#         if c["resp_snippet"]:
#             snippet = textwrap.shorten(c["resp_snippet"], width=90, placeholder="…")
#             print(f"       snippet  : {snippet}")
#
# print("\n" + "="*70)
#
# # per-flow pass rate
# print("\n  Flow summary:")
# for flow, cases in flow_groups.items():
#     p = sum(1 for c in cases if c["verdict"] == PASS)
#     print(f"    {flow:<22} {p}/{len(cases)}")
#
# print()
#