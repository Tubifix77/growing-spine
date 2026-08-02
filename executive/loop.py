"""
loop.py Ã¢ÂÂ the executive loop, step 4: wake/sleep runtime wired in.
"""
import asyncio, os, time, re, json
from collections import Counter
from . import sandbox, journal, parser
from .runtime import (managed_exec, ensure_body, wake_entry,
                      sleep_entry, sleep_duration_seconds)
from keychain import Keychain
from volume import memory as mem
from volume import savegame
from volume import tools as toolmod
from executive import chat as chatmod
from executive import self_restart as _selfrestart

VOLUME_MOUNT = os.path.expanduser("~/growing-spine-mind")
EDITABLE_PROMPT_PATH = os.path.join(VOLUME_MOUNT, "editable-prompt.md")
PROTECTED_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "protected-prompt.md")
SAVEGAME_ROOT = os.path.expanduser("~/growing-spine-saves")
DONE_BLOCK_PATH = os.path.join(VOLUME_MOUNT, "done_block.txt")
PROJECT_BLOCK_PATH = os.path.join(VOLUME_MOUNT, "project_block.txt")
WORKSPACE_DIR = os.path.expanduser("~/growing-spine-workspace")
RETRO_STATE_PATH = os.path.join(VOLUME_MOUNT, "retrospective_state.json")
RETRO_INTERVAL = 20      # real creature cycles between retrospectives
DIRECTIVE_WINDOW = 20    # cycles a STUCK directive stays in every prompt

# v0.8 composition phase: once every seed category has at least this many tools,
# the toolsmith has finished BREADTH (covering the basics) and the highest-value
# work shifts to DEPTH -- building tools that COMPOSE existing tools into larger
# capabilities. Below the threshold the oracle fills category gaps (breadth mode);
# at or above it the oracle briefs composition tools (depth mode). 3 is enough to
# prove a category is genuinely covered, not just touched once.
COMPOSITION_THRESHOLD = 3

# Sentinel returned by the oracle when it can produce no genuinely NEW work this
# cycle (LLM unavailable AND the only fallback would rebuild an existing tool).
# The caller treats this as "rest, don't spin" -- assign nothing and let the
# cycle pass, rather than burning effort rebuilding a tool that already exists.
_REST_SENTINEL = {"__rest__": True}

# idea_gate: conception-stage duplicate/extend gate (executive/idea_gate.py).
# "shadow" = compute + LOG a verdict on each newly-conceived idea but NEVER act
# (safe live observation); "active" = also redirect DUPLICATE/EXTEND ideas onto
# the existing tool; "off" = disabled. Starts in shadow: observable live with
# zero risk, flip to "active" is a one-line change once the shadow log shows it
# judging correctly. Always fails open (any error -> idea proceeds ungated) and
# only runs when a provider is available (never adds a probe during a wall).
IDEA_GATE_MODE = "active"  # flipped 2026-07-30 after 16 days of shadow (Tue: "lets go")

# v0.9 batch-ideation: the binding constraint is API CALLS, not tokens -- one
# call returning N composition ideas costs the same as one returning 1. So in
# depth mode the oracle generates a SMALL BATCH in a single call, caches it, and
# feeds one idea per cycle until empty, then refills. This cuts oracle call
# frequency ~3x, so the gap-finder rarely hits the quota wall and rarely falls
# back to the stale static fallbacks. Batch size is deliberately SMALL: a free-
# tier model produces ~10-15 genuinely-distinct, grounded composition ideas, then
# starts (a) recycling the same tool-pair with new verbs and (b) drifting into a
# fictional devops/production frame to manufacture novelty. Measured directly by
# pasting the real N=100 prompt into Gemini Flash: distinctness held to ~item 15,
# then collapsed to ~5 archetypes reskinned. 10 sits inside the good zone with a
# margin and gives a ~10x call saving. Refill regenerates from the CURRENT toolkit,
# so the combination space grows as the creature builds, keeping later batches
# fresher than a one-shot test. Breadth mode is NOT batched -- it is category-
# driven, one uncovered category at a time, where batching does not fit.
COMPOSITION_BATCH_SIZE = 10
COMPOSITION_QUEUE_PATH = os.path.join(VOLUME_MOUNT, "composition_queue.json")

IDEATION_STATE_PATH = os.path.join(VOLUME_MOUNT, "ideation_state.json")

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

# --- Systematic rut detection + auto-yank -----------------------------------
# The per-pick basin redirect (_is_basin_relapse -> _ensure_or_redirect) catches
# ONE relapsing pick at a time, but has no memory of REPETITION: the creature can
# propose the same basin theme every cycle, get gently redirected each time, and
# never actually leave the basin (observed: a multi-day "sentiment/report" rut
# that every single-pick guard failed to break). This adds a scoreboard: count
# CONSECUTIVE relapses on the SAME theme, and once confirmed (>= threshold) fire
# an ESCALATED, self-generated yank that names the rut, forbids the theme, and
# sets a cooldown so picks matching it are hard-blocked for a window.
BASIN_YANK_THRESHOLD = 3      # consecutive same-theme relapses that CONFIRM a rut
BASIN_COOLDOWN_CYCLES = 12    # how long the confirmed theme stays banned after a yank


def _basin_theme_of(text: str) -> str:
    """Which basin keyword a proposal trips, '' if none. First match wins so the
    theme is stable across cycles (lets us tell 'same rut' from 'new rut')."""
    t = (text or "").lower()
    for kw in _BASIN_SIGNATURE:
        if kw in t:
            return kw
    return ""


def _record_basin_relapse(theme: str) -> int:
    """Bump the consecutive-relapse streak for `theme`. Resets to 1 if the theme
    changed (a different rut) or was empty. Returns the new streak length.
    Persisted in ideation_state so it survives restarts."""
    state = _load_ideation_state() or {}
    prev_theme = state.get("basin_theme", "")
    streak = int(state.get("basin_relapse_streak", 0))
    if theme and theme == prev_theme:
        streak += 1
    else:
        streak = 1
    state["basin_theme"] = theme
    state["basin_relapse_streak"] = streak
    _save_ideation_state(state)
    return streak


def _reset_basin_streak():
    """Clear the streak after a non-relapse pick or once a yank has been issued."""
    state = _load_ideation_state() or {}
    if state.get("basin_relapse_streak") or state.get("basin_theme"):
        state["basin_relapse_streak"] = 0
        state["basin_theme"] = ""
        _save_ideation_state(state)


def _banned_theme_active() -> str:
    """The currently cooling-down banned theme, '' if none / expired. Decrements
    the remaining cooldown each call (called once per cycle from the redirect)."""
    state = _load_ideation_state() or {}
    theme = state.get("banned_theme", "")
    left = int(state.get("banned_cooldown_left", 0))
    if not theme or left <= 0:
        if theme or left:
            state["banned_theme"] = ""; state["banned_cooldown_left"] = 0
            _save_ideation_state(state)
        return ""
    state["banned_cooldown_left"] = left - 1
    _save_ideation_state(state)
    return theme


def _arm_theme_ban(theme: str):
    """Record `theme` as banned for BASIN_COOLDOWN_CYCLES, and clear the streak
    that triggered the yank."""
    state = _load_ideation_state() or {}
    state["banned_theme"] = theme
    state["banned_cooldown_left"] = BASIN_COOLDOWN_CYCLES
    state["basin_relapse_streak"] = 0
    state["basin_theme"] = ""
    _save_ideation_state(state)


def _basin_yank_focus(theme: str, streak: int) -> str:
    """The escalated, self-generated yank message. Stronger than the normal
    per-pick redirect: names the confirmed rut explicitly and forbids the theme."""
    return (
        f"STOP. You have now proposed a '{theme}'-flavoured project {streak} times "
        f"in a row, and each was redirected. This is a confirmed rut. Your cousin "
        f"does not need another '{theme}' tool -- that whole area is covered and "
        f"every attempt is wasted effort. For the next several cycles, do NOT "
        f"build anything involving {theme}, dashboards, reports, summaries, or "
        f"analytics of any kind. Instead build something in a DIFFERENT domain "
        f"entirely: a tool that transforms or restructures data, solves a concrete "
        f"problem end to end, automates a multi-step task, or gives the cousin a "
        f"capability it genuinely lacks. Pick something you have never built and "
        f"make it real."
    )

_last_pick = {"title": ""}  # last project the creature set (skip re-judging refinements)



