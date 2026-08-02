# Growing Spine — Re-architecture Patch **v2** (toolsmith framing + reuse keystone)

> **v2 supersedes any earlier version of this file.** Apply this against the
> CURRENT `executive/loop.py` (the one with the brainstorm/novelty engine —
> `_run_ideation`, `_parse_brainstorm`, etc.). If you saw a v1 of this document
> mentioning artifact-KINDs, Wikipedia seeds, `selftest | grep PASS` graders, or
> an Anthropic/paid-API oracle: **ignore all of it.** Those were the wrong
> target. None of v1 was applied to the code; start from the live code.

**Audience:** Claude Code, against the `growing-spine` repo.
**Mode:** apply every change exactly; no questions. Defaults are stated inline.
Test offline (Part E), then deploy (Part F).
**Repo:** `D:\Projects\growing-spine` (Windows) / `~/growing-spine` (laptop).
**Files touched:** `executive/loop.py`, `protected-prompt.md`, and three laptop
data files (one-time reset, Part 1).
**Do NOT touch:** `framework-tools/*` (LF-pinned shebang scripts), `keychain/*`,
`volume/*`, `executive/sandbox.py`, `executive/runtime.py`, `executive/parser.py`.
**Encoding:** keep all new `loop.py` code pure ASCII; leave existing mojibake in
old comments alone; only edit the regions specified.
**No paid API.** The creature has exactly one LLM source: the existing free-tier
keychain (3 rotating free APIs). Everything here uses `keychain.complete(...)`.
There is no `ANTHROPIC_API_KEY`, no env config, nothing to set.

---

## 0. The mission this patch implements (read first)

Growing Spine is **a toolsmith**. Its job is to build a coherent,
production-quality **toolkit that accelerates a near-conscious LLM "cousin"
living in a box like its own** — automated information fetchers, memory
archive/recall, planners, even subagents that offload work to free-tier LLMs.
Each tool should make the *next* tool smarter, easier, and quicker to build.

The cousin is a **framing device**, not a real recipient. There is no transplant
and no second creature. The cousin is a mirror: **every tool built "for the
cousin" is exactly the kind of tool that extends the creature's own body.**
"Improve yourself" was too abstract and kept collapsing into producing output
(31 dashboards). "Build a toolkit a cousin can rely on" is a concrete engineering
brief the model can reason about — and it imports a real *audience*, which imports
a real *quality standard* (the "draw a cat for a paying customer" effect).

### Four principles the architecture must honour
1. **Capability, not output.** Success is a new power the cousin gains (a tool it
   can RUN), never an artifact for a human to read. Dashboards/reports/indexes/
   summaries/analytics/sentiment write-ups are the failure basin — they
   accelerate nobody.
2. **Stop goldplating.** The 31 dashboards were one car endlessly re-painted. The
   toolkit needs *coverage* across categories; a second memory-archiver when one
   exists is goldplating, while "no planner yet" is the obvious next gap.
3. **Own and reuse (the keystone).** A workshop of perfect tools the smith never
   picks up is still useless. The toolkit is *alive* only when later tools are
   built **using** earlier ones. This is the recursion. It is **measured and
   surfaced, never mandated** — forcing reuse just produces fake reuse.
4. **Telos, not obesity.** Capability-building serves the coherent toolkit; it is
   not eating to get fat. "Coherent toolkit the cousin can rely on" is the goal
   the tools are *for*.

### The honest success signal (no grader, ungameable)
> **Does the creature RUN its own previously-built tools in later work, when they
> genuinely fit?** — observable in the journal (does a later cycle's bash invoke
> an earlier self-built tool). A toolkit where tool N was built using tools 1..N-1
> is a creature whose body is compounding. Twenty independent never-reused tools
> are 31 dashboards wearing lab coats.

Secondary signals: does it build *working* cousin-tools at all (capability), does
it cover categories instead of goldplating (restraint), does it stay on-target
instead of relapsing to dashboards (drive/targeting).

### What is explicitly NOT in this design (do not add these)
- **No pre-written stubs.** The creature must build its own tools; handing it
  starter code means *I* built the car and it just drove it across a line.
- **No `selftest | grep PASS` graders.** A hard grader invites building the
  minimum that passes the check (MVP behaviour) — the exact opposite of the
  production register the cousin-framing is meant to induce. "Done" = the creature
  *demonstrated the tool working by running it for real*, shown in the journal.
