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

VOLUME_MOUNT = os.path.expanduser("~/growing-spine-mind")
EDITABLE_PROMPT_PATH = os.path.join(VOLUME_MOUNT, "editable-prompt.md")
PROTECTED_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "protected-prompt.md")
SAVEGAME_ROOT = os.path.expanduser("~/growing-spine-saves")
DONE_BLOCK_PATH = os.path.join(VOLUME_MOUNT, "done_block.txt")
WORKSPACE_DIR = os.path.expanduser("~/growing-spine-workspace")
RETRO_STATE_PATH = os.path.join(VOLUME_MOUNT, "retrospective_state.json")
RETRO_INTERVAL = 20      # real creature cycles between retrospectives
DIRECTIVE_WINDOW = 20    # cycles a STUCK directive stays in every prompt



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
        return toolmod.build_catalogue(VOLUME_MOUNT)
    except Exception:
        return ""



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


DONE_MARK_RE = re.compile(r'remember\s+current-phase\s+["\']?done["\']?', re.I)



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
        f"You have attempted the same failing check `{bad_cmd[:80]}` "
        f"{count} times in a row without making real progress. "
        "This approach is structurally broken -- retrying will not fix it.\n\n"
        "Your current project has been cleared by the executive.\n\n"
        "You MUST start a completely different project. Do NOT attempt to fix "
        "the same tool or a variation of it. Do NOT make another report or index. "
        "Choose a genuinely new goal, set current-project and current-plan, "
        "and write a DONE WHEN that does not depend on the broken tool."
    )
    try:
        with open(DONE_BLOCK_PATH, "w", encoding="utf-8") as f:
            f.write(reason)
        journal.append(VOLUME_MOUNT, "error",
                       f"Spin trap: abandoned project after {count}x "
                       f"`{bad_cmd[:80]}`")
    except Exception:
        pass


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
            return  # done not asserted this cycle

        failures = [(c, code) for (c, code) in executed
                    if code != 0 and not c.strip().startswith("remember ")
                    and not DONE_MARK_RE.search(c)]
        if not failures:
            _record_completion()  # genuine completion: log it durably
            return

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
            return

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
    """Project switches, done-gate blocks and spin fires since a journal line."""
    sets, blocks, fires = [], 0, 0
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
                elif kind == "error":
                    if "Done-gate blocked" in content:
                        blocks += 1
                    elif "Spin trap" in content:
                        fires += 1
    except Exception:
        pass
    distinct = list(dict.fromkeys(sets))
    return {"project_sets": len(sets), "distinct_projects": distinct,
            "blocks": blocks, "spin_fires": fires}


def _build_digest(snap: dict, now: dict, win: dict, cycles: int) -> str:
    new_completed = now["completed"][snap.get("completions", 0):]
    prev_tail = now["completed"][max(0, snap.get("completions", 0) - 12):
                                 snap.get("completions", 0)]
    lines = [
        f"- real cycles in window: {cycles}",
        f"- projects completed in window: {len(new_completed)}"
        + (f" ({'; '.join(new_completed)})" if new_completed else ""),
        f"- total completions ever: {now['completions']}",
        f"- project switches in window: {win['project_sets']}",
        f"- distinct projects touched: {len(win['distinct_projects'])}"
        + (f" -- {'; '.join(win['distinct_projects'][:15])}"
           if win['distinct_projects'] else ""),
        f"- false 'done' attempts blocked by the executive: {win['blocks']}",
        f"- spin-trap forced abandonments: {win['spin_fires']}",
        f"- tools: {snap.get('tools', '?')} -> {now['tools']}",
        f"- durable memories: {snap.get('memories', '?')} -> {now['memories']}",
        f"- workspace size MB: {snap.get('workspace_mb', '?')} -> {now['workspace_mb']}",
        "- completed before this window: " + ("; ".join(prev_tail) or "none"),
    ]
    return "\n".join(lines)


_RETRO_PROMPT = """You are a periodic external reviewer for an autonomous agent that chooses its own projects in a sandbox. You see only summary statistics for its most recent work window. Judge the TRAJECTORY, not individual choices.

What healthy growth looks like: projects get completed; new work builds on or uses earlier work; capabilities accumulate; durable memory grows.
What being stuck looks like: many project switches with few or no completions; near-duplicate projects under different names (dashboards, reports, indexes, summaries, health checks); repeatedly trying to fix the same broken tools; tool count climbing while completions stay flat.

WINDOW DIGEST:
{digest}

Respond in EXACTLY one of these two forms and nothing else:
PROGRESSING
or
STUCK
<directive of at most 3 sentences, written as a direct order to the agent: name the repeated pattern it must stop, and say what genuinely different kind of work to do instead>"""


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
                    f"You have run `{cmd[:120]}` {n} times recently and the result has "
                    "not changed. Running it again will not change it. Act on the result "
                    "you already have — and if your DONE WHEN is met, write "
                    '`remember current-phase "done"`. Do not run that command again.\n\n')
    except Exception:
        return ""
    return ""


def _build_active_project_block() -> str:
    """Inject current-project and current-phase at the top of context."""
    try:
        project   = mem.retrieve(VOLUME_MOUNT, "current-project")
        phase     = mem.retrieve(VOLUME_MOUNT, "current-phase")
        completed = (mem.retrieve(VOLUME_MOUNT, "completed-log")
                     or mem.retrieve(VOLUME_MOUNT, "completed-projects"))
        # Rows can exist with value "" (e.g. after a spin-trap abandon);
        # treat empty values as absent so we don't render blank lines.
        if project and not project["value"].strip():
            project = None
        if phase and not phase["value"].strip():
            phase = None
        if completed and not completed["value"].strip():
            completed = None
        if not project and not phase:
            return ""
        lines = ["## Active project"]
        if project:
            lines.append(f"Project: {project['value']}")
        if phase:
            lines.append(f"Phase: {phase['value']}")
            if phase["value"].strip().lower() == "done":
                lines.append("-> This project is DONE. Start a new one or use what you built.")
        if completed:
            lines.append(f"\nCompleted projects: {completed['value']}")
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
        chat_block = f"\n\nMessage from Tue: {tue_message}\nReply to this in plain text before your bash blocks."
    active_project = _build_active_project_block()
    loop_warning = _build_loop_warning()
    done_block = _build_done_block()
    retro_directive = _build_retro_directive_block()
    return done_block + retro_directive + loop_warning + active_project + protected + "\n\n" + editable + catalogue_block + workspace_block + memory_text + journal_text + chat_block


async def run_cycle(keychain: Keychain, dockerfile_dir: str):
    recent_j = journal.recent(VOLUME_MOUNT, n=20)
    tue_message = chatmod.pop_unread(VOLUME_MOUNT)
    context = _build_context(recent_j, tue_message)

    journal.append(VOLUME_MOUNT, "think_start", "Sending to keychain...")
    response = await keychain.complete(context)
    journal.append(VOLUME_MOUNT, "think_end", response)

    if tue_message:
        reply = chatmod.extract_text_reply(response)
        if reply:
            chatmod.record_reply(VOLUME_MOUNT, reply)

    bash_blocks = parser.parse_bash_blocks(response)
    if not bash_blocks:
        journal.append(VOLUME_MOUNT, "exec_skip", "No bash blocks in response.")
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

    _enforce_done_gate(executed)
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