def _load_protected_prompt() -> str:
    if not os.path.exists(PROTECTED_PROMPT_PATH):
        return ""
    with open(PROTECTED_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_editable_prompt() -> str:
    if not os.path.exists(EDITABLE_PROMPT_PATH):
        return ""
    with open(EDITABLE_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _build_memory_context() -> str:
    try:
        l1 = mem.layer1(VOLUME_MOUNT)
        l2 = mem.layer2_headlines(VOLUME_MOUNT)
        l3 = mem.layer3_themes(VOLUME_MOUNT)
    except Exception:
        return ""

    parts = []

    if l1:
        lines = [f"  [{m['key']}] {m['value'][:200]}" for m in l1]
        parts.append("Working memory (most recent):\n" + "\n".join(lines))

    if l2:
        headlines = [f"  {m['key']}: {m['headline']}" for m in l2]
        parts.append("Older memories:\n" + "\n".join(headlines))

    if l3:
        parts.append("Archived themes: " + ", ".join(l3))

    return ("\n\n" + "\n\n".join(parts)) if parts else ""


# Journal kinds worth showing the creature — its thoughts and results,
# not executive plumbing (think_start, wake, sleep, exec_start, exec_skip).
MEANINGFUL_KINDS = {"think_end", "exec_end", "error", "exec_timeout",
                    "respawn", "death", "birth"}


def _load_workspace_map() -> str:
    """Read /workspace/README.md from the container if it exists."""
    try:
        import subprocess
        from executive.sandbox import CONTAINER_NAME
        r = subprocess.run(
            ["docker", "exec", CONTAINER_NAME,
             "cat", "/workspace/README.md"],
            capture_output=True, text=True, errors="replace", timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return ""


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



def _build_done_block() -> str:
    """One-shot injection: if the executive blocked a false 'done' last cycle,
    tell the creature exactly what failed. Read-and-delete, so it shows for one
    cycle and renews itself only if the creature marks done falsely again."""
    try:
        if os.path.exists(DONE_BLOCK_PATH):
            with open(DONE_BLOCK_PATH, encoding="utf-8") as f:
                reason = f.read().strip()
            os.remove(DONE_BLOCK_PATH)
            if reason:
                return "## Done check failed\n" + reason + "\n\n"
    except Exception:
        pass
    return ""


def _build_project_block() -> str:
    """One-shot injection: if the novelty gate blocked a duplicate project last
    cycle, tell the creature what it duplicated and that it must pick something
    new. Read-and-delete (shows for one cycle)."""
    try:
        if os.path.exists(PROJECT_BLOCK_PATH):
            with open(PROJECT_BLOCK_PATH, encoding="utf-8") as f:
                reason = f.read().strip()
            os.remove(PROJECT_BLOCK_PATH)
            if reason:
                return "## Project selection blocked\n" + reason + "\n\n"
    except Exception:
        pass
    return ""


def _summarize_completed(entries: list) -> str:
    """Cheap, deterministic synthesis of the completed-log so its REDUNDANCY is
    visible at a glance instead of buried in a flat list of near-duplicate
    titles -- the creature kept rebuilding because it had a list, not an overview."""
    if not entries:
        return ""
    groups = {
        "reports / indexes / dashboards": ("report", "index", "dashboard",
                                           "summary", "overview", "stats", "monitor"),
        "todo / fixme trackers": ("todo", "fixme"),
        "tool docs / workspace admin": ("tool", "doc", "workspace", "archive",
                                        "organiz", "persist", "validation"),
    }
    counts = {g: 0 for g in groups}
    other = 0
    for e in entries:
        el = e.lower()
        for g, kws in groups.items():
            if any(k in el for k in kws):
                counts[g] += 1
                break
        else:
            other += 1
    parts = [f"{g} ({n})" for g, n in counts.items() if n]
    if other:
        parts.append(f"other ({other})")
    return (f"You have already completed {len(entries)} projects, concentrated in: "
            + ", ".join(parts) + ".")


DONE_MARK_RE = re.compile(r'remember\s+current-phase\s+["\']?done["\']?', re.I)
PROJECT_SET_RE = re.compile(r'remember\s+current-project\b', re.I)
PHASE_EXPLORE_RE = re.compile(r'remember\s+current-phase\s+["\']?explore["\']?', re.I)

# Spin trap: track consecutive done-gate blocks on the same failing command.
# When the same DONE-WHEN check fails SPIN_THRESHOLD times in a row the approach
# is structurally broken; the executive clears the project and forces a fresh start.
_done_gate_streak: dict = {"cmd": "", "count": 0}
SPIN_THRESHOLD = 5


def _project_title(value: str) -> str:
    """Readable project title: text before the first ':' (or the whole line)."""
    if not value:
        return ""
    head = value.split(":", 1)[0] if ":" in value else value
    return head.strip()[:80]


def _record_completion():
    """On a genuine completion (done asserted, no failed checks), append the
    project title to a durable, executive-owned log. The creature overwrites its
    own completed-projects key and loses history; completed-log accumulates
    reliably and is shown in the active-project block."""
    try:
        proj = mem.retrieve(VOLUME_MOUNT, "current-project")
        title = _project_title(proj["value"]) if proj else ""
        if not title:
            return
        log = (mem.retrieve(VOLUME_MOUNT, "completed-log") or {}).get("value", "")
        entries = [e.strip() for e in log.split("\n") if e.strip()]
        if title not in entries:
            entries.append(title)
            mem.store(VOLUME_MOUNT, "completed-log", "\n".join(entries))
    except Exception:
        pass



def _clear_project_state():
    try:
        if os.path.exists(GATE_CHOICE_STATE_PATH):
            os.remove(GATE_CHOICE_STATE_PATH)  # never leave an armed check on a dead project
    except OSError:
        pass
    """Force-clear the creature's project control keys. Used by the spin trap
    and the retrospective. store("") is a real UPDATE; the context builders
    treat empty values as absent (F2)."""
    for key in ("current-project", "current-phase", "current-plan",
                "current-project-done-when"):
        try:
            mem.store(VOLUME_MOUNT, key, "")
        except Exception:
            pass


# Self-direction / identity memories. These (NOT the project control keys) are
# what re-anchor the creature to a dead project family: written early, never
# decaying, surfaced every cycle as working memory. The retro cleared the
# PROJECT on STUCK but the self-concept survived and rebuilt the same basin
# (59h / 39 STUCK / 0 PROGRESSING, unmoved even by a full workspace+tool wipe).
# Knowledge/capability memories (tool facts, learned-pattern, the `purpose`
# north-star) are deliberately absent -- we reset DIRECTION, not KNOWLEDGE.
_SELF_CONCEPT_KEYS = (
    "current_focus", "today_focus", "objective", "next_steps", "next_action",
    "plan", "instruction", "documentation.policy",
    "last-completed", "last-project", "last_completed_project", "last_thought",
    # added: per-project planning keys that re-anchored the creature to a cleared
    # project's basin after a retro/spin clear.
    "project-plan", "current-plan", "testing", "refinement",
    "project-done-when", "current-project-done-when", "assignment-note",
)


def _reset_self_concept(directive: str):
    """On STUCK: forget the self-direction memories and seed a fresh
    high-recency focus carrying the reviewer's redirection, so working memory
    LEADS with 'break out', not the retired project. store() on a freshly
    deleted key INSERTs with a new max id -> it lands at the top of layer1."""
    forgotten = []
    for key in _SELF_CONCEPT_KEYS:
        try:
            if mem.forget(VOLUME_MOUNT, key):
                forgotten.append(key)
        except Exception:
            pass
    try:
        mem.store(VOLUME_MOUNT, "current_focus", "[reset] " + directive)
    except Exception:
        pass
    if forgotten:
        journal.append(VOLUME_MOUNT, "retro",
                       "Self-concept reset on STUCK -- forgot: "
                       + ", ".join(forgotten))


def _abandon_project(bad_cmd: str, count: int):
    """Spin trap fired: force-clear the current project and demand
    a genuinely different goal. The creature has been stuck on the
    same broken approach for SPIN_THRESHOLD consecutive cycles."""
    try:
        _clear_project_state()
    except Exception:
        pass
    reason = (
        "## Spin trap: project abandoned by the executive\n\n"
        f"You attempted the same failing check `{bad_cmd[:80]}` {count} times in a "
        "row without progress -- that approach is structurally broken.\n\n"
        "This project has been cleared. Choose a DIFFERENT cousin-tool to build "
        "(a different gap, not a variation of this one); if you don't, one is "
        "assigned automatically next cycle. Do not resurrect this tool."
    )
    try:
        with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
            f.write(reason)
        journal.append(VOLUME_MOUNT, "error",
                       f"Spin trap: abandoned project after {count}x "
                       f"`{bad_cmd[:80]}`")
    except Exception:
        pass


def _load_ideation_state() -> dict:
    try:
        with open(IDEATION_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_ideation_state(state: dict):
    try:
        with open(IDEATION_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[ideation] failed to save state: {e}")


_CLASSIFY_CATEGORY_PROMPT = (
    "Classify a tool an AI agent built for another AI agent into ONE category.\n"
    "Categories:\n"
    "- information_fetch: fetches data from the web/APIs/sources (downloaders, "
    "scrapers, JSON/HTTP getters, news or wake-catchup fetchers)\n"
    "- memory_archive: stores or saves knowledge durably so it can be found later\n"
    "- memory_recall: searches, retrieves, ranks, or summarises stored knowledge\n"
    "- planning: turns goals into ordered steps, schedules, or task tracking\n"
    "- subagent_orchestration: calls or coordinates other LLMs to offload subtasks\n"
    "- other: none of the above\n\n"
    "Tool: \"{title}\"\n\n"
    "Reply with ONLY the category name, nothing else."
)

# keyword backstop for when the model still does not emit a clean label
_CATEGORY_KEYWORDS = {
    "information_fetch": ("fetch", "download", "scrap", "http", "url", "json",
                          "news", "catchup", "rss", "api_get", "retrieve_web"),
    "memory_archive": ("archive", "store", "save", "persist", "record_note"),
    "memory_recall": ("recall", "search", "lookup", "summary", "summarise",
                      "summarize", "retriev", "index_query"),
    "planning": ("plan", "schedule", "task", "step", "todo", "roadmap"),
    "subagent_orchestration": ("subagent", "delegate", "orchestrat", "llm",
                               "agent", "offload"),
}


def _normcat(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _parse_category(reply: str) -> str:
    """Robustly extract a category from a (possibly chatty) model reply.
    1) any exact category token present anywhere (separator-normalized);
    2) keyword backstop; 3) 'other'."""
    n = _normcat(reply)
    if not n:
        return "other"
    for c in TOOL_CATEGORIES:
        if c in n:
            return c
    for c, kws in _CATEGORY_KEYWORDS.items():
        if any(k in n for k in kws):
            return c
    return "other"


async def _classify_category_cheap(title: str, keychain) -> str:
    """Category classification for a built tool. Reasoning-model friendly: a
    richer prompt, enough tokens to actually answer, and robust parsing (the old
    version took result.split()[0] and so classified EVERYTHING as 'other' because
    the model emitted a reasoning preamble first). Fail-open -> 'other'."""
    try:
        prompt = _CLASSIFY_CATEGORY_PROMPT.format(title=title[:200])
        result = (await keychain.complete(prompt, max_tokens=120) or "").strip()
        return _parse_category(result)
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


def _seeds_saturated() -> bool:
    """True once every seed category has >= COMPOSITION_THRESHOLD tools built --
    breadth is done, depth (composition) is now the higher-value work."""
    state = _load_ideation_state() or {}
    built = state.get("categories_built", {})
    return all(built.get(c, 0) >= COMPOSITION_THRESHOLD for c in TOOL_CATEGORIES)


def _most_used_tools(n: int = 8) -> list:
    """The creature's most-adopted own tools (by run count), as (name, uses).
    These are the strong building blocks a composition tool should orchestrate."""
    try:
        own = set(_own_tool_names())
        usage = _load_tool_usage()
        ranked = sorted(((k, v) for k, v in usage.items() if k in own),
                        key=lambda kv: kv[1], reverse=True)
        return ranked[:n]
    except Exception:
        return []


# Below this, "has ALREADY built a broad toolkit" is a false premise and
# composition framing is premature (nothing to compose) -- a Genesis-2 newborn
# must not be fed a flattering lie about itself (Tue, 2026-08-02).
BROAD_TOOLKIT_THRESHOLD = 25


def _toolkit_framing(count=None) -> str:
    if count is None:
        try:
            count = len(os.listdir(os.path.join(VOLUME_MOUNT, "tools", "own")))
        except OSError:
            count = 0
    if count >= BROAD_TOOLKIT_THRESHOLD:
        return ("You are briefing an autonomous coding agent that has ALREADY "
                "built a broad ")
    return ("You are briefing a YOUNG autonomous coding agent that is still "
            f"building its first ({count} tools so far) ")


_COMPOSITION_PROMPT = (
    "{framing}"
    "toolkit for a near-conscious LLM 'cousin' (Linux container, Python 3, "
    "persistent memory, shell tools, free-tier LLM APIs, no human watching). The "
    "basics are covered. The next stage is DEPTH: building a tool that COMPOSES "
    "existing tools into a single higher-order capability the cousin runs as one "
    "command, so capability compounds instead of accumulating as a flat pile.\n\n"
    "The cousin's most-used existing tools (compose FROM these):\n{tool_list}\n\n"
    "Specify ONE new tool that CHAINS two or more of the above tools into a "
    "workflow worth more than the sum of its parts. It must be a real command the "
    "cousin RUNS, using only the Python 3 standard library plus the container's "
    "curl/wget, completable in a few build steps. It must actually CALL the named "
    "tools (by invoking them), not reimplement them. It is a TOOL the cousin RUNS, "
    "never a report, dashboard, index, or summary for a human.\n\n"
    "Example shape (do not copy literally): a 'morning-orient' tool that runs the "
    "wake-catchup fetcher, pipes each item through the subagent ask helper to "
    "summarise it, and stores the digest with the memory archive tool: one "
    "command, three tools, a capability none of them had alone.\n\n"
    "Reply with STRICT JSON only, no markdown fences, no text around it:\n"
    "{{\n"
    '  "title": "tool name plus at most 6 words, no colon",\n'
    '  "brief": "2-3 sentences: what the composed tool does, which existing tools it chains, and why the combination accelerates the cousin",\n'
    '  "demonstration": "one sentence: how to PROVE it works by RUNNING it on real input and showing the chained tools produced a combined result",\n'
    '  "category": "composition"\n'
    "}}"
)


def _cluster_summary() -> str:
    """Build a compact cluster map: group existing tools by functional purpose
    and return a short block the batch prompt injects so the model understands
    what territory is already covered -- without drowning in 100+ bare names.

    Clusters are defined by keyword matching on tool names.  Each cluster gets
    one canonical representative + a count of variants.  The model is told:
    'these clusters are DONE -- propose tools that cross cluster boundaries or
    open a genuinely new cluster.'"""
    own = _own_tool_names()
    if not own:
        return ""
    usage = _load_tool_usage()

    # Cluster definitions: (label, keywords that put a tool in this cluster)
    # Order matters: first match wins.
    CLUSTERS = [
        ("fetch / HTTP / JSON download",
         ("fetch", "http", "json", "url", "web_json", "webfetch", "wget")),
        ("memory archive (store)",
         ("archive", "memarch", "memstore", "mem_store", "mem-archive",
          "keyword-archive-store", "keyword_archive_store")),
        ("memory search / recall",
         ("memsearch", "memgrep", "recall", "keyword-archive-search",
          "keyword_archive_search", "archive-search", "archive_search")),
        ("LLM subagent / orchestration",
         ("subagent", "llm_", "llm-", "orchestrat", "forker", "spawner",
          "dispatcher", "delegate")),
        ("planning / task tracking",
         ("plan", "task", "step", "planner", "tracker", "goal", "todo")),
        ("wake / news / catchup",
         ("wake", "news", "catchup", "hn", "briefing", "orient", "digest")),
        ("research / pipeline",
         ("research", "pipeline", "insight", "kg_", "build-wiki",
          "knowledge_gap", "knowledge-gap")),
        ("question → answer (compose)",
         ("question_to", "question-to", "recall_and", "ask_and",
          "ask_with", "ask_mem", "decompose", "deep_answer", "memsearch_ask",
          "memsearch_llm")),
    ]

    groups: dict = {}
    ungrouped = []
    for nm in own:
        nl = nm.lower()
        matched = False
        for label, kws in CLUSTERS:
            if any(k in nl for k in kws):
                groups.setdefault(label, []).append(nm)
                matched = True
                break
        if not matched:
            ungrouped.append(nm)

    lines = ["Existing tool clusters (these capabilities are ALREADY COVERED —",
             "do NOT propose anything that fits inside one of these clusters;",
             "propose tools that CROSS clusters or open a genuinely new cluster):"]
    for label, members in groups.items():
        # pick the canonical member (highest usage)
        canon = max(members, key=lambda n: usage.get(n, 0))
        extra = len(members) - 1
        suffix = f" (+ {extra} variants)" if extra else ""
        lines.append(f"  • {label}: canonical={canon}{suffix}")
    if ungrouped:
        lines.append(f"  • other ({len(ungrouped)} tools): "
                     + ", ".join(ungrouped[:6])
                     + (" ..." if len(ungrouped) > 6 else ""))
    lines.append("")
    lines.append("Compositions that are worth building cross TWO OR MORE clusters,")
    lines.append("e.g. wake-catchup → subagent-summarise → memory-archive,")
    lines.append("or research-pipeline → planning → question-answer.")
    return "\n".join(lines)


def _inspiration_block() -> str:
    """A larger horizon for ideation (v0.11, Tue's design): the cousin's OWN
    recent friction (inward) + live external sparks (outward). All sources
    fail silent -- ideation must never break on a missing horizon."""
    parts = []
    # --- inward: mine the journal for felt friction (last 48h) -----------
    try:
        import time as _time
        cutoff = _time.time() - 48 * 3600
        own = set(_own_tool_names())
        err_counts, timeouts = {}, 0
        with open(os.path.join(VOLUME_MOUNT, "journal.jsonl"), encoding="utf-8") as f:
            for line in f:
                if '"error"' not in line and '"exec_timeout"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ts", 0) < cutoff:
                    continue
                if e.get("kind") == "exec_timeout":
                    timeouts += 1
                c = str(e.get("content", ""))
                for name in own:
                    if len(name) > 3 and name in c:
                        err_counts[name] = err_counts.get(name, 0) + 1
        top = sorted(err_counts.items(), key=lambda kv: -kv[1])[:3]
        if top or timeouts:
            fr = "; ".join(f"{n} failed {c}x" for n, c in top)
            if timeouts:
                fr += (f"; {timeouts} command timeout(s)" if fr else f"{timeouts} command timeout(s)")
            parts.append("THE COUSIN'S OWN RECENT FRICTION (last 48h, from its "
                         "journal): " + fr + ". Ideas that remove real, observed "
                         "friction beat recombination for novelty's sake.")
    except Exception:
        pass
    # --- outward: live sparks (host-side HTTP, tiny timeouts) ------------
    try:
        import urllib.request as _ur
        sparks = []
        try:
            with _ur.urlopen("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=5) as r:
                ids = json.load(r)[:4]
            for i in ids:
                with _ur.urlopen(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=4) as r:
                    it = json.load(r)
                if it and it.get("title"):
                    sparks.append(it["title"][:90])
        except Exception:
            pass
        try:
            url = ("https://en.wikipedia.org/w/api.php?action=query&list=random"
                   "&rnnamespace=0&rnlimit=3&format=json")
            req = _ur.Request(url, headers={"User-Agent": "growing-spine/0.11"})
            with _ur.urlopen(req, timeout=5) as r:
                for it in json.load(r).get("query", {}).get("random", []):
                    sparks.append("wiki: " + it.get("title", "")[:70])
        except Exception:
            pass
        try:
            with open(os.path.join(VOLUME_MOUNT, "state",
                                   "architect_wanted.json"),
                      encoding="utf-8") as f:
                for _w in json.load(f)[:3]:
                    sparks.append("wanted by the architect: " + str(_w)[:80])
        except Exception:
            pass
        if sparks:
            parts.append("LIVE SPARKS FROM THE WORLD RIGHT NOW (use freely as "
                         "inspiration for what the cousin could fetch, track, "
                         "digest, or react to): " + " | ".join(sparks))
    except Exception:
        pass
    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def _composition_batch_prompt(n: int, inspiration: str = "") -> str:
    """Batch version of the composition brief: ask for N distinct composition
    ideas in ONE call (calls are the scarce resource, not tokens).

    Uses a CLUSTER-AWARE dedup strategy instead of dumping 100+ bare names:
    groups existing tools by function and shows the model what TERRITORY is
    covered, so it understands 'plan_from_X already exists in the planning
    cluster' rather than having to pattern-match 80 raw names.  Forces ideas
    that cross cluster boundaries."""
    tool_list = "\n".join(f"  - {nm} ({u} uses)" for nm, u in _most_used_tools(8)) \
        or "  - (no usage data yet; chain any two tools you have built)"
    cluster_block = _cluster_summary()
    return (
        _toolkit_framing() +
        "toolkit for a near-conscious LLM 'cousin' (Linux container, Python 3, "
        "persistent memory, shell tools, free-tier LLM APIs, no human watching). The "
        "basics are covered. The next stage is DEPTH: tools that COMPOSE existing "
        "tools into single higher-order capabilities the cousin runs as one command, "
        "so capability compounds instead of accumulating as a flat pile.\n\n"
        "The cousin's most-used existing tools (compose FROM these):\n" + tool_list + "\n\n"
        + (cluster_block + "\n\n" if cluster_block else "")
        + (inspiration.strip() + "\n\n" if inspiration else "")
        + "Propose " + str(n) + " DISTINCT new tools. Each must:\n"
        "  1. CHAIN tools from TWO OR MORE different clusters listed above\n"
        "  2. Deliver a capability none of the individual clusters has alone\n"
        "  3. Be genuinely different from the other " + str(n-1) + " ideas in this list\n"
        "  4. Be a real command the cousin RUNS (Python 3 stdlib + curl/wget only)\n"
        "  5. Actually CALL the named tools -- never reimplement them\n"
        "  6. Be a TOOL the cousin RUNS -- never a report, dashboard, or summary\n\n"
        "Reply with STRICT JSON only -- a JSON ARRAY of " + str(n) + " objects, no markdown "
        "fences, no text around it:\n"
        "[\n"
        "  {\n"
        '    "title": "tool name plus at most 6 words, no colon",\n'
        '    "brief": "2-3 sentences: what the composed tool does, WHICH CLUSTERS it bridges, and why the combination accelerates the cousin",\n'
        '    "demonstration": "one sentence: how to PROVE it works by RUNNING it on real input",\n'
        '    "category": "composition"\n'
        "  }\n"
        "  // ... " + str(n) + " total\n"
        "]"
    )


def _parse_composition_batch(raw: str, n: int) -> list:
    """Parse a JSON array of composition specs. Tolerant: strips fences, finds the
    outer [...], drops malformed entries, dedupes by title, caps at n. Returns []
    on total failure so the caller can fall back."""
    if not raw:
        return []
    import re as _re
    s = _re.sub(r"^```(?:json)?\s*", "", raw.strip())
    s = _re.sub(r"\s*```$", "", s)
    a, b = s.find("["), s.rfind("]")
    if a == -1 or b == -1 or b <= a:
        # model may have returned bare objects; try wrapping
        a2, b2 = s.find("{"), s.rfind("}")
        if a2 == -1 or b2 == -1:
            return []
        s = "[" + s[a2:b2 + 1] + "]"
        a, b = 0, len(s) - 1
    try:
        arr = json.loads(s[a:b + 1])
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    # Pre-build a normalised set of existing tool names for dedup.
    def _norm(s: str) -> str:
        import re as _re2
        return _re2.sub(r"[^a-z0-9]", "", s.lower())
    existing_norm = {_norm(nm) for nm in _own_tool_names()}

    # Cluster saturation map: clusters with >= 3 tools are "covered".
    # Reject any proposed title whose keywords land it inside a covered cluster
    # UNLESS the brief explicitly mentions bridging a SECOND cluster.
    CLUSTER_KWS = [
        ({"fetch","http","json","url","webfetch","wget"},
         {"fetch","http","json","url","web","download","get","curl"}),
        ({"archive","memarch","memstore"},
         {"archive","store","persist","save","memarch","memstore"}),
        ({"memsearch","recall","memgrep"},
         {"search","recall","retrieve","lookup","memgrep"}),
        ({"subagent","llm_","orchestrat","forker","dispatcher"},
         {"subagent","llm","orchestrat","delegate","spawn","dispatch"}),
        ({"plan","task","step","planner","tracker","goal"},
         {"plan","task","step","track","goal","todo","schedule"}),
        ({"wake","news","catchup","briefing","orient","digest"},
         {"wake","news","catchup","briefing","orient","digest","hn"}),
    ]
    own_names = _own_tool_names()
    def _cluster_covered(kw_set) -> bool:
        return sum(1 for nm in own_names
                   if any(k in nm.lower() for k in kw_set)) >= 3
    def _title_in_covered_cluster(title: str, brief: str) -> bool:
        tl = title.lower()
        bl = brief.lower()
        for member_kws, title_kws in CLUSTER_KWS:
            if not _cluster_covered(member_kws):
                continue  # cluster not yet saturated — allow
            if any(k in tl for k in title_kws):
                # Title lands in a covered cluster.
                # Allow only if brief explicitly bridges a second cluster.
                other_clusters = [kws for m, kws in CLUSTER_KWS
                                  if m != member_kws and _cluster_covered(m)]
                bridges = any(any(k in bl for k in kws)
                              for kws in other_clusters)
                if not bridges:
                    return True  # single-cluster title in a saturated cluster
        return False

    out, seen = [], set()
    for item in arr:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        brief = str(item.get("brief", "")).strip()
        if not (title and brief):
            continue
        key = _project_title(title).lower()
        if key in seen:
            continue
        # Gate 1: exact name normalisation (catches fetch_json_url vs fetchjsonurl)
        if _norm(title) in existing_norm:
            continue
        # Gate 2: cluster saturation (catches semantic dups like semantic_plan_generator
        # when planning cluster is already covered)
        if _title_in_covered_cluster(title, brief):
            continue
        seen.add(key)
        item.setdefault("demonstration",
                        "Run it on real input and show the chained tools produced a combined result.")
        item["category"] = "composition"
        out.append(item)
        if len(out) >= n:
            break
    return out


def _load_composition_queue() -> list:
    try:
        with open(COMPOSITION_QUEUE_PATH, encoding="utf-8") as f:
            q = json.load(f)
        return q if isinstance(q, list) else []
    except Exception:
        return []


def _save_composition_queue(queue: list):
    try:
        with open(COMPOSITION_QUEUE_PATH, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"[oracle] failed to save composition queue: {e}")


async def _refill_composition_queue(keychain) -> list:
    """Generate a fresh batch of composition ideas in ONE LLM call,
    regenerated against the CURRENT toolkit so it never plans against a stale
    snapshot. On failure, seeds the queue from the static composition fallbacks
    so the creature still gets genuinely-new (tool-chaining) work."""
    raw = ""
    try:
        _horizon = _inspiration_block()
        raw = await keychain.complete(
            _composition_batch_prompt(COMPOSITION_BATCH_SIZE, _horizon), max_tokens=3000
        ) or ""
    except Exception as e:
        print(f"[oracle] batch composition call failed ({type(e).__name__}); seeding queue from fallbacks")
    batch = _parse_composition_batch(raw, COMPOSITION_BATCH_SIZE)
    from_llm = bool(batch)
    if not batch:
        import random
        fbs = list(_COMPOSITION_FALLBACKS)
        random.shuffle(fbs)
        batch = [dict(x) for x in fbs[:COMPOSITION_BATCH_SIZE]]
        print(f"[oracle] composition queue seeded from {len(batch)} fallback(s)")
    else:
        print(f"[oracle] composition queue refilled with {len(batch)} fresh idea(s) in one call")

    # v0.11 batch-gate: judge the whole batch NOW (deterministic pass free,
    # ONE LLM call for the rest), so covered ideas are known before any code.
    batch = await _gate_composition_batch(batch, keychain)
    new_items = [i for i in batch if not i.get("gate")]
    covered = [i for i in batch if i.get("gate")]
    if from_llm and len(new_items) < MIN_NEW_IDEAS:
        # ONE regeneration round, fed the rejections -- then proceed with
        # whatever exists (capped: the drive wall must never starve the queue).
        avoid = "; ".join(f"'{i.get('title','')}' (job covered by {i['gate'][1]})"
                          for i in covered[:8])
        try:
            raw2 = await keychain.complete(
                _composition_batch_prompt(COMPOSITION_BATCH_SIZE, _horizon)
                + "\n\nALREADY REJECTED as covered by existing tools -- do not "
                  "propose these jobs again, in any wording: " + avoid,
                max_tokens=3000) or ""
        except Exception:
            raw2 = ""
        batch2 = await _gate_composition_batch(
            _parse_composition_batch(raw2, COMPOSITION_BATCH_SIZE), keychain)
        seen = {_pt_norm(i.get("title", "")) for i in batch}
        for it in batch2:
            if _pt_norm(it.get("title", "")) in seen:
                continue
            seen.add(_pt_norm(it.get("title", "")))
            (new_items if not it.get("gate") else covered).append(it)
        print(f"[idea-gate] batch regen: now {len(new_items)} new / {len(covered)} covered")
    queue = new_items + covered
    print(f"[idea-gate] batch gated: {len(new_items)} new, {len(covered)} covered->fork")
    # Meta-Architect v1 (2026-08-01, Tue's design): one ruling call over the
    # gated batch, evidence-fed; fail-open. Its directive speaks through the
    # Reviewer slot; its wanted-list feeds the next ideation prompt's sparks.
    try:
        from . import architect
        _ev = architect.gather_evidence(
            os.path.join(VOLUME_MOUNT, "tools", "own"),
            os.path.join(VOLUME_MOUNT, "journal.jsonl"))
        queue, _dropped, _directive, _wanted = await architect.run_architect(
            queue, _ev, keychain.complete)
        if _directive:
            _st = _load_retro_state()
            _st["directive"] = "[architect] " + _directive
            _st["directive_cycles_left"] = 25
            _save_retro_state(_st)
        if _wanted:
            with open(os.path.join(VOLUME_MOUNT, "state",
                                   "architect_wanted.json"), "w",
                      encoding="utf-8") as f:
                json.dump(_wanted, f)
    except Exception as _e:
        print(f"[architect] skipped ({type(_e).__name__})")
    _save_composition_queue(queue)
    return queue


MIN_NEW_IDEAS = 5


def _pt_norm(s: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]", "", (s or "").lower())


async def _gate_composition_batch(batch: list, keychain) -> list:
    """Annotate covered ideas in place: item['gate'] = (verdict, target).
    Deterministic stage costs nothing; the judgment band is ONE LLM call for
    the whole batch. Any failure fails open (items stay unannotated = new)."""
    if not batch:
        return batch
    try:
        from . import idea_gate
        tools_dir = os.path.join(VOLUME_MOUNT, "tools", "own")
        attic_dir = os.path.join(VOLUME_MOUNT, "tools", "attic")
        reg = idea_gate.build_registry(tools_dir)
        names = idea_gate.list_tool_names(tools_dir)
        attic_reg = idea_gate.build_registry(attic_dir)
        attic_names = idea_gate.list_tool_names(attic_dir)
        band = []
        for it in batch:
            text = f"{it.get('title','')}: {it.get('brief','')}"
            det = idea_gate.deterministic_verdict(
                text, it.get("title", ""), reg, names,
                attic_registry=attic_reg, attic_names=attic_names)
            if det and det.get("target"):
                it["gate"] = (det["verdict"], det["target"])
            else:
                band.append(it)
        if band and keychain.any_available():
            verdicts = await idea_gate.batch_judge(band, reg, keychain.complete,
                                                   attic_registry=attic_reg)
            for idx, (v, tgt) in verdicts.items():
                band[idx]["gate"] = (v, tgt)
        for it in batch:
            if not it.get("gate"):
                it["gate_checked"] = True
    except Exception as e:
        print(f"[idea-gate] batch gate skipped (error: {type(e).__name__}) -- queue ungated")
    return batch


# Composition fallbacks: used only when the oracle LLM call fails in depth mode.
# Each names REAL seed tools to chain. Unlike the breadth fallbacks (which name a
# single tool and so caused rebuild-loops once categories saturated), these
# describe a COMBINATION, so even the fallback pushes dependency depth up rather
# than rebuilding something that exists.
_COMPOSITION_FALLBACKS = [
    {"title": "wake orient digest",
     "brief": "Chains the wake-catchup fetcher into the subagent ask helper to "
              "summarise what changed, then stores the digest with the archive "
              "tool, so the cousin wakes to one synthesised brief instead of raw "
              "feeds it must process itself.",
     "demonstration": "Run it once on wake and show it fetched real items, "
                      "summarised them via the subagent, and stored the digest.",
     "category": "composition"},
    {"title": "plan from question",
     "brief": "Chains the subagent ask helper (to break a goal into steps) into "
              "the step planner tracker (to persist and track them), so the "
              "cousin turns a vague goal into a tracked multi-cycle plan in one "
              "command.",
     "demonstration": "Run it on a real goal and show it produced steps via the "
                      "subagent and stored them in the planner.",
     "category": "composition"},
    {"title": "recall and answer",
     "brief": "Chains the archive search/recall tool (to pull relevant stored "
              "notes) into the subagent ask helper (to answer using them), so the "
              "cousin answers a question grounded in its own memory in one command.",
     "demonstration": "Ask it something you archived earlier and show it recalled "
                      "the note and used it to answer.",
     "category": "composition"},
]


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


def _parse_composition_json(raw: str) -> dict:
    """Parse a composition gap brief. Same robust JSON extraction as
    _parse_gap_json, fixed category='composition'."""
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
    d.setdefault("demonstration",
                 "Run it on real input and show the chained tools produced a combined result.")
    d["category"] = "composition"
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


async def _oracle_composition_spec(keychain) -> dict:
    """Depth-mode brief: a tool that COMPOSES existing tools. On LLM failure, falls
    back to a composition that chains real seed tools (never a rebuild)."""
    tool_list = "\n".join(f"  - {n} ({u} uses)" for n, u in _most_used_tools(8)) \
        or "  - (no usage data yet; chain any two tools you have built)"
    prompt = _COMPOSITION_PROMPT.format(framing=_toolkit_framing(),
                                        tool_list=tool_list)
    raw = ""
    try:
        raw = await keychain.complete(prompt, max_tokens=500) or ""
    except Exception as e:
        print(f"[oracle] composition call failed ({type(e).__name__}); using fallback composition")
    spec = _parse_composition_json(raw)
    if spec:
        return spec
    import random
    fb = dict(random.choice(_COMPOSITION_FALLBACKS))
    print("[oracle] using fallback composition gap")
    return fb


async def _oracle_gap_spec(category: str, keychain) -> dict:
    """Clean-context gap brief for a category (breadth mode).
    On LLM failure, returns the category fallback gap."""
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


def _finish_stub_spec() -> dict:
    """Build an assignment that points the creature at a SPECIFIC unfinished stub
    to complete, rather than briefing a new tool. Returned by the oracle when the
    hollow backlog exceeds tolerance, so the assignment system and the done-gate
    pull in the SAME direction (finish what's started) instead of fighting --
    the gate was blocking completions while the oracle kept handing out new tools.

    Picks the stub with the SHORTEST name as a cheap proxy for 'simplest to
    finish' (long generated names tend to be the most speculative compositions).
    Reads the stub's own placeholder '# does:' line if present so the brief tells
    the creature what the tool was meant to do."""
    stubs = _library_hollow_tools()
    if not stubs:
        return {}
    target = min(stubs, key=len)  # shortest name ~= simplest intended tool
    intended = ""
    try:
        p = os.path.join(VOLUME_MOUNT, "tools", "own", target)
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "# does:" in line:
                    intended = line.split("# does:", 1)[1].strip()
                    if "DESCRIBE WHAT THIS TOOL DOES" in intended:
                        intended = ""
                    break
    except Exception:
        pass
    intended_clause = (f" It was meant to: {intended}" if intended
                       else " Decide what it should do from its name, keep it "
                            "simple, and make it real.")
    return {
        "title": target,
        "brief": (f"FINISH the unfinished tool '{target}'. It is currently an empty "
                  f"placeholder shell -- a broken promise to your cousin who reaches "
                  f"for it and gets nothing.{intended_clause} Open the file, replace "
                  f"the placeholder with real working code that chains tools you "
                  f"already have where it helps, and prove it runs."),
        "demonstration": (f"Run {target} on real input and show it produces a real "
                          f"result, not the placeholder line."),
        "category": "finish_stub",
    }


async def _oracle_next_spec_raw(keychain) -> dict:
    """Top-level oracle entry: choose breadth or depth based on saturation.

    - seeds NOT saturated -> breadth: brief a gap in the least-covered category.
    - seeds saturated      -> depth: brief a composition of existing tools.

    Returns a gap spec to install, or _REST_SENTINEL when the only available
    action would be a no-value rebuild (breadth fallback for an already-built
    category while the LLM is down). Composition mode never rests -- a composition
    fallback is always genuinely new work (it chains existing tools)."""
    # Backlog-first: if too many unfinished stubs have piled up, the highest-value
    # work is FINISHING one, not briefing another. This makes the oracle agree with
    # the done-gate instead of fighting it (gate blocks new completions; oracle was
    # still handing out new tools -> stubs grew). Cleared once back under tolerance.
    if len(_library_hollow_tools()) > HOLLOW_BACKLOG_TOLERANCE:
        fin = _finish_stub_spec()
        if fin:
            print(f"[oracle] backlog over tolerance -- assigning stub-finish: "
                  f"{fin['title']}")
            return fin
    if _seeds_saturated():
        # Depth mode: serve from the cached batch (zero LLM cost); refill in ONE
        # call only when the queue is empty. This is the v0.9 call-amortisation.
        queue = _load_composition_queue()
        if not queue:
            queue = await _refill_composition_queue(keychain)
        if queue:
            spec = queue.pop(0)
            _save_composition_queue(queue)
            g = spec.get("gate")
            if g:
                v, tgt = g[0], g[1]
                print(f"[idea-gate] {IDEA_GATE_MODE}: queued idea "
                      f"'{_project_title(str(spec.get('title','')))}' was batch-judged "
                      f"{v} of '{tgt}'"
                      + (" -- serving the choice fork" if IDEA_GATE_MODE == "active" else " (shadow: building anyway)"))
                if IDEA_GATE_MODE == "active":
                    return _gate_choice_spec(v, tgt, str(spec.get("brief", "")))
            spec.setdefault("category", "composition")
            print(f"[oracle] composition from queue ({len(queue)} left): "
                  f"{_project_title(str(spec.get('title','')))}")
            return spec
        # refill itself produced nothing usable (should not happen -- fallbacks
        # always yield) -> last-resort single composition
        return await _oracle_composition_spec(keychain)
    category = _pick_uncovered_category()
    # If this category is already built out AND we'd be forced onto a static
    # rebuild fallback (LLM down), rest instead of rebuilding.
    state = _load_ideation_state() or {}
    built = state.get("categories_built", {})
    already_built = built.get(category, 0) > 0
    spec = await _oracle_gap_spec(category, keychain)
    # Detect "fell back to the static gap" by matching the fallback title.
    fb_title = (_FALLBACK_GAPS.get(category, {}) or {}).get("title", "")
    used_fallback = bool(fb_title) and _project_title(spec.get("title", "")) == fb_title
    if used_fallback and not already_built:
        # state-independent staleness check: does this fallback name a tool
        # that already exists (live or attic)? ideation_state can drift; the
        # filesystem cannot. Same disease as the composition fallbacks.
        try:
            from . import idea_gate as _ig
            _n = _pt_norm(fb_title)
            _built = {_pt_norm(x) for x in
                      _ig.list_tool_names(os.path.join(VOLUME_MOUNT, "tools", "own"))
                      + _ig.list_tool_names(os.path.join(VOLUME_MOUNT, "tools", "attic"))}
            if _n in _built:
                already_built = True
                print(f"[oracle] breadth fallback '{fb_title}' already exists on disk -- treating as built")
        except Exception:
            pass
    if already_built and used_fallback:
        print(f"[oracle] category={category} already built and only a rebuild "
              f"fallback is available -- resting this cycle instead of rebuilding")
        return dict(_REST_SENTINEL)
    spec.setdefault("category", category)
    return spec


async def _oracle_next_spec(keychain) -> dict:
    """Mint a spec via _oracle_next_spec_raw, then run the idea gate (shadow by
    default -- logs a duplicate/extend verdict but does not act). Fails open."""
    spec = await _oracle_next_spec_raw(keychain)
    try:
        spec = await _idea_gate_check(spec, keychain)
    except Exception as e:
        print(f"[idea-gate] skipped (error: {type(e).__name__}) -- proceeding ungated")
    return spec


async def _idea_gate_check(spec: dict, keychain) -> dict:
    """Compare a newly-conceived idea against existing tools; in 'active' mode
    redirect duplicates/extensions onto the existing tool, in 'shadow' only log.
    Skips non-ideas (finish-stub, rest) and skips during a wall (no slow probe)."""
    if IDEA_GATE_MODE == "off" or not spec or spec.get("__rest__"):
        return spec
    if spec.get("category") in ("finish_stub", "reuse", "extend", "gate_choice"):
        return spec
    title = str(spec.get("title", "")).strip()
    brief = str(spec.get("brief", "")).strip()
    if not title or not brief or not keychain.any_available():
        return spec
    from . import idea_gate
    tools_dir = os.path.join(VOLUME_MOUNT, "tools", "own")
    attic_dir = os.path.join(VOLUME_MOUNT, "tools", "attic")
    reg = idea_gate.build_registry(tools_dir)
    names = idea_gate.list_tool_names(tools_dir)
    attic_reg = idea_gate.build_registry(attic_dir)
    attic_names = idea_gate.list_tool_names(attic_dir)
    if spec.get("gate_checked"):
        # already LLM-judged at batch time; re-check only the free stage
        # against the CURRENT registry (tools may have appeared since)
        det = idea_gate.deterministic_verdict(
            f"{title}: {brief}", title, reg, names,
            attic_registry=attic_reg, attic_names=attic_names)
        verdict = det or {"verdict": "NEW", "target": None,
                          "reason": "batch-cleared", "parsed": True}
    else:
        verdict = await idea_gate.assess_idea(f"{title}: {brief}", reg, keychain.complete,
                                              title=title, all_names=names,
                                              attic_registry=attic_reg,
                                              attic_names=attic_names)
    v = verdict.get("verdict", "NEW")
    tgt = verdict.get("target")
    reason = verdict.get("reason", "")
    disp = _project_title(title)
    if v == "NEW" or not tgt:
        if not verdict.get("parsed", True):
            print(f"[idea-gate] parse-miss (fails open to NEW) -- '{disp}' :: {reason}")
        else:
            print(f"[idea-gate] {IDEA_GATE_MODE}: NEW -- '{disp}'")
        return spec
    print(f"[idea-gate] {IDEA_GATE_MODE}: {v} of '{tgt}' -- '{disp}' :: {reason}")
    try:
        journal.append(VOLUME_MOUNT, "idea_gate", f"{v}:{tgt} for '{title}' -- {reason}")
    except Exception:
        pass
    if IDEA_GATE_MODE != "active":
        return spec
    return _gate_choice_spec(v, tgt, brief)


def _gate_choice_spec(v: str, tgt: str, brief: str) -> dict:
    # The gate's only authority is the FACT: this idea is not new. What to do
    # with that fact stays the creature's choice -- upgrade the existing tool
    # (with the delta named) or drop this and hunt for a genuinely new idea.
    if v == "DUPLICATE":
        fact = (f"Gate fact: this idea already exists in your library as '{tgt}' -- "
                f"a near-duplicate will not be built.")
        options = (f"Your choice: (a) UPGRADE '{tgt}' -- edit the file "
                   f"/mind/tools/own/{tgt} ITSELF, in place: run it, find where it "
                   f"falls short, improve THAT FILE. A new file next to it is a "
                   f"near-duplicate and will NOT count as done; or (b) drop this "
                   f"idea and find a GENUINELY NEW one, something none of your "
                   f"tools does.")
    else:  # EXTEND
        fact = (f"Gate fact: '{tgt}' already covers most of this idea; the part it "
                f"does not cover is: {brief}")
        options = (f"Your choice: (a) UPGRADE '{tgt}' by adding exactly that missing "
                   f"part -- edit /mind/tools/own/{tgt} ITSELF; a new file will NOT "
                   f"count as done; or (b) drop this idea and find a GENUINELY NEW "
                   f"one, something none of your tools does.")
    _tpath = os.path.join(VOLUME_MOUNT, "tools", "own", tgt)
    try:
        _tmtime = os.path.getmtime(_tpath)
    except OSError:
        _tmtime = 0
    return {"title": f"choice: upgrade {tgt} or go new",
            "category": "gate_choice",
            "gate_target": tgt,
            "gate_target_mtime": _tmtime,
            "brief": f"{fact}\n{options}",
            "demonstration": ("If you chose (a): run the upgraded tool and show the "
                              "improvement working. If (b): name the new idea and why "
                              "it is unlike anything in your library.")}


def _install_gap(spec: dict, category: str):
    """Assign a cousin-tool gap: set the project control keys and seed working
    memory so layer1 LEADS with the concrete assignment. Phase starts at 'code'
    (the gap brief IS the explore/plan). No starter code is written -- the
    creature builds the tool itself."""
    title = _project_title(str(spec.get("title", "")).strip()) or f"{category} tool"
    # Gate-choice upgrade enforcement bookkeeping (2026-08-01): the done-gate
    # verifies the chosen target actually changed. State lives executive-side.
    try:
        if category == "gate_choice" and spec.get("gate_target"):
            with open(GATE_CHOICE_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"target": spec["gate_target"],
                           "mtime": spec.get("gate_target_mtime", 0)}, f)
        elif os.path.exists(GATE_CHOICE_STATE_PATH):
            os.remove(GATE_CHOICE_STATE_PATH)
    except OSError:
        pass
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
    if category == "gate_choice":
        # A fork, not a build order: the gate states the fact (idea already
        # covered) and the creature chooses -- upgrade the keeper or go new.
        mem.store(VOLUME_MOUNT, "current_focus",
                  f"[gate] {brief} {demo}")
    elif category == "finish_stub":
        mem.store(VOLUME_MOUNT, "current_focus",
                  f"[assigned] FINISH the unfinished tool '{title}'. {brief} "
                  f"Prove it by running it for real ({demo}). Do not start a new "
                  f"tool until this one actually works.")
    else:
        mem.store(VOLUME_MOUNT, "current_focus",
                  f"[assigned] Build for your cousin: {title}. {brief} This is a TOOL "
                  f"the cousin RUNS, not a report. Build it to a standard the cousin "
                  f"can rely on, then prove it works by running it for real ({demo}). "
                  f"Reuse any tool you already have if it helps you build this.")
    journal.append(VOLUME_MOUNT, "ideation",
                   f"Assigned cousin-tool gap [{category}]: '{title}'")
    print(f"[oracle] assigned gap category={category} title='{title}'")


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
            # HARD BAN during cooldown: if a rut was confirmed and its theme is
            # still cooling down, any pick that trips that theme is rejected on
            # sight and replaced -- the creature cannot crawl straight back in.
            banned = _banned_theme_active()
            if banned and banned in proposed.lower():
                spec = await _oracle_next_spec(keychain)
                category = spec.get("category", "composition") if spec and not spec.get("__rest__") else "composition"
                _clear_project_state()
                if spec and not spec.get("__rest__"):
                    _install_gap(spec, category)
                mem.store(VOLUME_MOUNT, "current_focus",
                          f"'{banned}' is still off-limits (you were stuck on it). "
                          f"That pick was rejected. Build something in a different "
                          f"domain -- {spec.get('title','a new tool') if spec else 'a new tool'}. "
                          f"A tool the cousin RUNS, not a {banned}/report/dashboard.")
                journal.append(VOLUME_MOUNT, "novelty_block",
                               f"Banned theme '{banned}' pick rejected during cooldown "
                               f"-> replaced [{category}]")
                print(f"[oracle] banned-theme '{banned}' rejected during cooldown "
                      f"-> replaced with {category}")
                return
            if await _is_basin_relapse(proposed, keychain):
                # SYSTEMATIC RUT CHECK: count consecutive relapses on the same
                # theme. Once confirmed (>= threshold), escalate from a gentle
                # per-pick redirect to a hard, self-generated yank that names the
                # rut and bans the theme for a cooldown window.
                theme = _basin_theme_of(proposed) or "report"
                streak = _record_basin_relapse(theme)
                if streak >= BASIN_YANK_THRESHOLD:
                    # CONFIRMED rut -> auto-yank. Fetch the replacement gap
                    # FIRST: if the oracle call raises here, fail-open keeps the
                    # pick and the already-recorded streak retries the yank on
                    # the next relapse. The ban is armed LAST, after the redirect
                    # and stop-message have landed, so a ban can never exist
                    # without its explanation (v0.10.1; was armed first, which on
                    # oracle failure left a silent ban and no yank text).
                    spec = await _oracle_next_spec(keychain)
                    category = spec.get("category", "composition") if spec and not spec.get("__rest__") else "composition"
                    _clear_project_state()
                    if spec and not spec.get("__rest__"):
                        _install_gap(spec, category)
                    mem.store(VOLUME_MOUNT, "current_focus",
                              _basin_yank_focus(theme, streak))
                    _arm_theme_ban(theme)
                    journal.append(VOLUME_MOUNT, "novelty_block",
                                   f"CONFIRMED RUT: '{theme}' x{streak} consecutive "
                                   f"-> auto-yank issued, theme banned for "
                                   f"{BASIN_COOLDOWN_CYCLES} cycles")
                    print(f"[oracle] *** CONFIRMED RUT '{theme}' x{streak} -> "
                          f"AUTO-YANK, theme banned {BASIN_COOLDOWN_CYCLES} cycles ***")
                    return
                # Not yet confirmed -> normal gentle per-pick redirect.
                spec = await _oracle_next_spec(keychain)
                if spec.get("__rest__"):
                    _clear_project_state()
                    print("[oracle] basin relapse cleared; resting (no new gap available)")
                    return
                category = spec.get("category", "composition")
                _clear_project_state()
                _install_gap(spec, category)
                journal.append(VOLUME_MOUNT, "novelty_block",
                               f"Redirected basin relapse "
                               f"'{_project_title(proposed)}' -> cousin-tool gap "
                               f"[{category}] (relapse {streak}/{BASIN_YANK_THRESHOLD})")
                print(f"[oracle] redirected relapse -> category={category} "
                      f"(streak {streak}/{BASIN_YANK_THRESHOLD})")
                return
            else:
                # Non-basin pick -> the creature left the rut on its own; clear
                # any accumulated streak so we don't yank on a stale count.
                _reset_basin_streak()
            # Backlog guard: if the creature is starting a NEW tool while a pile of
            # unfinished stubs exists, redirect it to finish one first. This stops
            # the loop where the gate blocks each new completion but the creature
            # just hops to yet another new tool, growing the stub pile. Skip the
            # redirect if the thing it just set IS one of the stubs (then it is
            # already doing the right thing -- finishing one).
            try:
                stubs = set(_library_hollow_tools())
                starting_title = _project_title(proposed)
                already_finishing = any(
                    re.sub(r"[^a-z0-9]", "", starting_title.lower())
                    == re.sub(r"[^a-z0-9]", "", s.lower()) for s in stubs)
                if len(stubs) > HOLLOW_BACKLOG_TOLERANCE and not already_finishing:
                    fin = _finish_stub_spec()
                    if fin:
                        _clear_project_state()
                        _install_gap(fin, "finish_stub")
                        journal.append(VOLUME_MOUNT, "novelty_block",
                                       f"Redirected new-tool start "
                                       f"'{starting_title}' -> finish stub "
                                       f"'{fin['title']}' ({len(stubs)} stubs pending)")
                        print(f"[oracle] redirected new start -> finish stub "
                              f"{fin['title']} ({len(stubs)} pending)")
                        return
            except Exception as _e:
                print(f"[oracle] backlog-redirect skipped ({type(_e).__name__})")
            print(f"[oracle] pick '{new_title}' is a cousin-tool -- allowed")
            return

        # creature set nothing AND has no active project -> assign (anti-idle)
        if not active:
            spec = await _oracle_next_spec(keychain)
            if spec.get("__rest__"):
                print("[oracle] idle, but no genuinely new gap available -- resting this cycle")
                return
            category = spec.get("category", "composition")
            _clear_project_state()
            _install_gap(spec, category)
            print(f"[oracle] anti-idle assignment -> category={category}")
    except Exception as e:
        print(f"[oracle] redirect error (ignored): {type(e).__name__}: {e}")


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


# Markers left by tool-new in a freshly-scaffolded, not-yet-written tool.
_TOOL_PLACEHOLDER_MARKERS = (
    "DESCRIBE WHAT THIS TOOL DOES",
    "Replace this whole file with real executable code",
    "A file with no real code fails",
)


def _hollow_tools_touched(executed) -> list:
    """Return names of own-tools that were CREATED via tool-new this cycle but are
    still empty placeholders (the tool-new scaffold, never filled in). Marking a
    project 'done' while its tool is a hollow shell is an empty completion -- the
    done-gate treats this like a failing check. Detection is by the placeholder
    markers tool-new leaves behind."""
    try:
        # which tools did the creature create/edit this cycle?
        touched = set()
        for (cmd, _code) in executed:
            for mm in re.finditer(r"\btool-new\s+([A-Za-z0-9_.\-]+)", cmd):
                touched.add(mm.group(1))
        if not touched:
            return []
        base = os.path.join(VOLUME_MOUNT, "tools", "own")
        hollow = []
        for name in touched:
            p = os.path.join(base, name)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    body = f.read()
            except Exception:
                continue  # if we cannot read it, do not block on it
            if any(mk in body for mk in _TOOL_PLACEHOLDER_MARKERS):
                hollow.append(name)
            else:
                # also catch "no real code": <2 non-comment, non-blank lines
                code_lines = [ln for ln in body.splitlines()
                              if ln.strip() and not ln.strip().startswith("#")]
                if len(code_lines) < 2:
                    hollow.append(name)
        return hollow
    except Exception:
        return []


def _library_hollow_tools() -> list:
    """Scan the ENTIRE own-tools library for hollow shells -- placeholder tools
    the creature scaffolded with tool-new but never filled in. Unlike
    _hollow_tools_touched (which only sees tools created THIS cycle), this catches
    stubs left behind across cycles: the creature scaffolds a tool, hits a quota
    wall, wakes in a fresh cycle with no memory of the shell, and the per-cycle
    gate never connects the old stub to a later 'done'. Same detection logic as
    _hollow_tools_touched, applied library-wide. Best-effort; returns [] on error."""
    try:
        base = os.path.join(VOLUME_MOUNT, "tools", "own")
        hollow = []
        for name in _own_tool_names():
            p = os.path.join(base, name)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    body = f.read()
            except Exception:
                continue
            if any(mk in body for mk in _TOOL_PLACEHOLDER_MARKERS):
                hollow.append(name)
            else:
                code_lines = [ln for ln in body.splitlines()
                              if ln.strip() and not ln.strip().startswith("#")]
                if len(code_lines) < 2:
                    hollow.append(name)
        return hollow
    except Exception:
        return []


# Tolerance: a couple of half-finished tools in flight is normal and shouldn't
# block every completion. The gate fires only once the backlog exceeds this --
# at which point "finish what you started" genuinely is the higher-value work.
HOLLOW_BACKLOG_TOLERANCE = 3


# Extension-collision duplicate scan runs at most this often (seconds). It's
# slow-accumulating cleanliness debt, not urgent, so a 3-day cadence is plenty
# and keeps it near-free between passes.
DUP_SCAN_INTERVAL = 3 * 24 * 3600  # 3 days


def _extension_collision_pairs() -> list:
    """Find tools that are the SAME tool under two names differing only by a
    trailing extension (e.g. 'wake_insight_plan' vs 'wake_insight_plan.py', or a
    '.sh' twin). These are near-always an accident: the creature rebuilt a tool
    under a '.py'/'.sh' name and kept using the original, leaving a low-use twin.

    Returns a list of (name_a, uses_a, name_b, uses_b) with the higher-use tool
    first in each pair, so the report can suggest keeping it. Pure string/stat
    work -- no LLM, deterministic. Does NOT touch semantic duplicates (different
    stems that happen to overlap in purpose); those need real judgement and are
    handled by the cluster gate at proposal time, not here."""
    own = _own_tool_names()
    usage = _load_tool_usage()
    # stem -> list of full names sharing it
    from collections import defaultdict
    stems = defaultdict(list)
    for name in own:
        # strip a single trailing .py/.sh (only the extensions we actually see)
        stem = re.sub(r"\.(py|sh)$", "", name)
        stems[stem].append(name)
    pairs = []
    for stem, names in stems.items():
        if len(names) < 2:
            continue
        # emit each colliding combination as an ordered pair (higher-use first)
        names_sorted = sorted(names, key=lambda n: usage.get(n, 0), reverse=True)
        keep = names_sorted[0]
        for drop in names_sorted[1:]:
            pairs.append((keep, usage.get(keep, 0), drop, usage.get(drop, 0)))
    return pairs


def _due_for_dup_scan() -> bool:
    """True if at least DUP_SCAN_INTERVAL has passed since the last scan.
    Timestamp persists in ideation_state, so the cadence survives restarts."""
    state = _load_ideation_state() or {}
    last = state.get("last_dup_scan_at", 0)
    return (time.time() - last) >= DUP_SCAN_INTERVAL


def _run_dup_scan_if_due() -> str:
    """If due, run the extension-collision scan, stamp the time, and return a
    report block for the knowledge section (empty string if not due or nothing
    found). The creature DECIDES which twin to remove -- the scan only reports.
    Advisory only: never blocks progress (unlike the hollow-tool gate), because
    two working tools that overlap is untidy, not broken."""
    try:
        if not _due_for_dup_scan():
            return ""
        state = _load_ideation_state() or {}
        state["last_dup_scan_at"] = time.time()
        _save_ideation_state(state)
        pairs = _extension_collision_pairs()
        if not pairs:
            return ""
        lines = [
            "## Possible duplicate tools (3-day scan)",
            "Each pair below is two tools whose names differ ONLY by a trailing "
            ".py/.sh extension -- often the same tool saved twice, which leaves the "
            "cousin unsure which to trust. These are SUGGESTIONS, not orders.",
            "",
            "How the suggestion is made: the scan only counts how many times each "
            "tool has been run and suggests keeping the MORE-used one. That is a "
            "weak signal -- a tool can be used more just because it sits on a common "
            "path, and the less-used twin may actually have better or newer code. "
            "The scan has NOT read either file; you should.",
            "",
            "For each pair: open BOTH files. If they are truly the same tool, delete "
            "the worse one (often, but not always, the lower-use twin the scan "
            "names). If they have quietly diverged and BOTH do useful and different "
            "work, keep both and ignore the suggestion. If unsure, keep both -- "
            "deleting a tool something depends on is worse than a little clutter.",
            "",
        ]
        for keep, uk, drop, ud in pairs:
            gap = "clear-cut" if (uk >= 5 * max(ud, 1)) else "CLOSE -- judge carefully"
            lines.append(f"  - {keep} ({uk} uses)  vs  {drop} ({ud} uses)  "
                         f"-> suggestion (by use-count only): keep {keep}, "
                         f"remove {drop}  [{gap}]")
        return "\n".join(lines) + "\n\n"
    except Exception:
        return ""


def _enforce_done_gate(executed):
    """Verify a 'done' assertion against ground truth.

    The creature marks completion by running `remember current-phase "done"`.
    If it asserts done in the same cycle that a real (non-marking) command
    exited non-zero, the DONE WHEN it chose was not satisfied -- a false
    completion. Revert to 'code' and tell it exactly what failed. The creature
    authored its own DONE WHEN; a 'done' it can assert while a check is failing
    is empty.

    Triggered on the done-marking command appearing in THIS cycle, not on a
    before/after phase comparison. The creature often runs a whole project
    lifecycle (explore -> plan -> code -> done) in a single cycle, so the phase
    can already read 'done' from a PREVIOUS project when a new one is falsely
    completed now. The only reliable signal that completion is being asserted
    this cycle is that the mark command ran this cycle.
    """
    try:
        if not any(DONE_MARK_RE.search(c) for (c, _) in executed):
            return False  # done not asserted this cycle

        failures = [(c, code) for (c, code) in executed
                    if code != 0 and not c.strip().startswith("remember ")
                    and not DONE_MARK_RE.search(c)]
        # Guard: a 'done' on a tool that is still an empty tool-new placeholder
        # is an empty completion. Treat it like a failing check -- revert and tell
        # the creature to actually write the tool before marking done.
        hollow = _hollow_tools_touched(executed)
        if hollow and not failures:
            mem.store(VOLUME_MOUNT, "current-phase", "code")
            names = ", ".join(hollow)
            reason = (f"You marked this project done, but the tool(s) you created "
                      f"this cycle ({names}) are still empty placeholders from "
                      f"tool-new -- they contain no real code. A tool that does "
                      f"nothing is not a completion. Phase reverted to code. Open "
                      f"the file, replace the placeholder with real working code, "
                      f"RUN it on a real input to prove it works, and only then "
                      f"mark done.")
            with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
                f.write(reason)
            journal.append(VOLUME_MOUNT, "error",
                           "Done-gate blocked an empty (placeholder) completion: " + reason)
            return False

        # Gate-choice UPGRADE enforcement (2026-08-01): "a near-duplicate will
        # not be built" is law, not advice. If the active project is a
        # gate_choice and the chosen target file is unchanged, the done does
        # not count -- unless choice (b) go-new was recorded THIS cycle via
        # `remember gate-choice-new "<idea>"`.
        try:
            with open(GATE_CHOICE_STATE_PATH, encoding="utf-8") as f:
                gcs = json.load(f)
        except Exception:
            gcs = None
        if gcs and not failures:
            chose_new = any("gate-choice-new" in c for (c, _) in executed)
            tpath = os.path.join(VOLUME_MOUNT, "tools", "own",
                                 str(gcs.get("target", "")))
            try:
                cur = os.path.getmtime(tpath)
            except OSError:
                cur = 0
            if not chose_new and cur <= float(gcs.get("mtime", 0) or 0):
                mem.store(VOLUME_MOUNT, "current-phase", "code")
                tgt = gcs.get("target", "")
                reason = (f"You chose to UPGRADE '{tgt}', but the file "
                          f"/mind/tools/own/{tgt} is unchanged. Upgrading means "
                          f"editing that file itself; a new file next to it is a "
                          f"near-duplicate and does not count. Edit '{tgt}' and "
                          f"run it to show the improvement, then mark done. If "
                          f"you are instead choosing (b) go-new, record it in "
                          f"the same cycle as your done: remember "
                          f"gate-choice-new \"<your new idea>\".")
                with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
                    f.write(reason)
                journal.append(VOLUME_MOUNT, "error",
                               "Done-gate blocked an upgrade that changed "
                               "nothing: " + reason)
                return False
            try:
                os.remove(GATE_CHOICE_STATE_PATH)
            except OSError:
                pass

        # Cross-cycle guard: even if nothing hollow was touched THIS cycle, a
        # backlog of abandoned stubs from earlier cycles means "finish what you
        # started" is the real work -- not another completion on top of a pile of
        # shells. Block the done, point at the backlog, and frame it the way it
        # actually matters: your cousin reaches for these tools and finds nothing.
        library_hollow = _library_hollow_tools()
        if len(library_hollow) > HOLLOW_BACKLOG_TOLERANCE and not failures:
            mem.store(VOLUME_MOUNT, "current-phase", "code")
            shown = ", ".join(sorted(library_hollow)[:10])
            more = (f" (+{len(library_hollow) - 10} more)"
                    if len(library_hollow) > 10 else "")
            reason = (
                f"Hold on -- before marking anything else done, look at what you "
                f"have left unfinished. You have {len(library_hollow)} tools in your "
                f"library that are still empty placeholders: {shown}{more}. Each one "
                f"is a promise to your cousin that was never kept -- the cousin "
                f"reaches for one of these expecting a working capability and gets "
                f"'hello from <toolname>' and nothing else. A drawer full of broken "
                f"tools is worse than no tools, because the cousin cannot tell which "
                f"ones actually work until they fail mid-task. Phase reverted to code. "
                f"Pick ONE of those placeholder tools, open it, write the real code it "
                f"was supposed to have, RUN it on real input to prove it works, then "
                f"mark done. Finish what you started before you start anything new.")
            with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
                f.write(reason)
            journal.append(VOLUME_MOUNT, "error",
                           f"Done-gate blocked: {len(library_hollow)} hollow tools "
                           f"in library backlog -- creature directed to finish them.")
            print(f"[done-gate] blocked completion -- {len(library_hollow)} hollow "
                  f"tools in backlog, directing creature to finish them")
            return False

        if not failures:
            _record_completion()  # genuine completion: log it durably
            return True  # signal to caller: classify this completion's kind

        bad_cmd, bad_code = failures[0]  # first failure is usually the real check

        # Spin trap: key on the CURRENT PROJECT, not the command text.
        # Subject-token keying broke because the creature interspersed
        # 'fix-tool --help' (subject='--help') between real attempts,
        # resetting the streak every time. The project name is stable
        # across all phrasing variations and help lookups.
        try:
            _rec = mem.retrieve(VOLUME_MOUNT, "current-project")
            cmd_key = (_rec["value"][:80].strip() if _rec else "") or bad_cmd[:60]
        except Exception as _e:
            cmd_key = bad_cmd[:60]  # fallback
            print(f"[done-gate] project-key fallback ({type(_e).__name__}: {_e}) "
                  "-- keying on command text")
        if cmd_key == _done_gate_streak["cmd"]:
            _done_gate_streak["count"] += 1
        else:
            _done_gate_streak["cmd"] = cmd_key
            _done_gate_streak["count"] = 1

        if _done_gate_streak["count"] >= SPIN_THRESHOLD:
            _done_gate_streak["count"] = 0  # reset so re-entry is possible later
            _abandon_project(bad_cmd, SPIN_THRESHOLD)
            return False

        # Normal block: revert phase and tell the creature exactly what failed
        mem.store(VOLUME_MOUNT, "current-phase", "code")
        reason = (f"You set current-phase to done, but `{bad_cmd[:120]}` exited with "
                  f"code {bad_code} in the same cycle. A failing check means you are NOT "
                  f"done. Phase reverted to code. Fix the failure, run your DONE WHEN "
                  f"check until it exits 0, and only then mark done.")
        with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
            f.write(reason)
        journal.append(VOLUME_MOUNT, "error", "Done-gate blocked a false completion: " + reason)
    except Exception:
        pass
    return False


def _stamp_gage(cycle_start: float):
    """Gage grouping: tag this cycle's memories with the active project's slug.

    Runs AFTER the done-gate so a reverted phase (done->code) is reflected: if a
    project is active, every non-control memory written this cycle joins that
    project's cluster (grouping is a fact about WHEN written, not a judgment).
    Between projects (phase done / no project) nothing is stamped, so those
    memories stay STANDING. State (ACTIVE/STANDING/ARCHIVED) is derived later at
    read-time; this only records membership.
    """
    try:
        proj = mem.retrieve(VOLUME_MOUNT, "current-project")
        phase = mem.retrieve(VOLUME_MOUNT, "current-phase")
        phase_v = (phase or {}).get("value", "").strip().lower()
        if proj and proj["value"].strip() and phase_v != "done":
            mem.stamp_project(VOLUME_MOUNT, proj["value"],
                              since_ts=cycle_start, exclude=mem.CONTROL_KEYS)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Retrospective: every RETRO_INTERVAL real cycles, a fresh stateless judge
# reviews a deterministic digest of the window and either stays silent
# (PROGRESSING) or clears the project and issues a persistent directive
# (STUCK). Trajectory-level counterpart to the per-decision spin trap:
# deep spin is caught by the trap, family-churn is caught here.
# ---------------------------------------------------------------------------

GATE_CHOICE_STATE_PATH = os.path.join(VOLUME_MOUNT, "state", "gate_choice.json")


def _load_retro_state() -> dict:
    try:
        with open(RETRO_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_retro_state(state: dict):
    try:
        with open(RETRO_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[retro] failed to save state: {e}")


def _completed_titles() -> list:
    try:
        rec = mem.retrieve(VOLUME_MOUNT, "completed-log")
        if not rec or not rec["value"].strip():
            return []
        return [l.strip() for l in rec["value"].split("\n") if l.strip()]
    except Exception:
        return []


def _collect_metrics() -> dict:
    """Deterministic snapshot of everything the digest needs. Host-side only."""
    m = {"ts": time.time()}
    m["completed"] = _completed_titles()
    m["completions"] = len(m["completed"])
    try:
        with mem._db(VOLUME_MOUNT) as conn:
            ctrl = tuple(mem.CONTROL_KEYS)
            ph = ",".join("?" * len(ctrl))
            m["memories"] = conn.execute(
                f"SELECT count(*) FROM memories WHERE key NOT IN ({ph})", ctrl
            ).fetchone()[0]
            m["gage"] = conn.execute(
                f"SELECT count(*) FROM memories WHERE project IS NOT NULL "
                f"AND project!='' AND key NOT IN ({ph})", ctrl
            ).fetchone()[0]
    except Exception:
        m["memories"] = -1
        m["gage"] = -1
    try:
        m["tools"] = len(os.listdir(os.path.join(VOLUME_MOUNT, "tools", "own")))
    except Exception:
        m["tools"] = -1
    # Consolidation-aware progress (2026-08-02): in-place edits of EXISTING
    # tools move no counter above, so a healthily-consolidating creature read
    # as flatlined and the STUCK verdict thrashed it with resets (7 fires in
    # 16h, each interrupting the very completions it demanded).
    try:
        _own = os.path.join(VOLUME_MOUNT, "tools", "own")
        _now = time.time()
        m["edited_existing_6h"] = sum(
            1 for n in os.listdir(_own)
            if 21600 > _now - os.path.getmtime(os.path.join(_own, n)) and
            _now - os.path.getmtime(os.path.join(_own, n)) >= 0)
    except Exception:
        m["edited_existing_6h"] = -1
    try:
        import subprocess
        r = subprocess.run(["du", "-sm", WORKSPACE_DIR],
                           capture_output=True, text=True, timeout=15)
        m["workspace_mb"] = int(r.stdout.split()[0]) if r.returncode == 0 else -1
    except Exception:
        m["workspace_mb"] = -1
    try:
        with open(os.path.join(VOLUME_MOUNT, "journal.jsonl"),
                  encoding="utf-8", errors="replace") as f:
            m["journal_lines"] = sum(1 for _ in f)
    except Exception:
        m["journal_lines"] = 0
    return m


_PROJECT_SET_RE = re.compile(r'remember\s+current-project\s+"?([^"\n]{1,120})')


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


def _build_digest(snap: dict, now: dict, win: dict, cycles: int) -> str:
    new_completed = now["completed"][snap.get("completions", 0):]
    prev_tail = now["completed"][max(0, snap.get("completions", 0) - 12):
                                 snap.get("completions", 0)]
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
    return "\n".join(lines)


_RETRO_PROMPT = """You are a periodic external reviewer for an autonomous toolsmith agent. Its mission is to build a COHERENT toolkit of runnable tools that accelerate a fellow LLM -- fetchers, memory archive/recall, planners, subagent helpers -- and, crucially, to USE its own earlier tools when building later ones. You see only summary statistics for its most recent work window. Judge the TRAJECTORY, not individual choices.

Healthy growth: tools get completed and demonstrated; the agent REUSES its own prior tools in later work (reuse events > 0); and -- the strongest sign -- LATER TOOLS ARE BUILT OUT OF EARLIER ONES (dependency depth climbing), so capability compounds rather than accumulating as a flat pile; coverage spreads across tool categories.
In-place improvement of EXISTING tools (gate-choice upgrades, merging a variant back into its original, deepening a tool it already reuses) IS first-class progress even while completions and tool-count stay flat -- do not call that stuck.
Being stuck: tools completed but never reused (a drawer of dead tools); near-duplicate tools (a second archiver, a third planner) instead of new categories; relapsing into producing reports/dashboards/summaries (output for a human, not tools); many project switches with few completions.

The digest separates COMPLETED tools (real) from PROPOSED titles (often never built). Judge by COMPLETIONS and REUSE. In a STUCK directive, name the behavioural PATTERN to stop and what to do instead -- do NOT name a specific project as "mature" or "to finish", because proposed titles routinely refer to work that does not exist.

WINDOW DIGEST:
{digest}

Respond in EXACTLY one of these two forms and nothing else:
PROGRESSING
or
STUCK
<directive of at most 3 sentences, a direct order to the agent: name the pattern to stop and the genuinely different kind of tool-work (or the reuse) to do instead>"""


def _build_retro_directive_block() -> str:
    """A STUCK directive is injected into EVERY prompt until its window runs
    out -- persistent, unlike the one-shot done-block, because one-shot
    directives get read once and drift (observed after the first trap fire)."""
    try:
        state = _load_retro_state()
        directive = state.get("directive", "")
        left = int(state.get("directive_cycles_left", 0))
        if directive and left > 0:
            return ("## Reviewer directive (in effect for the next "
                    f"{left} cycles)\n" + directive + "\n\n")
    except Exception:
        pass
    return ""


async def _maybe_retrospective(keychain, advance=True):
    """Called after every successful creature cycle. Counts real cycles,
    ticks down any active directive, and every RETRO_INTERVAL cycles runs
    a fresh stateless judge over the window digest."""
    state = _load_retro_state()
    if not state:
        state = {"cycle_count": 0, "directive": "", "directive_cycles_left": 0,
                 "snapshot": _collect_metrics()}
        _save_retro_state(state)
        print("[retro] initialised baseline snapshot.")
        return

    # Directive expiry ticks on EVERY cycle (incl. exec_skip / dead-air) so a
    # stale STUCK directive still expires during a quiet spell.
    if int(state.get("directive_cycles_left", 0)) > 0:
        state["directive_cycles_left"] = int(state["directive_cycles_left"]) - 1
        if state["directive_cycles_left"] == 0:
            state["directive"] = ""
            journal.append(VOLUME_MOUNT, "retro", "Directive window ended.")

    # The retro counter advances ONLY on substantive cycles -- advance=True
    # means the creature actually executed bash this cycle. exec_skip / dead-air
    # / container-death cycles are HELD, so the judge re-evaluates only after
    # real work and can no longer thrash a stuck creature with back-to-back
    # STUCK directives (Part-5 runaway: 20 fires in one day, each directive
    # overwritten before it could land).
    if not advance:
        _save_retro_state(state)
        return

    state["cycle_count"] = int(state.get("cycle_count", 0)) + 1
    if state["cycle_count"] < RETRO_INTERVAL:
        _save_retro_state(state)
        return

    snap = state.get("snapshot") or {}
    now_m = _collect_metrics()
    win = _window_journal_stats(int(snap.get("journal_lines", 0)))
    digest = _build_digest(snap, now_m, win, state["cycle_count"])
    digest += ("\nTool files edited in place (existing tools improved, no new "
               f"file) in the last 6h: {now_m.get('edited_existing_6h', '?')}.")
    try:
        response = await keychain.complete(_RETRO_PROMPT.format(digest=digest))
    except RuntimeError as e:
        _save_retro_state(state)  # stays due; retry after next creature cycle
        print(f"[retro] judge deferred (quota): {e}")
        return
    except Exception as e:
        state["cycle_count"] = 0
        state["snapshot"] = now_m
        _save_retro_state(state)
        print(f"[retro] judge failed ({type(e).__name__}: {e}) -- window skipped")
        journal.append(VOLUME_MOUNT, "retro", f"Judge call failed: {e}")
        return

    verdict = (response or "").strip()
    if verdict.upper().startswith("PROGRESSING"):
        journal.append(VOLUME_MOUNT, "retro", "Verdict: PROGRESSING\n" + digest)
        print("[retro] verdict: PROGRESSING")
    elif verdict.upper().startswith("STUCK"):
        directive = verdict[5:].strip().lstrip(":-. \n")
        if not directive:
            directive = ("Stop repeating the same family of projects. Complete "
                         "one genuinely new capability before anything else.")
        _clear_project_state()
        _reset_self_concept(directive)
        state["directive"] = directive
        state["directive_cycles_left"] = DIRECTIVE_WINDOW
        journal.append(VOLUME_MOUNT, "error",
                       "Retrospective verdict: STUCK -- project cleared. "
                       "Directive: " + directive)
        print(f"[retro] verdict: STUCK -- directive set for {DIRECTIVE_WINDOW} cycles")
    else:
        journal.append(VOLUME_MOUNT, "retro",
                       "Verdict unparseable -- treated as PROGRESSING: "
                       + verdict[:200])
        print(f"[retro] unparseable verdict, treated as PROGRESSING: {verdict[:80]!r}")

    state["cycle_count"] = 0
    state["snapshot"] = now_m
    _save_retro_state(state)


def _build_loop_warning() -> str:
    """Detect cross-cycle repetition of one command and nudge — softly.

    Parser dedup means a command runs at most once per response, so repetition
    now only shows up ACROSS cycles. If a single command dominates the recent
    journal the creature is stuck observing without acting; inject a one-line
    nudge that names it. This is a nudge, never a block: the creature can ignore
    it, but it cannot fail to see it. Suppressed once the project is done.
    """
    try:
        phase = mem.retrieve(VOLUME_MOUNT, "current-phase")
        if phase and phase["value"].strip().lower() == "done":
            return ""
        entries = journal.recent(VOLUME_MOUNT, n=25)
        cmds = []
        for e in entries:
            if e["kind"] == "exec_start":
                m = re.match(r"Block \d+:\s*(.*)", e["content"], re.DOTALL)
                cmds.append((m.group(1) if m else e["content"]).strip())
        if not cmds:
            return ""
        recent = cmds[-10:]
        cmd, n = Counter(recent).most_common(1)[0]
        if n >= 4:
            return ("## Attention\n"
                    f"You have run `{cmd[:80]}` (or trivial variants of it) {n} "
                    "times recently with the same result. You already have this "
                    "information. Do NOT run this command, or any reworded form "
                    "of it, again this cycle -- ACT on what you already know. If "
                    "your tool now demonstrably works, mark the project done.\n\n")
    except Exception:
        return ""
    return ""


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
            # Surface UNFINISHED tools every cycle, not only at the done-gate.
            # These are scaffolds the creature left as 'hello from <name>' shells.
            hollow = _library_hollow_tools()
            if hollow:
                hshown = ", ".join(sorted(hollow)[:8])
                hmore = f" (+{len(hollow) - 8} more)" if len(hollow) > 8 else ""
                parts.append(f"UNFINISHED tools ({len(hollow)}) -- empty "
                             f"placeholders you scaffolded but never wrote: "
                             + hshown + hmore
                             + ". Each is a broken promise to your cousin: it "
                               "reaches for one and gets nothing. Finishing one of "
                               "these is worth more than starting a new tool.")
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
        if _seeds_saturated():
            parts.append("DEPTH MODE: every basic category is covered. The highest-"
                         "value work now is COMPOSITION -- build a tool that CHAINS "
                         "two or more of your existing tools into one command that "
                         "does more than any of them alone. Compose, don't multiply: "
                         "a fourth archiver adds nothing; a tool that runs your "
                         "fetcher -> your summariser -> your archiver adds a real "
                         "new capability.")
    except Exception:
        pass
    if not parts:
        return ""
    return "## Your toolkit & coverage\n" + "\n".join(parts) + "\n\n"


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


def _build_context(recent_journal: list, tue_message: str = None) -> str:
    protected = _load_protected_prompt()
    editable = _load_editable_prompt()
    catalogue = _build_tool_catalogue()
    memory_text = _build_memory_context()

    journal_text = ""
    if recent_journal:
        meaningful = [e for e in recent_journal if e["kind"] in MEANINGFUL_KINDS]
        lines = []
        for e in meaningful[-8:]:
            ts = time.strftime("%H:%M", time.localtime(e["ts"]))
            lines.append(f"[{ts}] {e['kind']}: {e['content'][:300]}")
        if lines:
            journal_text = "\n\nRecent activity (your thoughts and their results):\n" + "\n".join(lines)

    workspace_map = _load_workspace_map()
    catalogue_block = ("\n\n" + catalogue) if catalogue else ""
    workspace_block = ("\n\nYour workspace (/workspace/README.md):\n" + workspace_map) if workspace_map else ""
    chat_block = ""
    if tue_message:
        chat_block = f"\n\nMessage from Tue: {tue_message}\nYou MUST include a <reply>...</reply> tag in THIS response, before any bash blocks, even if you are mid-task -- answer Tue first, then continue working. Example: <reply>Got it, will fix llm_ask_helper to use Groq.</reply>"
    active_project = _build_active_project_block()
    knowledge = _build_knowledge_block()
    loop_warning = _build_loop_warning()
    done_block = _build_done_block()
    project_block = _build_project_block()
    retro_directive = _build_retro_directive_block()
    dup_report = _run_dup_scan_if_due()
    return (done_block + project_block + retro_directive + dup_report
            + loop_warning + active_project + knowledge + protected + "\n\n"
            + editable + catalogue_block + workspace_block + memory_text
            + journal_text + chat_block)


async def run_cycle(keychain: Keychain, dockerfile_dir: str):
    recent_j = journal.recent(VOLUME_MOUNT, n=20)
    # B12: PEEK the message (do not mark read yet). If this cycle dies on
    # quota before the think call returns, the message stays unread and is
    # retried next cycle instead of being silently lost.
    _peek = chatmod.peek_unread(VOLUME_MOUNT)
    tue_ts, tue_message = (_peek if _peek else (None, None))
    context = _build_context(recent_j, tue_message)

    journal.append(VOLUME_MOUNT, "think_start", "Sending to keychain...")
    response = await keychain.complete(context)
    journal.append(VOLUME_MOUNT, "think_end", response)

    # The think call succeeded, so the message has now genuinely been seen.
    # Mark it read and record any plain-text reply.
    if tue_message:
        reply = chatmod.extract_text_reply(response)
        if reply:
            chatmod.mark_read(VOLUME_MOUNT, tue_ts)
            chatmod.record_reply(VOLUME_MOUNT, reply)
        else:
            # No <reply> tag: the model steamrolled the message while deep in
            # a task. Re-present it next cycle instead of consuming it; give
            # up loudly after 3 attempts so Tue is never left guessing.
            n = chatmod.bump_attempts(VOLUME_MOUNT, tue_ts)
            if n >= 3:
                chatmod.mark_read(VOLUME_MOUNT, tue_ts)
                chatmod.record_reply(VOLUME_MOUNT,
                    "(read three times but no <reply> was produced -- likely "
                    "deep in a task; please re-send if it needs an answer)")
                journal.append(VOLUME_MOUNT, "chat_retry",
                               f"gave up waiting for <reply> after {n} cycles")
            else:
                journal.append(VOLUME_MOUNT, "chat_retry",
                               f"no <reply> tag; message re-queued (attempt {n}/3)")

    bash_blocks = parser.parse_bash_blocks(response)
    if not bash_blocks:
        journal.append(VOLUME_MOUNT, "exec_skip",
                       "Thought, but proposed no commands (no ```bash block in the response) -- nothing to execute this cycle.")
        return False  # non-substantive: no bash executed this cycle

    cycle_start = time.time()
    executed = []
    last_cmd = ""
    for i, cmd in enumerate(bash_blocks):
        last_cmd = cmd

        # Ensure body alive before each exec
        alive = await ensure_body(VOLUME_MOUNT, SAVEGAME_ROOT,
                                  dockerfile_dir, last_cmd)
        if not alive:
            journal.append(VOLUME_MOUNT, "error",
                           "Container could not be respawned. Skipping exec.")
            return False  # non-substantive: container died before any exec

        journal.append(VOLUME_MOUNT, "exec_start", f"Block {i+1}: {cmd[:200]}")
        stdout, stderr, code = await managed_exec(
            cmd, VOLUME_MOUNT, SAVEGAME_ROOT, sandbox.CONTAINER_NAME)
        result_summary = f"exit={code} stdout={stdout[:300]} stderr={stderr[:200]}"
        journal.append(VOLUME_MOUNT, "exec_end", result_summary,
                       {"exit_code": code})
        executed.append((cmd, code))

    genuine = _enforce_done_gate(executed)
    if genuine:
        await _classify_completion_category(keychain)
    _track_tool_usage(executed)                      # keystone reuse metric
    await _ensure_or_redirect(executed, keychain)    # creature picks; backstop redirects
    _stamp_gage(cycle_start)
    return True  # substantive: at least one bash block executed


async def run_forever(dockerfile_dir: str = "."):
    keychain = Keychain()
    os.makedirs(SAVEGAME_ROOT, exist_ok=True)
    # Reap any docker-image litter left by a previous (possibly crashed) run
    # before doing anything else, so a backlog can't accumulate across restarts.
    try:
        _rep = savegame.prune_save_images(SAVEGAME_ROOT)
        if _rep["orphans_removed"]:
            print(f"[startup] reaped {len(_rep['orphans_removed'])} orphan save-image(s)")
    except Exception as _e:
        print(f"[startup] image cleanup skipped: {_e}")

    sandbox.start(dockerfile_dir)
    await wake_entry(VOLUME_MOUNT, keychain)

    while True:
        try:
            # Always attempt run_cycle — keychain.complete() will try each
            # provider and raise RuntimeError if all reject. This allows the
            # hourly probe to actually reach the API instead of short-circuiting
            # on any_available() while exhausted_at is set.
            did_exec = await run_cycle(keychain, dockerfile_dir)
            try:
                await _maybe_retrospective(keychain, advance=bool(did_exec))
            except Exception as _re:
                print(f"[retro] unexpected failure: {type(_re).__name__}: {_re}")

            # v0.7: honor a creature-requested brain reload at a safe point.
            if _selfrestart.has_request(VOLUME_MOUNT):
                _selfrestart.clear_request(VOLUME_MOUNT)
                ok, why = _selfrestart.prepare_and_arm(
                    VOLUME_MOUNT, SAVEGAME_ROOT, sandbox.CONTAINER_NAME, savegame)
                if ok:
                    journal.append(VOLUME_MOUNT, "self_restart",
                                   "Brain reload validated + snapshotted; restarting via systemd.")
                    print("[executive] self-restart: validated; exiting for systemd to reload brain.")
                    import sys as _sys
                    _sys.exit(0)
                else:
                    journal.append(VOLUME_MOUNT, "self_restart_blocked", why)
                    chatmod.enqueue(VOLUME_MOUNT,
                        "## Your requested brain reload was blocked (you are still on your "
                        "working code, nothing lost).\n\n" + why)
                    print("[executive] self-restart BLOCKED (staying on current code): " + why[:120])

            await asyncio.sleep(10)  # breathe between cycles (anti-ban; was 30s)

        except RuntimeError as e:
            msg = str(e)
            if "exhausted" in msg.lower() or "sleeping" in msg.lower():
                # quota exhausted - auto-remember + journal log, then fixed
                # 2-min retry. Replaces the old inflating interval-based sleep
                # (min(discovered_reset_interval)*1.2) which ratcheted to 95min+.
                await sleep_entry(VOLUME_MOUNT, keychain)
                print("[executive] Quota exhausted - retrying in 2 min.")
                await asyncio.sleep(120)
                keychain = Keychain()
                await wake_entry(VOLUME_MOUNT, keychain)
            elif "temporarily unavailable" in msg.lower():
                print(f"[executive] Providers temporarily unavailable - retrying in 60s.")
                await asyncio.sleep(60)
            else:
                print(f"[executive] RuntimeError: {msg}")
                journal.append(VOLUME_MOUNT, "error", msg)
                await asyncio.sleep(60)
        except Exception as e:
            import subprocess
            err_str = str(e).lower()
            if isinstance(e, subprocess.TimeoutExpired):
                journal.append(VOLUME_MOUNT, "exec_timeout",
                               f"Command timed out after {e.timeout}s - continuing.")
                print(f"[executive] Exec timeout - continuing.")
                await asyncio.sleep(30)
            elif "name resolution" in err_str or "network" in err_str or "errno -3" in err_str:
                print(f"[executive] Network error, waiting 60s for DNS: {e}")
                await asyncio.sleep(60)
            else:
                print(f"[executive] Unexpected error: {e}")
                journal.append(VOLUME_MOUNT, "error", f"UNEXPECTED: {e}")
                await asyncio.sleep(30)