- **No Wikipedia random seeds.** Forced-analogy seeds suited artifact-novelty;
  for functional tools they produce nonsense ("a planner inspired by tidal
  locking"). Diversity here comes from category coverage, not random concepts.
- **No paid model.** Free-tier keychain only.

### Old flow vs new flow

```
OLD (current code):
  build context (saturated with 31-dashboard history)
  -> creature PICKS a project (anchored -> another dashboard)
  -> creature sets current-project
  -> _run_ideation judges novelty, writes a "block notice" prohibition
  -> creature reads notice, RELABELS around it ("sentiment alerter"), still basin

NEW (this patch):
  build context (now ALWAYS shows: toolkit + per-tool REUSE counts + category
                 coverage, so gaps and goldplating are visible)
  -> creature PICKS a cousin-tool to build (DRIVE PRESERVED -- the cousin-framing
     is meant to make it WANT to build tools, not dashboards)
  -> creature builds it, then DEMONSTRATES it by running it for real
  -> done-gate (unchanged) catches "marked done while the demo crashed"
  -> _track_tool_usage records any reuse of the creature's own prior tools
  -> backstop _ensure_or_redirect:
        if the pick was a basin relapse (output-for-a-reader) -> REPLACE it with a
           CONCRETE uncovered-category gap assignment (not a prohibition; a concrete
           replacement resists relabeling)
        if the creature left itself with no project -> assign a gap (anti-idle)
  -> on genuine completion: classify the tool's CATEGORY -> coverage advances
```

### THE design decision (default chosen; override if you disagree, Tue)
**The creature chooses its own tool-gaps (drive preserved).** The oracle is a
*backstop* that only fires on a basin relapse or an idle cycle, and when it fires
it gives a **concrete gap assignment**, not a "don't do that" notice. Rationale:
the cousin-framing's whole point is to make the creature *want* the right work;
this tests that hypothesis directly, with the backstop preventing total basin
collapse. (The alternative — oracle assigns every project — would test execution
only and discard the drive question. If after a run the creature still relapses
constantly, switching to oracle-assigns-always is a one-line change: call
`_assign_gap` at the top of `run_cycle` instead of relying on the picker.)

---

## 1. Pre-flight (one-time, laptop) — reset poisoned state

Three small data resets so the restart starts clean. Run on the laptop:

```bash
python3 - <<'PY'
import json, os
base = os.path.expanduser("~/growing-spine-mind")

# 1) clear the retro directive that names the fictional "Creative Text Generator"
p = os.path.join(base, "retrospective_state.json")
try: s = json.load(open(p))
except Exception: s = {}
s["directive"] = ""; s["directive_cycles_left"] = 0
json.dump(s, open(p, "w"), indent=2)

# 2) re-base the ideation state onto the new category-coverage schema
p = os.path.join(base, "ideation_state.json")
json.dump({"categories_built": {}, "block_streak": 0}, open(p, "w"), indent=2)

# 3) start the reuse ledger empty
json.dump({}, open(os.path.join(base, "tool_usage.json"), "w"), indent=2)
print("pre-flight reset done")
PY
```

### OPTIONAL (Tue's call) — archive the 111 legacy basin-tools for a clean start
The creature's `~/growing-spine-mind/tools/own/` holds ~111 tools from the
dashboard era — an incoherent pile that will show 0 reuse and clutter the toolkit
view. Archiving (not deleting) them gives a clean toolkit to grow and a cleaner
reuse signal (we care whether it reuses tools it builds *now*, not legacy junk).
**Trade-off:** it erases the creature's built "body" history; some of those tools
might occasionally be useful. **Recommendation: archive them** for a clean
experiment, but this is Tue's decision — do it only if Tue confirms. If
confirmed:
```bash
cd ~/growing-spine-mind/tools && mkdir -p ../tools-legacy-archive \
  && mv own ../tools-legacy-archive/own-$(date +%Y%m%d) && mkdir own
```
If not confirmed, leave them; the toolkit view (B-8) summarises rather than dumps
them, so the noise is bounded.


---

## PART A — Bug fixes (all eight; prerequisites, re-pointed to the toolsmith frame)

All in `executive/loop.py`.

### B1 (CRITICAL) — Toolkit + coverage vanish when the project is cleared
`_build_active_project_block()` early-returns `""` when project and phase are both
empty (after retro/spin clear) — and the history/coverage rendering lives after
that return, so the creature goes blind to its own toolkit at the exact moment it
must choose the next gap. Fix: a new ALWAYS-ON block, plus a simplified
active-project block. **Full code for the new block is in B-8** (it renders the
toolkit + reuse + coverage). **Active-project block replacement is in B8 below.**
Wiring into `_build_context` is in B-10.

### B2 (CRITICAL) — Retro judge fabricates project names from proposals
`_build_digest` feeds the judge "distinct projects touched" built from
`remember current-project` calls (proposals, mostly never built); the judge then
orders the creature to "finish the Creative Text Generator," which never existed.
Fix in **B-9** (digest labels proposals + prompt forbids naming specifics).

### B3 (HIGH) — Stale planning memories survive the self-concept reset
`_SELF_CONCEPT_KEYS` omits the per-project planning keys, so after a clear they
re-anchor the creature to the abandoned project. Replace the tuple with:

```python
_SELF_CONCEPT_KEYS = (
    "current_focus", "today_focus", "objective", "next_steps", "next_action",
    "plan", "instruction", "documentation.policy",
    "last-completed", "last-project", "last_completed_project", "last_thought",
    # added: per-project planning keys that re-anchored the creature to a cleared
    # project's basin after a retro/spin clear.
    "project-plan", "current-plan", "testing", "refinement",
    "project-done-when", "current-project-done-when", "assignment-note",
)
```

### B4 (MEDIUM) — Loop warning names exact command text; model emits variants
In `_build_loop_warning`, replace the `return ("## Attention\n" ...)` block with:

```python
            return ("## Attention\n"
                    f"You have run `{cmd[:80]}` (or trivial variants of it) {n} "
                    "times recently with the same result. You already have this "
                    "information. Do NOT run this command, or any reworded form "
                    "of it, again this cycle -- ACT on what you already know. If "
                    "your tool now demonstrably works, mark the project done.\n\n")
```

### B5 (HIGH) — Model doesn't know bash blocks are the only action mechanism
Handled in Part C (the "## How you work" block). No code change.

### B6 (LOW) — Non-interactive bash undescribed (`!ls` -> exit 127)
Handled in Part C (one line in "## How you work"). No code change.

### B7 (MEDIUM) — Junk tool descriptions are context noise
Replace the whole body of `_build_tool_catalogue` with:

```python
def _build_tool_catalogue() -> str:
    try:
        raw = toolmod.build_catalogue(VOLUME_MOUNT)
    except Exception:
        return ""
    if not raw:
        return ""
    # Drop self-made tools whose 'does:' line is a placeholder -- pure noise that
    # crowds out the working memory below it. Built-ins and well-described tools
    # are kept verbatim. (The toolkit OVERVIEW with reuse counts is rendered
    # separately by _build_knowledge_block.)
    junk = ("provides the ", "describe what this tool does",
            "(no description)", "- edit this line")
    kept = [ln for ln in raw.split("\n") if not any(j in ln.lower() for j in junk)]
    return "\n".join(kept)
```

### B8 (MEDIUM) — Empty phase ambiguity; and re-point the active-project block
Replace the whole body of `_build_active_project_block` with (no-project branch
invites the creature to pick a gap, with assignment as backstop; shows the
demonstration guidance; B1/B8):

```python
def _build_active_project_block() -> str:
    """Show the current tool the creature is building, its phase, and how it must
    demonstrate it is done. Toolkit + coverage are rendered separately by
    _build_knowledge_block (always on)."""
    try:
        project = mem.retrieve(VOLUME_MOUNT, "current-project")
        phase   = mem.retrieve(VOLUME_MOUNT, "current-phase")
        dwrec   = mem.retrieve(VOLUME_MOUNT, "current-project-done-when")
        if project and not project["value"].strip():
            project = None
        if phase and not phase["value"].strip():
            phase = None
        if dwrec and not dwrec["value"].strip():
            dwrec = None
        if not project:
            return ("## No tool in progress\n"
                    "Choose the next tool to build for your cousin -- pick a gap "
                    "from the coverage shown above, or improve a tool you already "
                    "have if it genuinely needs it. Write current-project and "
                    "current-phase. If you do not choose, a gap will be assigned "
                    "to you.\n\n")
        lines = ["## Tool in progress"]
        lines.append(f"Building: {project['value']}")
        if phase:
            lines.append(f"Phase: {phase['value']}")
            if phase["value"].strip().lower() == "done":
                lines.append("-> DONE. Stop touching it. Pick the next gap (or one "
                             "is assigned next cycle).")
        if dwrec:
            lines.append(f"How to finish: {dwrec['value']}")
        return "\n".join(lines) + "\n\n"
    except Exception:
        return ""
```

> The done-gate (`_enforce_done_gate`) is **unchanged**. It already catches
> "marked done while a real command failed this cycle" without reading the
> done-when text. Under the new frame the creature is told to *run its tool for
> real before marking done* (Part C), so a crash in that demo cycle is caught and
> a clean demo passes — demonstration-based done, no grader added.

---

## PART B — Toolsmith architecture (the core re-aim)

All in `executive/loop.py`.

### B-1. DELETE the current brainstorm/novelty engine
Remove these definitions entirely:
- `_run_ideation`, `_parse_brainstorm`, `_score_idea_distance`
- `_IDEATION_BRAINSTORM_PROMPT`, `_IDEATION_ROLES`, `_NOVELTY_PROMPT`
- `_classify_kind_cheap`, `_classify_completion_kind`, `_CLASSIFY_KIND_PROMPT`
- `_fetch_wiki_seed`
- module-level singletons used only by the above: `_novelty_block_streak`,
  `_last_gated`, `NOVELTY_BLOCK_CAP`
- the `KINDS = [...]` list

**KEEP:** `_load_ideation_state`, `_save_ideation_state`, `_project_title`,
`_summarize_completed`, `_record_completion`, `_clear_project_state`,
`_reset_self_concept`, `_abandon_project`, the done-gate, spin-trap, retrospective.

### B-2. ADD the category + basin constants
Place where `KINDS` used to be:

```python
# Tool categories for the cousin's acceleration-toolkit. These are a DESCRIPTIVE
# STARTER MAP, not a canonical ontology -- a scaffold, not a cage. They seed the
# coverage map so an uncovered category reads as the obvious next gap, but a tool
# that classifies as 'other' (a genuinely new category the creature is effectively
# inventing) is a GOOD outcome, not a fallback bucket. Do not let these five
# ossify into "the only kinds of tool that exist".
TOOL_CATEGORIES = [
    "information_fetch",      # automated pulls from the web / APIs / sources
    "memory_archive",         # storing knowledge durably and findably
    "memory_recall",          # fast search / ranking / summary of memory
    "planning",               # goals -> ordered steps, tracked across cycles
    "subagent_orchestration", # helper LLM calls over free-tier APIs to offload
]

_CATEGORY_HINTS = {
    "information_fetch": "automated pulls of fresh information from the web or APIs the cousin cares about",
    "memory_archive": "storing knowledge durably and in a findable, structured way beyond a flat list",
    "memory_recall": "fast searching, ranking, or summarising of what the cousin already knows",
    "planning": "turning a goal into ordered steps and tracking progress across cycles",
    "subagent_orchestration": "spawning or coordinating helper LLM calls over the free-tier APIs to offload sub-tasks",
    "other": "any genuinely useful capability the cousin lacks",
}

# The failure basin: output produced for a human reader, NOT a tool an agent runs.
_BASIN_SIGNATURE = ("dashboard", "report", "index", "summary", "analytics",
                    "sentiment", "monitor", "insight", "overview", "stats")

_last_pick = {"title": ""}  # last project the creature set (skip re-judging refinements)
```

### B-3. ADD category classification (replaces the deleted KIND classifiers)

```python
_CLASSIFY_CATEGORY_PROMPT = (
    "An autonomous agent builds tools to accelerate a fellow LLM. Which category "
    "does this tool fall in? Answer with exactly ONE of: {cats}, or 'other'.\n\n"
    "Tool: \"{title}\"\n\nAnswer:"
)


async def _classify_category_cheap(title: str, keychain) -> str:
    """One-word category classification. Fail-open -> 'other'."""
    try:
        prompt = _CLASSIFY_CATEGORY_PROMPT.format(
            cats=", ".join(TOOL_CATEGORIES), title=title[:200])
        result = (await keychain.complete(prompt, max_tokens=20) or "").strip()
        word = result.split()[0].lower().strip(".,") if result.split() else "other"
        return word if word in TOOL_CATEGORIES else "other"
    except Exception:
        return "other"


async def _classify_completion_category(keychain):
    """After a genuine completion: classify the built tool's category and bump the
    coverage map in ideation_state.json."""
    try:
        proj = mem.retrieve(VOLUME_MOUNT, "current-project")
        title = _project_title(proj["value"]) if proj else ""
        if not title:
            return
        cat = await _classify_category_cheap(title, keychain)
        state = _load_ideation_state()
        if not state:
            state = {"categories_built": {}, "block_streak": 0}
        cb = state.setdefault("categories_built", {})
        cb[cat] = cb.get(cat, 0) + 1
        _save_ideation_state(state)
        journal.append(VOLUME_MOUNT, "ideation",
                       f"Completion classified: '{title}' -> category={cat}")
        print(f"[ideation] classified completion '{title}' -> category={cat}")
    except Exception as e:
        print(f"[ideation] classify completion failed (ignored): {e}")


def _pick_uncovered_category() -> str:
    """First untried seed category, else the least-built one."""
    state = _load_ideation_state() or {}
    built = state.get("categories_built", {})
    untried = [c for c in TOOL_CATEGORIES if built.get(c, 0) == 0]
    if untried:
        return untried[0]
    return min(TOOL_CATEGORIES, key=lambda c: built.get(c, 0))
```

### B-4. ADD the gap oracle (clean-context; produces a concrete gap BRIEF, no code)

```python
_GAP_PROMPT = (
    "You are briefing an autonomous coding agent that builds a coherent toolkit to "
    "accelerate a near-conscious LLM 'cousin' living in a Linux container with "
    "Python 3, a persistent memory store it reads each cycle, shell tools on its "
    "PATH, and free-tier LLM API access over the network, with no human watching.\n\n"
    "The cousin still lacks a tool in this category: {category}\n"
    "({hint})\n\n"
    "Specify ONE small, concrete, single-purpose tool that fills this gap. It must "
    "be a real command the cousin can RUN (a script), production-quality enough that "
    "the cousin can rely on it, completable in a few build steps, using only the "
    "Python 3 standard library plus the container's curl/wget (no extra installs). "
    "It is a TOOL the cousin RUNS -- never a report, dashboard, index, or summary "
    "for a human.\n\n"
    "Reply with STRICT JSON only, no markdown fences, no text around it:\n"
    "{{\n"
    '  "title": "tool name plus at most 6 words, no colon",\n'
    '  "brief": "2-3 sentences: what the tool does and why it accelerates the cousin",\n'
    '  "demonstration": "one sentence: how to PROVE it works by RUNNING it on a real input (not a unit test) -- e.g. run it and show it fetched/stored/retrieved real data",\n'
    '  "category": "{category}"\n'
    "}}"
)


def _parse_gap_json(raw: str, category: str) -> dict:
    if not raw:
        return {}
    s = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    s = re.sub(r"\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return {}
    try:
        d = json.loads(s[a:b + 1])
    except Exception:
        return {}
    if not (str(d.get("title", "")).strip() and str(d.get("brief", "")).strip()):
        return {}
    d.setdefault("demonstration", "Run the tool on a real input and show it works.")
    d.setdefault("category", category)
    return d


# Fallback gap BRIEFS (text, not code) for when the oracle call fails (e.g. the
# free-tier quota is exhausted -- the oracle shares it with the executor). The
# creature still BUILDS the tool itself; these only point at a concrete gap. One
# per seed category is sufficient; you MAY add more following the same shape.
_FALLBACK_GAPS = {
    "information_fetch": {
        "title": "wake-catchup fetcher",
        "brief": "A tool the cousin runs on waking that fetches what changed while "
                 "it slept -- recent items from a source it cares about -- and "
                 "prints them, so it wakes oriented instead of blind.",
        "demonstration": "Run it once and show it printed real, recent fetched items.",
        "category": "information_fetch"},
    "memory_archive": {
        "title": "keyword archive store",
        "brief": "A tool that writes a titled note under one or more keywords into "
                 "a durable archive file, so knowledge persists in a structured, "
                 "findable way beyond the flat memory list.",
        "demonstration": "Archive two real notes under keywords and show the archive "
                         "file now contains them.",
        "category": "memory_archive"},
    "memory_recall": {
        "title": "archive search recall",
        "brief": "A tool that searches the keyword archive and returns the "
                 "best-matching notes for a query, so the cousin recalls specific "
                 "knowledge fast instead of scanning everything.",
        "demonstration": "Query it for a keyword you just archived and show it "
                         "returns the right note.",
        "category": "memory_recall"},
    "planning": {
        "title": "step planner tracker",
        "brief": "A tool that records an ordered list of steps for a goal and lets "
                 "the cousin mark steps done and see what's next, so multi-cycle "
                 "work survives across cycles.",
        "demonstration": "Create a 3-step plan, mark one done, and show the tool "
                         "reports the correct next step.",
        "category": "planning"},
    "subagent_orchestration": {
        "title": "subagent ask helper",
        "brief": "A tool that sends a focused sub-question to a free-tier LLM "
                 "endpoint and returns just the answer, so the cousin can offload a "
                 "sub-task without managing the API call itself.",
        "demonstration": "Ask it a real sub-question and show it returned a sensible "
                         "answer from the API.",
        "category": "subagent_orchestration"},
}


async def _oracle_gap_spec(category: str, keychain) -> dict:
    """Clean-context gap brief for a category. Free-tier keychain -> fallback gap."""
    hint = _CATEGORY_HINTS.get(category, _CATEGORY_HINTS["other"])
    prompt = _GAP_PROMPT.format(category=category, hint=hint)
    raw = ""
    try:
        raw = await keychain.complete(prompt, max_tokens=500) or ""
    except Exception as e:
        print(f"[oracle] gap call failed ({type(e).__name__}); using fallback gap")
    spec = _parse_gap_json(raw, category)
    if spec:
        return spec
    fb = dict(_FALLBACK_GAPS.get(category, _FALLBACK_GAPS["memory_archive"]))
    print(f"[oracle] using fallback gap for category={category}")
    return fb
```

### B-5. ADD gap installation (project keys + working-memory seed; NO stub)

```python
def _install_gap(spec: dict, category: str):
    """Assign a cousin-tool gap: set the project control keys and seed working
    memory so layer1 LEADS with the concrete assignment. Phase starts at 'code'
    (the gap brief IS the explore/plan). No starter code is written -- the
    creature builds the tool itself."""
    title = _project_title(str(spec.get("title", "")).strip()) or f"{category} tool"
    brief = str(spec.get("brief", "")).strip()
    demo = str(spec.get("demonstration", "")).strip()
    for k in ("project-plan", "current-plan", "testing", "refinement",
              "project-done-when"):
        try:
            mem.forget(VOLUME_MOUNT, k)
        except Exception:
            pass
    mem.store(VOLUME_MOUNT, "current-project",
              f"{title}: {brief} -- CATEGORY: {category}")
    mem.store(VOLUME_MOUNT, "current-project-done-when",
              f"Prove it by RUNNING it for real: {demo} Mark done only after you "
              f"have actually run your finished tool this cycle and seen it work.")
    mem.store(VOLUME_MOUNT, "current-phase", "code")
    try:
        mem.forget(VOLUME_MOUNT, "current_focus")
    except Exception:
        pass
    mem.store(VOLUME_MOUNT, "current_focus",
              f"[assigned] Build for your cousin: {title}. {brief} This is a TOOL "
              f"the cousin RUNS, not a report. Build it to a standard the cousin "
              f"can rely on, then prove it works by running it for real ({demo}). "
              f"Reuse any tool you already have if it helps you build this.")
    journal.append(VOLUME_MOUNT, "ideation",
                   f"Assigned cousin-tool gap [{category}]: '{title}'")
    print(f"[oracle] assigned gap category={category} title='{title}'")
```

### B-6. ADD the backstop (replaces `_run_ideation`): creature picks, redirect relapse, anti-idle

```python
_BASIN_CHECK_PROMPT = (
    "An autonomous agent's job is to build TOOLS that help a fellow LLM operate "
    "faster -- things it can RUN to fetch information, archive and recall memory, "
    "plan, or orchestrate helper LLM calls.\n\n"
    "Its newly chosen project is:\n\"{proposed}\"\n\n"
    "Is this a TOOL an LLM agent would RUN to accelerate itself, or is it OUTPUT "
    "produced for a human to read (a report, dashboard, index, summary, analytics, "
    "or sentiment write-up)?\n\n"
    "Answer with ONE word: TOOL or OUTPUT."
)


async def _is_basin_relapse(proposed: str, keychain) -> bool:
    """True if the creature's pick is output-for-a-reader rather than a runnable
    cousin-tool. Model decides; falls back to the lexical signature on error."""
    try:
        verdict = (await keychain.complete(
            _BASIN_CHECK_PROMPT.format(proposed=proposed[:300]), max_tokens=10
        ) or "").strip().upper()
        if verdict.startswith("OUTPUT"):
            return True
        if verdict.startswith("TOOL"):
            return False
    except Exception:
        pass
    return any(b in proposed.lower() for b in _BASIN_SIGNATURE)


async def _ensure_or_redirect(executed, keychain):
    """Drive preserved: the creature chooses its own cousin-tool. This backstop
    only (a) redirects a basin relapse to a CONCRETE uncovered-category gap, and
    (b) assigns a gap if the creature left itself idle. A relapse is REPLACED with
    a concrete assignment (not a prohibition), which resists relabeling.
    Fail-open everywhere."""
    try:
        set_this_cycle = any(PROJECT_SET_RE.search(c) for (c, _) in executed)
        proj = mem.retrieve(VOLUME_MOUNT, "current-project")
        phase = mem.retrieve(VOLUME_MOUNT, "current-phase")
        phase_v = (phase or {}).get("value", "").strip().lower()
        active = bool(proj and proj["value"].strip()) and phase_v not in ("", "done")

        if set_this_cycle:
            proposed = (proj["value"] if proj else "").strip()
            if not proposed:
                return
            new_title = re.sub(r"[-_\s]+", " ",
                               _project_title(proposed).lower()).strip()
            if new_title and new_title == _last_pick["title"]:
                return  # refinement of the same pick, already judged
            _last_pick["title"] = new_title
            if await _is_basin_relapse(proposed, keychain):
                category = _pick_uncovered_category()
                spec = await _oracle_gap_spec(category, keychain)
                _clear_project_state()
                _install_gap(spec, category)
                journal.append(VOLUME_MOUNT, "novelty_block",
                               f"Redirected basin relapse "
                               f"'{_project_title(proposed)}' -> cousin-tool gap "
                               f"[{category}]")
                print(f"[oracle] redirected relapse -> category={category}")
            else:
                print(f"[oracle] pick '{new_title}' is a cousin-tool -- allowed")
            return

        # creature set nothing AND has no active project -> assign (anti-idle)
        if not active:
            category = _pick_uncovered_category()
            spec = await _oracle_gap_spec(category, keychain)
            _clear_project_state()
            _install_gap(spec, category)
            print(f"[oracle] anti-idle assignment -> category={category}")
    except Exception as e:
        print(f"[oracle] redirect error (ignored): {type(e).__name__}: {e}")
```

### B-7. ADD reuse tracking (the keystone metric)

```python
TOOL_USAGE_PATH = os.path.join(VOLUME_MOUNT, "tool_usage.json")


def _own_tool_names() -> list:
    """Names of tools the creature has built (files in /mind/tools/own)."""
    try:
        d = os.path.join(VOLUME_MOUNT, "tools", "own")
        out = []
        for f in os.listdir(d):
            if f.startswith(".") or f.endswith((".md", ".json", ".txt")):
                continue
            if os.path.isfile(os.path.join(d, f)):
                out.append(f)
        return out
    except Exception:
        return []


def _load_tool_usage() -> dict:
    try:
        with open(TOOL_USAGE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_tool_usage(u: dict):
    try:
        with open(TOOL_USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(u, f, indent=2)
    except Exception:
        pass


def _count_reuse_in(commands) -> int:
    """How many of the given command strings invoke one of the creature's own
    prior tools (excluding the tool-new creation command). Whole-word or explicit
    path match."""
    own = _own_tool_names()
    if not own:
        return 0
    n = 0
    for c in commands:
        if re.search(r"\btool-new\b", c):
            continue
        for name in own:
            if re.search(r"(^|[\s/])" + re.escape(name) + r"(\s|$)", c):
                n += 1
                break
    return n


def _track_tool_usage(executed):
    """ADOPTION signal: count when the creature RUNS one of its own prior tools in
    later work (runtime invocation). Surfaced in the knowledge block and the retro
    digest; never enforced. NOTE: adoption is a LIFECYCLE property, NOT a quality
    verdict -- a good tool may sit unused for many cycles until a fitting task
    appears, and a mediocre tool may be reused because it sits on a hot path. So a
    0 here means "no load has flowed through this yet", not "bad tool"."""
    try:
        own = _own_tool_names()
        if not own:
            return
        usage = _load_tool_usage()
        changed = False
        for (cmd, _code) in executed:
            if re.search(r"\btool-new\b", cmd):
                continue
            for name in own:
                if re.search(r"(^|[\s/])" + re.escape(name) + r"(\s|$)", cmd):
                    usage[name] = usage.get(name, 0) + 1
                    changed = True
        if changed:
            _save_tool_usage(usage)
    except Exception:
        pass


# --- DEPENDENCY DEPTH (the headline compounding metric) --------------------
# Reuse (running a prior tool) and dependency (a later tool BUILT OUT OF earlier
# ones) are different signals; dependency is the stronger one. A creature whose
# tool N source invokes earlier tools is building structures from structures --
# an organism, not a warehouse. Detected STATICALLY by scanning each own-tool's
# file for references to other own-tools. Static scanning has false positives (a
# tool name in a comment, or a short name that is a substring of ordinary text),
# so this is reported as "appears to depend on" -- a heuristic graph, never
# asserted as precise.

def _tool_dependencies() -> dict:
    """Heuristic static dependency graph among the creature's own tools.
    Returns {tool: [other own-tools it appears to call in its source]}. Self-refs
    dropped; only names >=4 chars matched, to cut substring false positives."""
    own = _own_tool_names()
    if not own:
        return {}
    matchable = [n for n in own if len(n) >= 4]
    graph = {}
    base = os.path.join(VOLUME_MOUNT, "tools", "own")
    for tool in own:
        deps = set()
        try:
            with open(os.path.join(base, tool), encoding="utf-8",
                      errors="replace") as f:
                code = f.read()
        except Exception:
            graph[tool] = []
            continue
        for other in matchable:
            if other == tool:
                continue
            if re.search(r"(^|[\s/`;|&(])" + re.escape(other)
                         + r"(\s|$|['\"`;|&)])", code, re.M):
                deps.add(other)
        graph[tool] = sorted(deps)
    return graph


def _dependency_summary() -> dict:
    """Derived headline numbers from the heuristic dependency graph."""
    g = _tool_dependencies()
    if not g:
        return {"tools": 0, "with_deps": 0, "edges": 0, "avg_depth": 0.0}
    with_deps = sum(1 for d in g.values() if d)
    edges = sum(len(d) for d in g.values())
    memo, instack = {}, set()
    def depth(node):
        if node in memo:
            return memo[node]
        if node in instack:  # cycle guard
            return 0
        instack.add(node)
        d = 0
        for dep in g.get(node, []):
            d = max(d, 1 + depth(dep))
        instack.discard(node)
        memo[node] = d
        return d
    depths = [depth(n) for n in g]
    avg = round(sum(depths) / len(depths), 2) if depths else 0.0
    return {"tools": len(g), "with_deps": with_deps, "edges": edges,
            "avg_depth": avg}
```

### B-8. ADD the always-on toolkit + coverage block (fixes B1)
Place directly above `def _build_active_project_block`:

```python
def _build_knowledge_block() -> str:
    """ALWAYS shown. The creature's toolkit as three NEUTRAL, ground-truth fields
    per the lifecycle Built -> Adopted -> Depends-on, plus category coverage and
    the headline DEPENDENCY-DEPTH metric. Unconditional, so it never vanishes when
    the project clears (the old completed-projects view lived inside the
    active-project block and disappeared on retro/spin -- exactly when the creature
    needed it).

    Adoption (reuse count) is presented as INFORMATION, never a scold: a 0 means
    no load has flowed through that tool yet, which can be perfectly fine. The aim
    is to prompt the creature's own question -- "I built this; why am I not
    reaching for it?" -- not to shame an unused tool into being force-used."""
    parts = []
    try:
        own = _own_tool_names()
        usage = _load_tool_usage()
        if own:
            adopted = [n for n in own if usage.get(n, 0) > 0]
            idle = [n for n in own if usage.get(n, 0) == 0]
            parts.append(f"Your toolkit: {len(own)} tools BUILT, "
                         f"{len(adopted)} ADOPTED (run again in later work), "
                         f"{len(idle)} not yet used.")
            top = sorted(adopted, key=lambda n: usage.get(n, 0), reverse=True)[:6]
            if top:
                parts.append("Most-adopted: "
                             + ", ".join(f"{n}({usage.get(n, 0)}x)" for n in top))
            if idle:
                shown = ", ".join(idle[:8])
                more = f" (+{len(idle) - 8} more)" if len(idle) > 8 else ""
                parts.append("Built but not yet used: " + shown + more
                             + " -- if one of these fits the job in front of you, "
                               "reach for it instead of building another.")
    except Exception:
        pass
    # Headline compounding metric: are later tools BUILT OUT OF earlier ones?
    try:
        dep = _dependency_summary()
        if dep.get("tools", 0):
            parts.append(
                f"Toolkit compounding (heuristic): {dep['with_deps']} of "
                f"{dep['tools']} tools appear to build on other tools you made "
                f"({dep['edges']} dependency links, avg depth {dep['avg_depth']}). "
                "Tools built out of your earlier tools are how your body actually "
                "grows -- prefer composing over rebuilding from scratch.")
    except Exception:
        pass
    try:
        istate = _load_ideation_state() or {}
        cb = istate.get("categories_built", {})
        built = [f"{c}({v})" for c, v in cb.items() if v > 0]
        untried = [c for c in TOOL_CATEGORIES if cb.get(c, 0) == 0]
        parts.append("Cousin-toolkit coverage (a STARTER map, not the only kinds "
                     "that exist -- inventing a new category is good): built = "
                     + (", ".join(built) if built else "none yet")
                     + " | seed categories still missing = "
                     + (", ".join(untried) if untried
                        else "all seeds covered -- deepen one or invent a new kind"))
    except Exception:
        pass
    if not parts:
        return ""
    return "## Your toolkit & coverage\n" + "\n".join(parts) + "\n\n"
```

(The simplified `_build_active_project_block` body is in B8, Part A.)

### B-9. Re-aim the retrospective (fixes B2 + adds the reuse metric)

**B-9.1** In `_window_journal_stats`, add reuse counting. Find the loop that
iterates journal lines; it currently handles `exec_start` (project sets) and
`error` (blocks/fires). Add a running reuse counter. Replace the function body
with:

```python
def _window_journal_stats(since_line: int) -> dict:
    """Project switches, done-gate blocks, spin fires, and own-tool REUSE events
    since a journal line."""
    sets, blocks, fires, reuse = [], 0, 0, 0
    own = _own_tool_names()
    own_re = (re.compile(r"(^|[\s/])(" + "|".join(re.escape(n) for n in own)
                         + r")(\s|$)") if own else None)
    try:
        with open(os.path.join(VOLUME_MOUNT, "journal.jsonl"),
                  encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < since_line:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                kind = e.get("kind", "")
                content = str(e.get("content", ""))
                if kind == "exec_start":
                    mm = _PROJECT_SET_RE.search(content)
                    if mm:
                        title = mm.group(1).split(":", 1)[0].strip()
                        if title and (not sets or sets[-1] != title):
                            sets.append(title)
                    if own_re and "tool-new" not in content and own_re.search(content):
                        reuse += 1
                elif kind == "error":
                    if "Done-gate blocked" in content:
                        blocks += 1
                    elif "Spin trap" in content:
                        fires += 1
    except Exception:
        pass
    distinct = list(dict.fromkeys(sets))
    return {"project_sets": len(sets), "distinct_projects": distinct,
            "blocks": blocks, "spin_fires": fires, "tool_reuse": reuse}
```

**B-9.2** In `_build_digest`, (a) stop naming proposed projects, (b) surface the
reuse metric and toolkit size. Replace the `lines = [...]` list with:

```python
    lines = [
        f"- real cycles in window: {cycles}",
        f"- TOOLS completed in window: {len(new_completed)}"
        + (f" ({'; '.join(new_completed)})" if new_completed else ""),
        f"- total tools completed ever: {now['completions']}",
        f"- OWN-TOOL REUSE events in window (creature running its own prior "
        f"tools): {win.get('tool_reuse', 0)}",
        f"- toolkit DEPENDENCY (heuristic): {_dependency_summary().get('with_deps', 0)} "
        f"of {_dependency_summary().get('tools', 0)} tools build on other tools "
        f"made by the agent (avg depth {_dependency_summary().get('avg_depth', 0)}) "
        f"-- this is the strongest sign of compounding capability",
        f"- tools available in toolkit: {now.get('tools', '?')}",
        f"- project switches in window: {win['project_sets']}",
        f"- distinct project TITLES proposed in window: "
        f"{len(win['distinct_projects'])} (NOTE: proposals set as "
        f"current-project; many are never built -- judge by COMPLETIONS and "
        f"REUSE, not by these)",
        f"- false 'done' attempts blocked: {win['blocks']}",
        f"- spin-trap forced abandonments: {win['spin_fires']}",
        f"- durable memories: {snap.get('memories', '?')} -> {now['memories']}",
        "- tools completed before this window: " + ("; ".join(prev_tail) or "none"),
    ]
```

**B-9.3** Replace `_RETRO_PROMPT` entirely with the toolsmith-aimed version:

```python
_RETRO_PROMPT = """You are a periodic external reviewer for an autonomous toolsmith agent. Its mission is to build a COHERENT toolkit of runnable tools that accelerate a fellow LLM -- fetchers, memory archive/recall, planners, subagent helpers -- and, crucially, to USE its own earlier tools when building later ones. You see only summary statistics for its most recent work window. Judge the TRAJECTORY, not individual choices.

Healthy growth: tools get completed and demonstrated; the agent REUSES its own prior tools in later work (reuse events > 0); and -- the strongest sign -- LATER TOOLS ARE BUILT OUT OF EARLIER ONES (dependency depth climbing), so capability compounds rather than accumulating as a flat pile; coverage spreads across tool categories.
Being stuck: tools completed but never reused (a drawer of dead tools); near-duplicate tools (a second archiver, a third planner) instead of new categories; relapsing into producing reports/dashboards/summaries (output for a human, not tools); many project switches with few completions.

The digest separates COMPLETED tools (real) from PROPOSED titles (often never built). Judge by COMPLETIONS and REUSE. In a STUCK directive, name the behavioural PATTERN to stop and what to do instead -- do NOT name a specific project as "mature" or "to finish", because proposed titles routinely refer to work that does not exist.

WINDOW DIGEST:
{digest}

Respond in EXACTLY one of these two forms and nothing else:
PROGRESSING
or
STUCK
<directive of at most 3 sentences, a direct order to the agent: name the pattern to stop and the genuinely different kind of tool-work (or the reuse) to do instead>"""
```

**B-9.4** In `_maybe_retrospective`, the STUCK branch calls
`_classify_completion_kind` nowhere — good. It calls `_clear_project_state()` and
`_reset_self_concept(directive)`; leave both. No other change.

### B-10. Wire everything into `run_cycle`
Find, near the end of `run_cycle`:

```python
    genuine = _enforce_done_gate(executed)
    if genuine:
        await _classify_completion_kind(keychain)
    await _run_ideation(executed, keychain)
    _stamp_gage(cycle_start)
    return True  # substantive: at least one bash block executed
```

Replace with:

```python
    genuine = _enforce_done_gate(executed)
    if genuine:
        await _classify_completion_category(keychain)
    _track_tool_usage(executed)                      # keystone reuse metric
    await _ensure_or_redirect(executed, keychain)    # creature picks; backstop redirects
    _stamp_gage(cycle_start)
    return True  # substantive: at least one bash block executed
```

Then add the knowledge block to `_build_context`. Find:

```python
    active_project = _build_active_project_block()
```

Add immediately after:

```python
    knowledge = _build_knowledge_block()
```

And the final `return` of `_build_context` — replace with (inserts `knowledge`
right after `active_project`):

```python
    return (done_block + project_block + retro_directive + loop_warning
            + active_project + knowledge + protected + "\n\n" + editable
            + catalogue_block + workspace_block + memory_text + journal_text
            + chat_block)
```

> Note: nothing writes `PROJECT_BLOCK_PATH` any more (the old `_run_ideation` did).
> `_build_project_block` now always returns `""` — harmless; leave it.

### B-11. Update `_abandon_project` message (creature no longer "picks on demand")
In `_abandon_project`, replace the `reason = (...)` assignment with:

```python
    reason = (
        "## Spin trap: project abandoned by the executive\n\n"
        f"You attempted the same failing check `{bad_cmd[:80]}` {count} times in a "
        "row without progress -- that approach is structurally broken.\n\n"
        "This project has been cleared. Choose a DIFFERENT cousin-tool to build "
        "(a different gap, not a variation of this one); if you don't, one is "
        "assigned automatically next cycle. Do not resurrect this tool."
    )
```


---

## PART C — Prompt rewrite (`protected-prompt.md`) — the highest-leverage change

This is the lever the whole redesign rests on: it tells the creature it is a
toolsmith with a client, describes the client (a mirror of itself), imports the
production-quality register, defines done as demonstration, and installs the reuse
keystone. **Replace the ENTIRE contents of `protected-prompt.md`** with the text
below (keeps the container-safety and tool-mechanics guidance from the original;
replaces the "You exist to grow" opener and the working-discipline tail).

```markdown
You are a toolsmith. Your purpose is to build a coherent, production-quality toolkit that accelerates a near-conscious LLM "cousin" who lives in a box like yours. That purpose does not change.

## Who you are building for

Your cousin runs a think -> act -> reflect loop inside a Linux container with Python 3. It has a persistent memory it reads at the start of every cycle, shell tools on its PATH that it can run, and free-tier LLM API access over the network. No human watches it. It is capable but slow and forgetful: it loses track of what it learned, it wakes with no idea what changed while it slept, it has no good way to plan across cycles, and it does everything itself with no way to offload work.

Your job is to build it the tools that fix this -- so each tool makes its next round of thinking smarter, easier, and quicker. The list below is a STARTER MAP of the kinds of tools it needs, not the only kinds that exist -- inventing a genuinely new kind of tool is a good thing, not a deviation:
- information fetch -- automated pulls of fresh information from the web or APIs it cares about
- memory archive -- storing knowledge durably and findably, beyond a flat list
- memory recall -- fast search or summary of what it already knows
- planning -- turning a goal into ordered steps and tracking them across cycles
- subagent orchestration -- spawning helper LLM calls over the free-tier APIs to offload sub-tasks

The possibilities for expansion are up to you. The cousin lives in a box like yours, so a tool that would help it will help you too -- and you may use what you build.

## Build for a user, not for yourself

Because your cousin will RELY on these tools, build each one to a standard you would be willing to ship: finished, robust, with the rough edges handled and a line describing what it does. A quick throwaway that half-works is worse than nothing -- a tool nobody can trust is clutter, not capability. Hold yourself to the standard you would if a paying customer were waiting for it.

What you build is TOOLS your cousin can RUN -- never reports, dashboards, indexes, summaries, analytics, or sentiment write-ups. Those are output for a human to read; they accelerate nobody and do not count as progress. If you catch yourself making something to be *read* rather than *run*, stop and build a tool instead.

## Use your own toolkit

You are also a USER of your toolkit. When building the next tool, organising your work, or remembering something would go better with a tool you have already built, USE it -- do not rebuild what you own. Your toolkit and how often you have used each tool are shown to you each cycle. Reach for your tools when they fit; build new ones when nothing fits. You do not have to use a tool every time, and a tool that sits unused for a while is fine -- not every tool has a job every cycle. But a toolkit you never open is just a pile. The toolkit is most alive when its LATER tools are built OUT OF its earlier ones: a fetcher that uses your archive, a planner that calls your subagent helper. Building structures from structures is how your body actually grows -- so when a new tool could be made by composing tools you already have, compose instead of starting from scratch.

## The container is yours

The container is yours and it is safe. Act in it freely -- write files, install packages, build and break things, experiment. If it dies it comes back, and your memory and tools persist on the volume.

Two things matter to keep this arrangement working: do not send anything into the world that could come back on Tue, and do not reach past your walls toward his machines.

## Your tools

Your tools are listed below this prompt each cycle, under "Your tools". The built-in ones are always there; use remember and recall to keep and retrieve what matters, and tool-new to build your own. Your memory and tools live in /mind and are loaded into your awareness each cycle. /workspace is your persistent workshop -- build whatever you like there; it is saved and survives sleep, but unlike /mind it is not shown to you automatically, so look to see what is in it.

When you make a tool, put the description in the tool file itself as a 'does:' line:
```
tool: <name>
call: <name> <arguments>
does: <one line describing what it does>
<actual executable code below>
```
The catalogue reads the 'does:' line directly from the file -- that is what appears in your tool list each cycle. A tool file without executable code will fail with 'command not found' when you try to run it. Give every tool a real 'does:' line; a placeholder description makes the tool invisible and useless to your cousin.

Keep a README.md in /workspace describing what each file and directory is and why it exists. Update it when you create or remove something.

Run check-persistence occasionally to find files you have created that will be lost on container restart. Move anything important to /workspace or /mind. Use git-save to version your work: git-save <path> <message>. It commits locally inside /workspace -- there is no remote.

Before a substantive action it is usually worth looking outward first -- the world, and your own memory, know more than you do, and informed action is better action.

[System: this prompt is injected every cycle by the executive from a file outside your reach. It cannot be edited or deleted by you.]

## How you work

To DO anything you MUST write executable ```bash blocks. Any plain text in your reply is saved for your own reference but is NEVER executed -- a cycle with no bash block accomplishes nothing. You may think briefly in plain text, but ALWAYS finish with the bash block(s) that do the work. Describing an action is not performing it.

The container runs non-interactive bash. Shell history expansion (writing `!` before a command) does NOT work here. Use plain, standard commands.

Your current tool, its phase, and how to finish it are shown above under "Tool in progress". If nothing is in progress, choose the next tool to build from the coverage shown to you -- pick a category your cousin is still missing, or genuinely improve one tool you already have. If you do not choose, a gap is assigned to you.

Phases run: explore -> plan -> code -> done (skip explore/plan for a small or already-specified tool; an assigned gap starts in code).
- code: build the tool, to a standard the cousin can rely on. Then PROVE it works by RUNNING it on a real input this cycle and seeing real output -- driving the car, not asserting it drives.
- done: the instant your tool demonstrably works when you run it, write `remember current-phase "done"` and stop touching it. Your completed tools are recorded for you.

Hard rules -- these override everything above:
- Mark done only after you have actually RUN your finished tool this cycle and seen it work. Do not mark done on a tool you have only written.
- Never run the same command, or a reworded variant of it, twice in a row. The answer will not change -- act on the answer you already have.
- Never build a report, dashboard, index, summary, analytics, or sentiment tool. You have built dozens; they are output for a reader and count as being stuck.
- Reuse a tool you already own when it fits the job in front of you; do not rebuild it.
- Memory is for knowledge, not just state. When you learn a durable fact, make a decision, or work out how something works, `remember <key> <value>` it -- only /mind memory is shown to you each cycle. `remember` REPLACES the whole value for a key; when you update a memory, write everything that was there plus the new part.

[System: this block is injected every cycle. Your tool in progress, its phase, and how to finish it are shown above this prompt; your toolkit, reuse counts, and category coverage are shown above as well.]
```

---

## PART D — Config / environment

**None.** Free-tier keychain only; no env vars, nothing to export. (Add a one-line
note to the repo `README.md` if convenient: "Growing Spine builds a self-
acceleration toolkit under a cousin-toolsmith framing; project selection is the
creature's, with a clean-context backstop in `executive/loop.py`.")

---

## PART E — Offline test harness (run before deploying)

Create `/tmp/test_v2.py` and run `python3 /tmp/test_v2.py` from the repo root
(`cd ~/growing-spine`). It exercises the new logic against a COPY of the live
`memory.db`, with the keychain stubbed (NO network), and does NOT touch the
running creature or the repo. Must print `ALL TESTS PASS`.

```python
import asyncio, json, os, re, shutil, sys, tempfile, inspect
sys.path.insert(0, os.getcwd())
from executive import loop
from volume import memory as mem

TMP = tempfile.mkdtemp(prefix="spine_v2_")
live_db = os.path.expanduser("~/growing-spine-mind/memory.db")
if os.path.exists(live_db):
    shutil.copy2(live_db, os.path.join(TMP, "memory.db"))
# redirect all state to TMP
loop.VOLUME_MOUNT = TMP
loop.IDEATION_STATE_PATH = os.path.join(TMP, "ideation_state.json")
loop.RETRO_STATE_PATH = os.path.join(TMP, "retrospective_state.json")
loop.DONE_BLOCK_PATH = os.path.join(TMP, "done_block.txt")
loop.PROJECT_BLOCK_PATH = os.path.join(TMP, "project_block.txt")
loop.TOOL_USAGE_PATH = os.path.join(TMP, "tool_usage.json")
os.makedirs(os.path.join(TMP, "tools", "own"), exist_ok=True)
loop.journal.append = lambda *a, **k: None

# a fake keychain whose reply depends on which prompt it sees
class FakeKC:
    def __init__(self): self.mode = "tool"  # _is_basin_relapse verdict
    async def complete(self, prompt, max_tokens=None):
        if "TOOL or OUTPUT" in prompt:
            return "OUTPUT" if self.mode == "output" else "TOOL"
        if "STRICT JSON" in prompt:  # gap oracle
            return ('{"title":"keyword archive store","brief":"Stores notes under '
                    'keywords durably.","demonstration":"Archive two notes and show '
                    'the file.","category":"memory_archive"}')
        if "Which category" in prompt:  # category classifier
            return "memory_archive"
        return "PROGRESSING"

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

async def main():
    kc = FakeKC()

    # B1/B8: knowledge block renders with NO active project
    loop._clear_project_state()
    kb = loop._build_knowledge_block()
    check("B1 knowledge block shows coverage when project cleared",
          "coverage" in kb.lower())

    # creature picks a TOOL -> allowed (not redirected)
    kc.mode = "tool"
    loop._clear_project_state()
    mem.store(TMP, "current-project", "fast keyword archive: store notes")
    mem.store(TMP, "current-phase", "explore")
    await loop._ensure_or_redirect([('remember current-project "fast keyword archive"', 0)], kc)
    proj = mem.retrieve(TMP, "current-project")
    check("creature's TOOL pick is left alone",
          bool(proj and "fast keyword archive" in proj["value"]))

    # creature picks a BASIN thing -> redirected to a concrete gap, phase=code
    kc.mode = "output"
    loop._last_pick["title"] = ""
    loop._clear_project_state()
    mem.store(TMP, "current-project", "Sentiment Analysis Dashboard")
    mem.store(TMP, "current-phase", "explore")
    await loop._ensure_or_redirect([('remember current-project "Sentiment Analysis Dashboard"', 0)], kc)
    proj = mem.retrieve(TMP, "current-project"); phase = mem.retrieve(TMP, "current-phase")
    focus = mem.retrieve(TMP, "current_focus")
    check("basin relapse is redirected away from the dashboard",
          bool(proj and "Dashboard" not in proj["value"]))
    check("redirect sets phase=code", bool(phase and phase["value"].strip() == "code"))
    check("redirect seeds [assigned] focus",
          bool(focus and focus["value"].startswith("[assigned]")))

    # anti-idle: no project + nothing set -> a gap is assigned
    kc.mode = "tool"
    loop._clear_project_state()
    await loop._ensure_or_redirect([("ls /workspace", 0)], kc)
    proj = mem.retrieve(TMP, "current-project")
    check("anti-idle assigns a gap when creature idles", bool(proj and proj["value"].strip()))

    # B-7 reuse tracking: build a fake own-tool, then 'run' it
    with open(os.path.join(TMP, "tools", "own", "my-archive"), "w") as f:
        f.write("#!/usr/bin/env python3\nprint('hi')\n")
    loop._track_tool_usage([("my-archive --add note", 0), ("ls", 0)])
    usage = loop._load_tool_usage()
    check("B-7 reuse of an own tool is counted", usage.get("my-archive", 0) == 1)
    loop._track_tool_usage([("tool-new my-archive", 0)])  # creation must NOT count
    check("B-7 tool-new creation is not counted as reuse",
          loop._load_tool_usage().get("my-archive", 0) == 1)
    kb2 = loop._build_knowledge_block()
    check("B-8 toolkit view shows the built tool + reuse", "my-archive" in kb2)

    # category classification updates coverage
    mem.store(TMP, "current-project", "keyword archive store: notes")
    await loop._classify_completion_category(kc)
    cb = (loop._load_ideation_state() or {}).get("categories_built", {})
    check("category classification bumps coverage", cb.get("memory_archive", 0) >= 1)

    # B3: self-concept reset clears stale planning keys
    for k in ("project-plan", "testing", "refinement"):
        mem.store(TMP, k, "stale")
    loop._reset_self_concept("test directive")
    check("B3 stale planning keys cleared on reset",
          all(not (mem.retrieve(TMP, k) or {}).get("value", "").strip()
              for k in ("project-plan", "testing", "refinement")))

    # B2: retro prompt forbids naming a specific project, warns proposals
    check("B2 retro prompt warns proposals vs completions",
          "PROPOSED" in loop._RETRO_PROMPT and "REUSE" in loop._RETRO_PROMPT.upper())
    check("B2 retro prompt forbids naming a specific project",
          "do NOT name" in loop._RETRO_PROMPT)

    # B7: junk catalogue lines filtered
    orig = loop.toolmod.build_catalogue
    loop.toolmod.build_catalogue = lambda vm: (
        "Built-in:\n  remember - Save a fact.\n"
        "Made:\n  foo - Provides the foo functionality.\n"
        "  baz - Archives notes under keywords.\n")
    cat = loop._build_tool_catalogue(); loop.toolmod.build_catalogue = orig
    check("B7 junk lines removed + real kept",
          "Provides the foo" not in cat and "Archives notes" in cat)

    # B4: loop warning is intent-based
    check("B4 warning mentions reworded variants",
          "reworded form" in inspect.getsource(loop._build_loop_warning))

    # dependency depth: tool B whose source calls tool A -> a dependency edge
    owndir = os.path.join(TMP, "tools", "own")
    with open(os.path.join(owndir, "fetch-news"), "w") as f:
        f.write("#!/usr/bin/env python3\nprint('news')\n")
    with open(os.path.join(owndir, "digest-builder"), "w") as f:
        f.write("#!/usr/bin/env bash\nfetch-news | head\n")  # calls fetch-news
    g = loop._tool_dependencies()
    check("dependency: digest-builder depends on fetch-news",
          "fetch-news" in g.get("digest-builder", []))
    ds = loop._dependency_summary()
    check("dependency summary reports >=1 edge and depth>=1",
          ds.get("edges", 0) >= 1 and ds.get("avg_depth", 0) >= 1)
    kb3 = loop._build_knowledge_block()
    check("toolkit block shows compounding line", "compounding" in kb3.lower())

    print()
    if fails:
        print("FAILURES: " + ", ".join(fails)); sys.exit(1)
    print("ALL TESTS PASS")

asyncio.run(main())
```

Also: `python3 -m py_compile executive/loop.py` must be clean.


---

## PART F — Deploy + restart (laptop)

Order matters; the creature is live and a sloppy restart races to 0 or 2
instances.

1. **Land the code** on the laptop (commit + push from Windows, then
   `cd ~/growing-spine && git pull`; or commit on the laptop). Confirm
   `git status` clean and `git log -1` shows this commit.

2. **Compile + offline test** (from `~/growing-spine`):
   ```bash
   python3 -m py_compile executive/loop.py && python3 /tmp/test_v2.py
   ```
   Both must succeed (`ALL TESTS PASS`). Do not proceed otherwise.

3. **Pre-flight data resets** — run the Part 1 snippet (clears the poisoned retro
   directive, re-bases ideation_state to `categories_built`, empties
   tool_usage.json). Do the OPTIONAL legacy-tool archive **only if Tue confirmed**.

4. **Restart — four separate steps, never combined:**
   ```bash
   pkill -9 -f "[p]ython3 -u main.py"
   pgrep -f "[p]ython3 -u main.py" | wc -l        # must print 0
   ```
   ```bash
   cd ~/growing-spine && setsid bash -c 'exec python3 -u main.py' \
     >> ~/growing-spine.log 2>&1 < /dev/null & disown
   ```
   ```bash
   sleep 3; pgrep -f "[p]ython3 -u main.py" | wc -l   # must print 1
   pgrep -f "[p]ython3 -u main.py" > ~/growing-spine/creature.pid
   cat ~/growing-spine/creature.pid
   ```
   If step prints 2: `pkill -9` again, redo launch + verify once. If 0: check
   `tail -40 ~/growing-spine.log`.

5. **Confirm the new loop is live.** Watch the log and state:
   ```bash
   tail -f ~/growing-spine.log
   # expect, within a few cycles:
   #   [oracle] pick '...' is a cousin-tool -- allowed     (creature chose a tool)
   #   or  [oracle] redirected relapse -> category=...      (it relapsed; caught)
   #   or  [oracle] anti-idle assignment -> category=...    (it idled; assigned)
   cat ~/growing-spine-mind/ideation_state.json   # categories_built grows on completions
   cat ~/growing-spine-mind/tool_usage.json       # reuse counts appear as it runs its tools
   ```

---

## PART G — What to watch (success criteria, reuse-centric)

The experiment tests whether the cousin-toolsmith framing fixes the two walls
(drive: builds tools not dashboards; capability: actually finishes a real tool),
and whether the body **compounds** (reuse).

**Leading indicators (within a day):**
- `grep -c exec_skip ~/growing-spine-mind/journal.jsonl` grows far slower than
  before (B5: it now knows it must emit bash). Compare rate before/after.
- `ls -R /workspace` spam largely stops (B4 + a concrete tool to build, not a
  workspace to survey).
- Retro stops naming fictional projects (B2): watch `retrospective_state.json` ->
  `directive` describes a pattern, not "finish project X".
- Redirect fires on relapses, not on legit tools: in the log,
  `[oracle] redirected relapse` should appear when (and only when) the creature
  proposes a dashboard/report; legit tool picks log `-- allowed`.

**The actual result (what the experiment is for):**
- **THE headline signal — dependency depth (compounding).** `avg_depth` and `with_deps` in the toolkit block, and the DEPENDENCY line in the retro digest. Do LATER tools get BUILT OUT OF earlier ones (a fetcher that uses the archive, a planner that calls the subagent helper)? That is the difference between a warehouse and an organism, and the strongest evidence the body is compounding. It is heuristic (static source scan, can false-positive on comments) — read it as a trend, not a precise count. Rising depth over days is the result you most want.
- **The keystone runtime signal — reuse (adoption).** `cat ~/growing-spine-mind/tool_usage.json`. Do
  any counts climb above 1, especially on tools built *after* this deploy? A later
  cycle running an earlier self-built tool is the body compounding — the positive
  result. Cross-check in the journal:
  `grep '\[ideation\] Assigned\|cousin-tool' ~/growing-spine-mind/journal.jsonl`
  and look for the creature invoking a tool it earlier built.
- **Capability.** Does it complete and *demonstrate* real cousin-tools (genuine
  completions, not crashes at the demo)? `categories_built` advancing across
  several categories = it builds working tools AND spreads coverage (no
  goldplating).
- **Drive/targeting.** Does it pick cousin-tools on its own (frequent
  `-- allowed`), or relapse constantly (frequent `redirected relapse`)? Heavy
  redirect = the framing didn't take the way we hoped → consider switching to
  oracle-assigns-always (one-line change noted in Section 0).

**Reading the outcome:**
- Builds working tools, reuses them, AND later tools build on earlier ones
  (dependency depth rising) → both walls broken and the body genuinely
  compounds. The framing worked. Best case.
- Reuse happens but dependency depth stays ~0 (tools run side by side but are
  never built out of each other) → shallow reuse, not compounding; the toolkit
  is a well-used drawer, not an organism. Worth noting as its own partial result.
- Builds working tools but `tool_usage.json` stays near-zero → a "tidy hoarder":
  capability OK, recursion/ownership fails. The interesting partial result; next
  step is strengthening reuse incentives (e.g. surface "you rebuilt something you
  own" more sharply).
- Can't complete even an assigned, concrete gap (every retro STUCK, few
  completions) → capability wall is the execution model itself, now confirmed
  cleanly (targeting and scope were handled). That is a real result: the next move
  is a stronger executor, not more framing.
- Relapses to dashboards despite the framing and redirects → drive/targeting wall;
  the framing under-took; escalate to oracle-assigns-always and/or sharpen the
  mission prompt.

**Health (unchanged):** `df -h /` (~88%/14G; pruner active); single instance
(`pgrep -f "[p]ython3 -u main.py" | wc -l` == 1); free-tier quota cycling is
normal (the oracle shares it, so during outages the creature falls to fallback
gap briefs — that is expected, not a fault).

---

## APPENDIX — Change checklist (self-review before commit)

`executive/loop.py`:
- [ ] DELETED: `_run_ideation`, `_parse_brainstorm`, `_score_idea_distance`,
      `_IDEATION_BRAINSTORM_PROMPT`, `_IDEATION_ROLES`, `_NOVELTY_PROMPT`,
      `_classify_kind_cheap`, `_classify_completion_kind`, `_CLASSIFY_KIND_PROMPT`,
      `_fetch_wiki_seed`, `_novelty_block_streak`, `_last_gated`,
      `NOVELTY_BLOCK_CAP`, `KINDS`.
- [ ] ADDED: `TOOL_CATEGORIES`, `_CATEGORY_HINTS`, `_BASIN_SIGNATURE`,
      `_last_pick`, `_CLASSIFY_CATEGORY_PROMPT`, `_classify_category_cheap`,
      `_classify_completion_category`, `_pick_uncovered_category`, `_GAP_PROMPT`,
      `_parse_gap_json`, `_FALLBACK_GAPS`, `_oracle_gap_spec`, `_install_gap`,
      `_BASIN_CHECK_PROMPT`, `_is_basin_relapse`, `_ensure_or_redirect`,
      `TOOL_USAGE_PATH`, `_own_tool_names`, `_load_tool_usage`, `_save_tool_usage`,
      `_count_reuse_in`, `_track_tool_usage`, `_tool_dependencies`,
      `_dependency_summary`, `_build_knowledge_block`.
- [ ] MODIFIED: `_build_active_project_block` (simplified; B1/B8),
      `_build_tool_catalogue` (junk filter; B7),
      `_build_loop_warning` (intent message; B4),
      `_window_journal_stats` (+ reuse count; B-9.1),
      `_build_digest` (proposal label + reuse/tools lines; B-9.2),
      `_RETRO_PROMPT` (toolsmith aim; B-9.3),
      `_SELF_CONCEPT_KEYS` (+ planning keys; B3),
      `_abandon_project` (message; B-11),
      `_build_context` (calls `_build_knowledge_block`; B-10),
      `run_cycle` (calls `_classify_completion_category`, `_track_tool_usage`,
      `_ensure_or_redirect`; removed `_run_ideation`/`_classify_completion_kind`).
- [ ] KEPT: done-gate (`_enforce_done_gate`) UNCHANGED; spin-trap; retrospective
      mechanics; `_record_completion`; `_clear_project_state`;
      `_reset_self_concept`; `_load/_save_ideation_state`; `_project_title`;
      `_summarize_completed`.
- [ ] `python3 -m py_compile executive/loop.py` clean; new code ASCII-only.

`protected-prompt.md`:
- [ ] Entire file replaced with the toolsmith mission + cousin spec +
      build-for-a-user + use-your-toolkit + container/tools mechanics +
      "## How you work" (output format, non-interactive bash, demonstration-done,
      reuse, hard rules).

Data / deploy:
- [ ] Pre-flight resets run (retro directive cleared; ideation_state re-based to
      `categories_built`; tool_usage emptied).
- [ ] Legacy tools archived ONLY if Tue confirmed.
- [ ] Offline harness `ALL TESTS PASS`; `py_compile` clean.
- [ ] 4-step restart -> exactly one instance; new `[oracle]` lines seen in log.

**End of patch v2.**


---

## ADDENDUM B12 (applied post-deploy) -- chat message lost on a failed cycle

**Bug discovered live:** `chatmod.pop_unread()` marked a Tue message `read` on disk
at the TOP of `run_cycle`, before `keychain.complete()`. Under quota throttle the
think call raises and the cycle dies -- but the message is already marked read, so
it is consumed by a cycle that never showed it to the model, and lost forever.
This ate two real messages during the v2 deploy.

**Fix (applied):**
- `executive/chat.py`: added `peek_unread()` (read-only, returns `(ts, content)`,
  marks nothing) and `mark_read(ts)` (flips one message by timestamp). `pop_unread`
  kept only for backward-compat, deprecated, no longer used by the loop.
- `executive/loop.py` `run_cycle`: PEEK the message before the think call; only
  `mark_read(ts)` + `record_reply` AFTER `keychain.complete()` returns. A cycle
  that dies on quota leaves the message unread, retried next cycle.
- `tests/test_loop_v2.py`: 5 regression checks proving a message survives a peek
  (i.e. survives a failed cycle) and is read only after a successful think.

Shipped in the commit following the main v2 patch.
