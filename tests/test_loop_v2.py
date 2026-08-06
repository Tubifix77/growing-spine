"""
Regression test for the v2 re-architecture patch (toolsmith framing + reuse keystone).
Runs against a fresh temp dir with an empty-but-valid memory DB -- no live
memory.db or container needed. Safe to run anywhere the repo is checked out.

Usage (from repo root):
    python tests/test_loop_v2.py
Must print ALL TESTS PASS.
"""
import asyncio, json, os, shutil, sys, tempfile, inspect, time

TMP = tempfile.mkdtemp(prefix="spine_v2_")
REAL_MIND = os.path.expanduser("~/growing-spine-mind")

# MUST precede the executive imports: embed_gate freezes VOLUME_MOUNT from the
# environment at import time (embed_gate.py:22), so a later reassignment would
# leave the REAL embedding index as the one this suite refreshes.
os.environ["VOLUME_MOUNT"] = TMP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from executive import loop
from volume import tools as vtools
from volume import memory as mem

os.makedirs(os.path.join(TMP, "tools", "own"), exist_ok=True)
os.makedirs(os.path.join(TMP, "state"), exist_ok=True)
mem.init_db(TMP)


def _repoint_all(mod, real, tmp):
    """Repoint EVERY module-level path derived from the real mind dir.

    2026-08-05: this used to be six hand-written assignments, and it had missed
    FIVE paths -- including GATE_CHOICE_STATE_PATH, the done-gate's arming file.
    _clear_project_state() deletes that file unconditionally and this suite calls
    it six times, so every run disarmed the live "the chosen target file must
    actually change" enforcement -- and self_restart.py runs this suite ON THE
    LIVE HOST at every creature-requested deploy-self, i.e. precisely during
    self-modification. Enumerating by hand is what rotted; discover instead, so a
    new path constant is repointed the day it is added.
    """
    moved = []
    for name in dir(mod):
        if not name.isupper():
            continue
        val = getattr(mod, name)
        if isinstance(val, str) and val.startswith(real):
            dest = tmp + val[len(real):]
            setattr(mod, name, dest)
            parent = os.path.dirname(dest)
            if parent:
                os.makedirs(parent, exist_ok=True)
            moved.append(name)
    return moved


_suite_path = os.path.abspath(__file__)
REPOINTED = _repoint_all(loop, REAL_MIND, TMP)
loop.VOLUME_MOUNT = TMP
loop.journal.append = lambda *a, **k: None


class FakeKC:
    def __init__(self): self.mode = "tool"
    async def complete(self, prompt, max_tokens=None):
        if "TOOL or OUTPUT" in prompt:
            return "OUTPUT" if self.mode == "output" else "TOOL"
        if "STRICT JSON" in prompt:
            return ('{"title":"keyword archive store","brief":"Stores notes under '
                    'keywords durably.","demonstration":"Archive two notes and show '
                    'the file.","category":"memory_archive"}')
        if "Classify a tool" in prompt or "Which category" in prompt:
            return "memory_archive"
        return "PROGRESSING"


fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + ((" -- " + extra) if extra else ""))
    if not cond:
        fails.append(name)


async def main():
    kc = FakeKC()

    # B1/B8: knowledge block always renders coverage even with no active project
    loop._clear_project_state()
    json.dump({"categories_built": {}, "block_streak": 0},
              open(loop.IDEATION_STATE_PATH, "w"))
    kb = loop._build_knowledge_block()
    check("B1 knowledge block shows coverage when project cleared",
          "coverage" in kb.lower())

    # creature picks a TOOL -> allowed, not redirected
    kc.mode = "tool"
    loop._clear_project_state()
    mem.store(TMP, "current-project", "fast keyword archive: store notes")
    mem.store(TMP, "current-phase", "explore")
    await loop._ensure_or_redirect(
        [('remember current-project "fast keyword archive"', 0)], kc)
    proj = mem.retrieve(TMP, "current-project")
    check("creature's TOOL pick is left alone",
          bool(proj and "fast keyword archive" in proj["value"]))

    # creature picks a BASIN thing -> redirected to a concrete gap, phase=code
    kc.mode = "output"
    loop._last_pick["title"] = ""
    loop._clear_project_state()
    mem.store(TMP, "current-project", "Sentiment Analysis Dashboard")
    mem.store(TMP, "current-phase", "explore")
    await loop._ensure_or_redirect(
        [('remember current-project "Sentiment Analysis Dashboard"', 0)], kc)
    proj = mem.retrieve(TMP, "current-project")
    phase = mem.retrieve(TMP, "current-phase")
    focus = mem.retrieve(TMP, "current_focus")
    check("basin relapse is redirected away from the dashboard",
          bool(proj and "Dashboard" not in proj["value"]))
    check("redirect sets phase=code",
          bool(phase and phase["value"].strip() == "code"))
    check("redirect seeds [assigned] focus",
          bool(focus and focus["value"].startswith("[assigned]")))

    # anti-idle: no project + nothing set -> a gap is assigned
    kc.mode = "tool"
    loop._clear_project_state()
    await loop._ensure_or_redirect([("ls /workspace", 0)], kc)
    proj = mem.retrieve(TMP, "current-project")
    check("anti-idle assigns a gap when creature idles",
          bool(proj and proj["value"].strip()))

    # B-7 reuse tracking
    with open(os.path.join(TMP, "tools", "own", "my-archive"), "w") as f:
        f.write("#!/usr/bin/env python3\nprint('hi')\n")
    loop._track_tool_usage([("my-archive --add note", 0), ("ls", 0)])
    usage = loop._load_tool_usage()
    check("B-7 reuse of an own tool is counted",
          usage.get("my-archive", 0) == 1)
    loop._track_tool_usage([("tool-new my-archive", 0)])
    check("B-7 tool-new creation is not counted as reuse",
          loop._load_tool_usage().get("my-archive", 0) == 1)
    kb2 = loop._build_knowledge_block()
    check("B-8 toolkit view shows the built tool + reuse", "my-archive" in kb2)

    # category classification updates coverage
    mem.store(TMP, "current-project", "keyword archive store: notes")
    await loop._classify_completion_category(kc)
    cb = (loop._load_ideation_state() or {}).get("categories_built", {})
    check("category classification bumps coverage",
          cb.get("memory_archive", 0) >= 1)

    # B3: self-concept reset clears stale planning keys
    for k in ("project-plan", "testing", "refinement"):
        mem.store(TMP, k, "stale")
    loop._reset_self_concept("test directive")
    check("B3 stale planning keys cleared on reset",
          all(not (mem.retrieve(TMP, k) or {}).get("value", "").strip()
              for k in ("project-plan", "testing", "refinement")))

    # B2: retro prompt forbids naming specific projects; flags proposals vs completions
    check("B2 retro prompt warns proposals vs completions",
          "PROPOSED" in loop._RETRO_PROMPT and "REUSE" in loop._RETRO_PROMPT.upper())
    check("B2 retro prompt forbids naming a specific project",
          "do NOT name" in loop._RETRO_PROMPT)

    # B7: junk catalogue lines filtered -- specifically the FALLBACK path
    # (curated catalogue, 2026-08-04, has no reason to hit the junk phrases
    # since it reads does-lines directly; the fallback is what a young/
    # embed-unavailable library still uses, and must still filter junk).
    orig = loop.toolmod.build_catalogue
    orig_avail = loop.embed_gate.available
    loop.toolmod.build_catalogue = lambda vm: (
        "Built-in:\n  remember - Save a fact.\n"
        "Made:\n  foo - Provides the foo functionality.\n"
        "  baz - Archives notes under keywords.\n")
    loop.embed_gate.available = lambda: False
    cat = loop._build_tool_catalogue()
    loop.toolmod.build_catalogue = orig
    loop.embed_gate.available = orig_avail
    check("B7 junk lines removed + real kept (fallback path)",
          "Provides the foo" not in cat and "Archives notes" in cat)

    # B4: loop warning uses intent-based language
    check("B4 warning mentions reworded variants",
          "reworded form" in inspect.getsource(loop._build_loop_warning))

    # dependency depth: digest-builder calls fetch-news -> 1 dependency edge
    owndir = os.path.join(TMP, "tools", "own")
    with open(os.path.join(owndir, "fetch-news"), "w") as f:
        f.write("#!/usr/bin/env python3\nprint('news')\n")
    with open(os.path.join(owndir, "digest-builder"), "w") as f:
        f.write("#!/usr/bin/env bash\nfetch-news | head\n")
    g = loop._tool_dependencies()
    check("dependency: digest-builder depends on fetch-news",
          "fetch-news" in g.get("digest-builder", []))
    ds = loop._dependency_summary()
    # avg_depth averages over all tools; with 3 tools at depths 0/0/1 -> 0.33.
    # Check edges (>=1) and that at least one tool has a dependency (with_deps>=1).
    check("dependency summary reports >=1 edge and >=1 tool with deps",
          ds.get("edges", 0) >= 1 and ds.get("with_deps", 0) >= 1)
    kb3 = loop._build_knowledge_block()
    check("toolkit block shows compounding line", "compounding" in kb3.lower())

    # B12: a Tue message must survive a cycle that dies before the think call.
    # peek_unread must NOT mark read; mark_read flips it only after success.
    import json as _json
    chatmod = __import__("executive.chat", fromlist=["chat"])
    chatmod.enqueue(TMP, "hello creature")
    _peek = chatmod.peek_unread(TMP)
    check("B12 peek returns the message", bool(_peek) and _peek[1] == "hello creature")
    _peek2 = chatmod.peek_unread(TMP)
    check("B12 message still unread after peek (survives failed cycle)",
          bool(_peek2) and _peek2[1] == "hello creature")
    _ts = _peek[0] if _peek else None
    check("B12 mark_read flips the message", chatmod.mark_read(TMP, _ts) is True)
    check("B12 message read after mark_read", chatmod.peek_unread(TMP) is None)
    check("B12 re-marking an already-read message returns False",
          chatmod.mark_read(TMP, _ts) is False)

    # BUG A: robust category parsing -- chatty/preamble replies must still map.
    check("A parse: clean label", loop._parse_category("information_fetch") == "information_fetch")
    check("A parse: preamble then label",
          loop._parse_category("We need to classify. Answer: planning") == "planning")
    check("A parse: spaces instead of underscores",
          loop._parse_category("memory recall") == "memory_recall")
    check("A parse: keyword backstop (delegate->subagent)",
          loop._parse_category("a tool that delegates to another model") == "subagent_orchestration")
    check("A parse: fetch keyword -> information_fetch",
          loop._parse_category("downloads json from a url") == "information_fetch")
    check("A parse: genuinely unknown -> other",
          loop._parse_category("a banana peeler") == "other")

    # BUG B: done-gate must block marking done on a hollow tool-new placeholder.
    owndir = os.path.join(TMP, "tools", "own")
    # a hollow placeholder tool, freshly created this cycle
    with open(os.path.join(owndir, "hollow_tool"), "w") as f:
        f.write("#!/usr/bin/env python3\n# does: DESCRIBE WHAT THIS TOOL DOES - edit this line\n# Replace this whole file with real executable code\n")
    holl = loop._hollow_tools_touched([("tool-new hollow_tool", 0)])
    check("B detects a hollow placeholder tool", "hollow_tool" in holl)
    # a real tool created this cycle must NOT be flagged
    with open(os.path.join(owndir, "real_tool"), "w") as f:
        f.write("#!/usr/bin/env python3\nimport sys, json\nprint(json.dumps({'ok': True}))\nx = sum(range(10))\n")
    holl2 = loop._hollow_tools_touched([("tool-new real_tool", 0)])
    check("B does NOT flag a real tool", "real_tool" not in holl2)
    # full gate: mark done + a hollow tool-new this cycle -> blocked (returns False)
    import volume.memory as _m
    _m.store(TMP, "current-project", "hollow_tool: a json fetcher")
    _m.store(TMP, "current-phase", "done")
    gate = loop._enforce_done_gate([("tool-new hollow_tool", 0), ('remember current-phase "done"', 0)])
    check("B gate blocks done on a hollow tool (returns False)", gate is False)

    # NEW: cross-cycle library backlog. Create enough hollow stubs (beyond the
    # tolerance) WITHOUT touching them this cycle, then mark a CLEAN project done.
    # The widened gate must still block, citing the library backlog.
    for i in range(loop.HOLLOW_BACKLOG_TOLERANCE + 2):
        with open(os.path.join(owndir, f"stub_{i}"), "w") as f:
            f.write("#!/usr/bin/env python3\n# does: DESCRIBE WHAT THIS TOOL DOES - edit this line\nimport sys\nprint('hello from ' + sys.argv[0])\n")
    lib_holl = loop._library_hollow_tools()
    check("library scan finds cross-cycle stubs",
          len([h for h in lib_holl if h.startswith("stub_")]) >= loop.HOLLOW_BACKLOG_TOLERANCE + 2)
    # a clean tool marked done, nothing hollow touched THIS cycle, but backlog exists
    with open(os.path.join(owndir, "clean_done_tool"), "w") as f:
        f.write("#!/usr/bin/env python3\nimport sys\nprint('real output')\nx = 1 + 1\n")
    _m.store(TMP, "current-project", "clean_done_tool: a real tool")
    _m.store(TMP, "current-phase", "done")
    gate2 = loop._enforce_done_gate([("clean_done_tool", 0), ('remember current-phase "done"', 0)])
    check("B gate blocks done when library backlog exceeds tolerance", gate2 is False)
    # clean up the stubs so they don't pollute later tests
    for i in range(loop.HOLLOW_BACKLOG_TOLERANCE + 2):
        try: os.remove(os.path.join(owndir, f"stub_{i}"))
        except Exception: pass

    # NEW: oracle must assign a stub-FINISH when backlog is over tolerance,
    # instead of briefing a brand-new tool. (main() is async, so await directly.)
    for i in range(loop.HOLLOW_BACKLOG_TOLERANCE + 2):
        with open(os.path.join(owndir, f"pend_{i}"), "w") as f:
            f.write("#!/usr/bin/env python3\n# does: DESCRIBE WHAT THIS TOOL DOES - edit this line\nimport sys\nprint('hello from ' + sys.argv[0])\n")
    class _FakeKC:
        async def complete(self, *a, **k):
            return "PROGRESSING"  # should never be reached for the finish path
    spec = await loop._oracle_next_spec(_FakeKC())
    # Asserts the CONTRACT (a finish assignment aimed at a real stub), not the
    # picker's proxy: 2026-08-06 the picker moved from shortest-name to
    # most-demanded, and this fixture's owndir carries earlier tests' stubs with
    # usage, so hardcoding "pend_" was measuring the old heuristic. The demand
    # ordering itself is covered in isolation further down.
    check("oracle assigns finish_stub when backlog over tolerance",
          spec.get("category") == "finish_stub"
          and spec.get("title") in loop._library_hollow_tools())
    for i in range(loop.HOLLOW_BACKLOG_TOLERANCE + 2):
        try: os.remove(os.path.join(owndir, f"pend_{i}"))
        except Exception: pass

    # NEW: extension-collision duplicate scan. Create a shell tool and its .py
    # twin with different usage counts; the scan should pair them, higher-use
    # first, and NOT pair unrelated tools.
    with open(os.path.join(owndir, "twintool"), "w") as f:
        f.write("#!/usr/bin/env bash\necho real\nx=1\n")
    with open(os.path.join(owndir, "twintool.py"), "w") as f:
        f.write("#!/usr/bin/env python3\nprint('real')\nx = 1\n")
    with open(os.path.join(owndir, "lonelytool"), "w") as f:
        f.write("#!/usr/bin/env bash\necho solo\ny=2\n")
    # set usage so twintool (5) > twintool.py (1)
    _u = loop._load_tool_usage()
    _u["twintool"] = 5; _u["twintool.py"] = 1
    loop._save_tool_usage(_u)
    pairs = loop._extension_collision_pairs()
    twin_pairs = [p for p in pairs if p[0].startswith("twintool") or p[2].startswith("twintool")]
    check("collision scan finds the .py twin", len(twin_pairs) == 1)
    if twin_pairs:
        keep, uk, drop, ud = twin_pairs[0]
        check("collision scan puts higher-use tool first (keep)",
              keep == "twintool" and drop == "twintool.py")
    check("collision scan does NOT pair unrelated tools",
          not any("lonelytool" in (p[0], p[2]) for p in pairs))
    for t in ("twintool", "twintool.py", "lonelytool"):
        try: os.remove(os.path.join(owndir, t))
        except Exception: pass

    # NEW: systematic rut detection state machine (streak -> confirm -> ban -> cooldown)
    loop._reset_basin_streak()
    # three consecutive SAME-theme relapses must escalate the streak to threshold
    s1 = loop._record_basin_relapse("sentiment")
    s2 = loop._record_basin_relapse("sentiment")
    s3 = loop._record_basin_relapse("sentiment")
    check("basin streak counts consecutive same-theme relapses",
          s1 == 1 and s2 == 2 and s3 == 3 and s3 >= loop.BASIN_YANK_THRESHOLD)
    # a DIFFERENT theme resets the streak to 1
    s4 = loop._record_basin_relapse("dashboard")
    check("basin streak resets when the theme changes", s4 == 1)
    # theme detection picks the right keyword
    check("basin theme detection finds the tripping keyword",
          loop._basin_theme_of("Customer Sentiment Analysis Report") in ("sentiment","report","analytics"))
    check("basin theme detection returns empty for a clean tool name",
          loop._basin_theme_of("json_diff_merger") == "")
    # arming a ban makes the theme active for the cooldown window, then it expires
    loop._arm_theme_ban("sentiment")
    active_now = loop._banned_theme_active()
    check("armed ban reports the theme as active", active_now == "sentiment")
    # burn down the cooldown; it must expire to '' eventually
    for _ in range(loop.BASIN_COOLDOWN_CYCLES + 2):
        expired = loop._banned_theme_active()
    check("ban expires after cooldown window", expired == "")
    loop._reset_basin_streak()
    ph = _m.retrieve(TMP, "current-phase")
    check("B gate reverts phase to code", bool(ph) and ph["value"].strip() == "code")

    # v0.10.1 regression: a FAILED yank must not leave a silent ban behind.
    # Old order armed the ban before the oracle call; an oracle failure then
    # left a ban armed with no yank message and no redirect installed. New
    # order fetches the redirect first and arms the ban last, so on failure:
    # no ban, streak preserved (retry next relapse), pick stands (fail-open).
    loop._reset_basin_streak()
    loop._record_basin_relapse("sentiment")
    loop._record_basin_relapse("sentiment")  # streak=2; the pick below makes 3
    _real_oracle = loop._oracle_next_spec
    async def _boom(_kc):
        raise RuntimeError("oracle down (simulated)")
    loop._oracle_next_spec = _boom
    kc.mode = "output"  # judge calls the pick a basin OUTPUT
    loop._last_pick["title"] = ""
    loop._clear_project_state()
    mem.store(TMP, "current-project", "Sentiment Alerting Service")
    mem.store(TMP, "current-phase", "explore")
    await loop._ensure_or_redirect(
        [('remember current-project "Sentiment Alerting Service"', 0)], kc)
    loop._oracle_next_spec = _real_oracle
    st = loop._load_ideation_state() or {}
    proj = mem.retrieve(TMP, "current-project")
    check("failed yank arms no silent ban", not st.get("banned_theme"))
    check("failed yank preserves the streak for a retry",
          int(st.get("basin_relapse_streak", 0)) >= loop.BASIN_YANK_THRESHOLD)
    check("failed yank fails open (the pick stands)",
          bool(proj and "Sentiment Alerting" in proj["value"]))
    loop._reset_basin_streak()
    loop._clear_project_state()

    # ---- batch_judge parser resilience (the 4/4 0/N live refills, Jul 15-16) ----
    from executive import idea_gate
    bj_reg = {"fetch_url": "fetch a url and print it",
              "research_task_planner": "plan research tasks from questions",
              "memstore": "store a memory"}
    bj_items = [{"title": "A", "brief": "a"},
                {"title": "B", "brief": "b"},
                {"title": "C", "brief": "c"}]
    styled = ("We need to decide for each idea whether an existing tool covers "
              "its intent. Tools marked [consolidated] are prior art. I will "
              "answer now.\n"
              "**1.** DUPLICATE of research_task_planner\n"
              "IDEA 2: NEW\n"
              "3 - EXTEND:fetch_url\n")
    async def _bj_styled(prompt, max_tokens=None):
        return styled
    bj_out = await idea_gate.batch_judge(bj_items, bj_reg, _bj_styled)
    check("batch_judge parses styled verdicts under a prose preamble",
          bj_out.get(0) == ("DUPLICATE", "research_task_planner")
          and 1 not in bj_out and bj_out.get(2) == ("EXTEND", "fetch_url"))
    async def _bj_prose(prompt, max_tokens=None):
        return "We need to decide if each idea is covered. Considering the intents..."
    check("batch_judge fails open (empty) on prose-only reply",
          await idea_gate.batch_judge(bj_items, bj_reg, _bj_prose) == {})
    async def _bj_think(prompt, max_tokens=None):
        return ("<think>deliberation that once ate the whole budget</think>"
                "1: DUPLICATE:fetch_url\n2: NEW\n3: NEW")
    bj_out = await idea_gate.batch_judge(bj_items, bj_reg, _bj_think)
    check("batch_judge strips <think> blocks before parsing",
          bj_out.get(0) == ("DUPLICATE", "fetch_url"))

    # ---- provider extraction None-safety (the 02:00 len(None) cycle-killer) ----
    # Arity grew to 4 on 2026-08-05 (finish_reason, reasoning_only). The
    # reasoning-fallback case below used to assert the substitution was DESIRED;
    # it was only ever a crash fix, and downstream it meant a truncated
    # deliberation arrived at scanning parsers as if it were the answer. The
    # text is still returned for diagnosis, but the flag now says what it is.
    from keychain import provider as kc_provider
    pt, pn, pf, pr = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": "hi"}}], "usage": {"total_tokens": 7}})
    check("provider extract: normal content + usage", pt == "hi" and pn == 7
          and pr is False)
    pt, pn, pf, pr = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": None, "reasoning": "thought"}}], "usage": None})
    check("provider extract: null content falls to reasoning, null usage safe",
          pt == "thought" and pn == len("thought") // 4)
    check("provider extract: and that fallback is now MARKED reasoning-only",
          pr is True)
    pt, pn, pf, pr = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": None, "reasoning": None}}]})
    check("provider extract: both null -> empty text, no len(None)",
          pt == "" and pn == 0 and pr is False)

    # ---- keychain error taxonomy (tonight's real strings, 2026-07-17) ----
    from keychain.keychain import classify_error
    check("classify: empty completion -> flaky (next provider, not abort)",
          classify_error("empty completion (content and reasoning both null)") == "flaky")
    check("classify: read timeout -> flaky",
          classify_error("The read operation timed out") == "flaky")
    check("classify: openrouter upstream 429 -> quota (probe machinery heals)",
          classify_error('HTTP 429: {"error":{"message":"Provider returned error"'
                         ',"code":429}} temporarily rate-limited upstream') == "quota")
    check("classify: groq 413 TPM -> too_large",
          classify_error("HTTP 413: Request too large ... TPM Limit 12000") == "too_large")
    check("classify: per-minute rate limit -> retryable",
          classify_error("rate_limit hit: 30 requests per minute") == "retryable")
    check("classify: unknown -> hard",
          classify_error("something exploded weirdly") == "hard")
    check("classify: dead model 404 -> quota (walls, never hard-raises)",
          classify_error('HTTP 404: {"error":{"message":"No endpoints found for '
                         'qwen/qwen3-coder:free"}}') == "quota")
    check("classify: model_not_found -> quota",
          classify_error("model_not_found: that model id does not exist") == "quota")

    # ---- upward re-probe ordering (the nemotron-monopoly fix) ----
    from keychain.keychain import order_providers
    provs = [{"key": "coder"}, {"key": "nemotron"}]
    now = 1000000.0
    st_cooled  = {"coder": {"exhausted_at": now - 700, "last_success_at": 0},
                  "nemotron": {"exhausted_at": 0, "last_success_at": now - 60}}
    st_cooling = {"coder": {"exhausted_at": now - 60, "last_success_at": 0},
                  "nemotron": {"exhausted_at": 0, "last_success_at": now - 60}}
    check("upward reprobe: cooled higher rung outranks open lower rung",
          [p["key"] for p in order_providers(provs, st_cooled, now)] == ["coder", "nemotron"])
    check("upward reprobe: still-cooling higher rung stays at the tail",
          [p["key"] for p in order_providers(provs, st_cooling, now)] == ["nemotron", "coder"])
    check("upward reprobe: all-open keeps config order",
          [p["key"] for p in order_providers(provs, {}, now)] == ["coder", "nemotron"])

    # ---- batch judge: reasoning-model reply with terminal VERDICTS block ----
    # (the exact live failure shape from 2026-07-19 02:34: prose deliberation
    # incl. "Choose EXTEND:X", verdicts only in a final block)
    from executive.idea_gate import _scan_verdict_lines
    _reply = ("We need to decide for each idea whether an existing tool already "
              "covers its intent. Use intent, not wording. Idea one seems novel. "
              "Idea two: tracker not present. Might be EXTEND of alpha_tool. "
              "Choose EXTEND:alpha_tool.\n\nVERDICTS:\n1: NEW\n2: EXTEND:alpha_tool\n"
              "3: DUPLICATE:beta_tool\n")
    _n, _hits = _scan_verdict_lines(_reply, 3)
    check("batch judge scan: terminal VERDICTS block parses after prose (3/3)",
          _n == 3 and _hits[0][0] == "NEW"
          and _hits[1] == ("EXTEND", "alpha_tool")
          and _hits[2] == ("DUPLICATE", "beta_tool"))
    check("batch judge scan: prose-only reply still parses zero (fail-open)",
          _scan_verdict_lines("We should pick EXTEND for the tracker idea.", 3)[0] == 0)

    # ---- judge twins fused (2026-08-02): single path = batch of one ----
    from executive.idea_gate import _single_from_batch
    check("fused judge: covered batch-of-one maps to the single contract",
          _single_from_batch({0: ("DUPLICATE", "archive_backed_query")}) ==
          {"verdict": "DUPLICATE", "target": "archive_backed_query",
           "reason": "batch-of-one judge", "parsed": True, "candidates": []})
    check("fused judge: empty result fails open as NEW",
          _single_from_batch({})["verdict"] == "NEW"
          and _single_from_batch({})["parsed"] is True)

    # ---- truthful toolkit framing (Genesis-2 proofing, 2026-08-02) ----
    from executive import loop as _lp
    check("toolkit framing: broad claim above the threshold",
          "ALREADY built a broad" in _lp._toolkit_framing(count=30))
    check("toolkit framing: a young library gets the honest brief",
          "YOUNG" in _lp._toolkit_framing(count=3)
          and "3 tools so far" in _lp._toolkit_framing(count=3)
          and _lp.BROAD_TOOLKIT_THRESHOLD == 25)

    # ---- retro hysteresis + directive arbitration (2026-08-03) ----
    _st = {}
    _f1, _ = _lp._stuck_should_fire(_st)
    _f2, _ = _lp._stuck_should_fire(_st)
    # ---- curated catalogue (2026-08-04 incident fix) ----
    _cown = os.path.join(TMP, "tools", "own")
    _cfw = os.path.join(TMP, "tools", "framework")
    os.makedirs(_cown, exist_ok=True)
    os.makedirs(_cfw, exist_ok=True)
    open(os.path.join(_cfw, "tool-find"), "w").write(
        "#!/usr/bin/env python3\n# does: search tools by meaning\n")
    open(os.path.join(_cfw, "tool-new"), "w").write(
        "#!/usr/bin/env bash\n# does: create a new tool\n")
    for i in range(90):  # exceed the 70-tool budget so a real remainder exists
        open(os.path.join(_cown, f"ctool_{i}"), "w").write(
            f"#!/usr/bin/env bash\n# does: does thing number {i} with archives\n")
    _cj = os.path.join(TMP, "journal.jsonl")
    with open(_cj, "w") as f:
        for _ in range(9):
            f.write(json.dumps({"kind": "exec_start",
                                "content": "Block 1: /mind/tools/own/ctool_3 run"}) + "\n")
    loop.USAGE_CACHE_PATH = os.path.join(TMP, "state", "usage_cache_test.json")
    loop.SURFACED_STATE_PATH = os.path.join(TMP, "state", "surfaced_test.json")
    _counts = loop._update_usage_cache()
    check("usage cache: cold scan counts the referenced tool",
          _counts.get("ctool_3") == 9)
    with open(_cj, "a") as f:
        f.write(json.dumps({"kind": "exec_start",
                            "content": "Block 1: /mind/tools/own/ctool_3 run"}) + "\n")
    _counts2 = loop._update_usage_cache()
    check("usage cache: incremental scan only adds the NEW line (10, not 18)",
          _counts2.get("ctool_3") == 10)
    _sz_before = os.path.getsize(_cj)
    with open(_cj, "w") as f:
        f.write(json.dumps({"kind": "exec_start",
                            "content": "Block 1: /mind/tools/own/ctool_7 run"}) + "\n")
    check("usage cache: shrunk journal (rotation) triggers a safe rescan, not a crash",
          loop._update_usage_cache().get("ctool_7") == 1)

    _cat = loop._build_tool_catalogue()
    check("curated catalogue: built-ins present verbatim",
          "tool-find" in _cat and "tool-new" in _cat)
    _names_seen = [ln.strip().split(" - ")[0].strip()
                   for ln in _cat.splitlines() if ln.startswith("  ")]
    check("curated catalogue: no tool listed twice across sections",
          len(_names_seen) == len(set(_names_seen)))
    check("curated catalogue: far smaller than the old full alphabetical dump",
          len(_cat) < 6000)
    # Embedder-dependent: without an index _build_tool_catalogue correctly falls
    # back to the FULL listing, which has no hidden tail. That made this read as
    # a hard failure on machines without the model (a WSL run, 2026-08-05) and
    # cost a parallel session real time deciding whether it had broken something.
    # Embedder-dependent: with no index _build_tool_catalogue correctly falls back
    # to the FULL listing, which has no hidden tail and so cannot name one. That
    # made this read as a hard failure on a machine without the model (a WSL run,
    # 2026-08-05) and cost a parallel session real time deciding whether it had
    # broken something. Assert the tail only where a tail can exist.
    from executive import embed_gate as _eg_probe
    _eg_ok = _eg_probe.available()
    check("curated catalogue: honest tail names how many are hidden + how to find them"
          if _eg_ok else
          "curated catalogue tail -- SKIPPED (no embedder: full-listing fallback)",
          (("more. Run `tools`" in _cat and "tool-find" in _cat) if _eg_ok else True))

    # ---- flatline sensor (2026-08-04 incident fix) ----
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import spine_health as _H
    _H.CONFIG = os.path.join(TMP, "config_health_test.yaml")
    _H.QUOTA_STATE = os.path.join(TMP, "quota_health_test.json")
    with open(_H.CONFIG, "w") as f:
        f.write("providers:\n- key: alive\n  enabled: true\n"
                "- key: dead\n  enabled: true\n- key: off\n  enabled: false\n")
    _now = time.time()
    json.dump({"alive": {"last_success_at": _now - 3600},
               "dead": {"last_success_at": _now - 20 * 3600},
               "off": {}}, open(_H.QUOTA_STATE, "w"))
    _flat = _H.check_flatline()
    check("flatline sensor: recent success is fine, disabled providers are ignored",
          "alive" not in _flat and "off" not in _flat)
    check("flatline sensor: a silent enabled provider past the threshold is flagged loudly",
          "FLATLINE:!!" in _flat and "dead(20h)" in _flat)
    json.dump({"alive": {"last_success_at": _now - 3600}},
              open(_H.QUOTA_STATE, "w"))  # 'dead' never even attempted
    check("flatline sensor: a provider with NO recorded success ever is also flagged",
          "dead(never)" in _H.check_flatline())

    # ---- hollow-stub organ re-armed (2026-08-06) ----
    # The markers had never matched what tool-new writes, so six organs no-oped
    # for their entire existence. These cover the canonical marker list, the
    # merged demand reader, and the janitor's new sparing rule.
    check("markers: the CURRENT tool-new template is recognised as hollow",
          vtools.is_hollow_stub("#!/usr/bin/env python3\n"
                                "# Replace the body below with real executable code.\n"
                                "print('not implemented yet: x')\n"))
    check("markers: legacy template still recognised (old attic residents)",
          vtools.is_hollow_stub("# does: DESCRIBE WHAT THIS TOOL DOES - edit this line"))
    check("markers: a real tool is not hollow",
          vtools.is_hollow_stub("import sys\nprint(sum(int(a) for a in sys.argv[1:]))") is False)

    _dmnd = os.path.join(TMP, "demand_test")
    os.makedirs(os.path.join(_dmnd, "state"), exist_ok=True)
    json.dump({"flat_only": 6, "both": 2, "with_ext.py": 9},
              open(os.path.join(_dmnd, "tool_usage.json"), "w"))
    json.dump({"offset": 5, "counts": {"both": 10, "/mind/tools/own/pathy": 7}},
              open(os.path.join(_dmnd, "state", "tool_usage_cache.json"), "w"))
    _dc = vtools.demand_counts(_dmnd)
    check("demand: both counters merged, MAX not sum (2 vs 10 -> 10)",
          _dc.get("both") == 10)
    check("demand: flat-only entries survive the merge", _dc.get("flat_only") == 6)
    check("demand: keys normalised across .py suffix and full paths",
          _dc.get("with_ext") == 9 and _dc.get("pathy") == 7)
    check("demand: floor sits in the live distribution gap (10 kept, 4 swept)",
          vtools.is_demanded("both", _dc) and not vtools.is_demanded("nothing", _dc))

    _jown = os.path.join(TMP, "jan", "tools", "own")
    _jatt = os.path.join(TMP, "jan", "tools", "attic")
    os.makedirs(_jown, exist_ok=True)
    _shell = ("#!/usr/bin/env python3\n"
              "# Replace the body below with real executable code.\n"
              "print('not implemented yet: x')\n")
    for _n in ("wanted_stub", "abandoned_stub", "young_stub"):
        open(os.path.join(_jown, _n), "w").write(_shell)
    open(os.path.join(_jown, "real_tool"), "w").write("print(1 + 1)\n")
    _old = time.time() - 9 * 86400
    for _n in ("wanted_stub", "abandoned_stub", "real_tool"):
        os.utime(os.path.join(_jown, _n), (_old, _old))
    json.dump({"wanted_stub": 40, "abandoned_stub": 1},
              open(os.path.join(TMP, "jan", "tool_usage.json"), "w"))
    _H.OWN, _H.ATTIC, _H.MIND = _jown, _jatt, os.path.join(TMP, "jan")
    _jres = _H.stub_janitor()
    check("janitor: an aged, unwanted shell is finally attic'd (was aged-out 0 forever)",
          "aged-out 1" in _jres and os.path.exists(os.path.join(_jatt, "abandoned_stub")))
    check("janitor: an aged shell the creature keeps calling is SPARED, not attic'd",
          "SPARED-DEMANDED:1" in _jres
          and os.path.exists(os.path.join(_jown, "wanted_stub")))
    # A .bak of a filled stub is hollow by markers but is NOT a tool: it must not
    # inflate the backlog, and the janitor must not sweep the creature's safety net.
    open(os.path.join(_jown, "wanted_stub.bak_1786000000"), "w").write(_shell)
    os.utime(os.path.join(_jown, "wanted_stub.bak_1786000000"), (_old, _old))
    _jres2 = _H.stub_janitor()
    check("janitor: the creature's own .bak safety net is never attic'd",
          "aged-out 0" in _jres2
          and os.path.exists(os.path.join(_jown, "wanted_stub.bak_1786000000")))

    check("janitor: young shells and real tools are left alone",
          os.path.exists(os.path.join(_jown, "young_stub"))
          and os.path.exists(os.path.join(_jown, "real_tool")))

    _fsown = os.path.join(TMP, "tools", "own")
    os.makedirs(_fsown, exist_ok=True)
    for _n in ("stub_dull", "stub_wanted"):
        open(os.path.join(_fsown, _n), "w").write(_shell)
    json.dump({"stub_wanted": 33, "stub_dull": 1},
              open(os.path.join(TMP, "tool_usage.json"), "w"))
    _fspec = _lp._finish_stub_spec()
    check("finish_stub: the assignment targets the MOST-DEMANDED shell",
          _fspec.get("title") == "stub_wanted")
    open(os.path.join(_fsown, "stub_wanted.bak_1786000001"), "w").write(_shell)
    check("hollow census: a .bak backup is not a tool and never enters the backlog",
          "stub_wanted.bak_1786000001" not in _lp._library_hollow_tools()
          and "stub_wanted.bak_1786000001" not in _lp._own_tool_names())
    try: os.remove(os.path.join(_fsown, "stub_wanted.bak_1786000001"))
    except OSError: pass
    for _n in ("stub_dull", "stub_wanted"):
        try: os.remove(os.path.join(_fsown, _n))
        except OSError: pass

    # ---- retro verdict contract (2026-08-06): same cure as the batch judge ----
    _pv = _lp._parse_retro_verdict
    check("retro: terminal block parses (the reasoning-window shape)",
          _pv("Let me weigh this. Reuse is up, depth climbing.\n\n"
              "VERDICT: PROGRESSING")[0] == "PROGRESSING")
    check("retro: the LAST verdict wins, not a mused-about one",
          _pv("At first glance this looks STUCK -- a drawer of dead tools.\n"
              "But reuse events are 6 and depth climbed.\n\nVERDICT: PROGRESSING")[0]
          == "PROGRESSING")
    _v, _d = _pv("Deliberating...\n\nVERDICT: STUCK\nStop building a third "
                 "planner. Reuse memory_archive_search in your next tool.")
    check("retro: a STUCK directive is taken from AFTER the terminal line",
          _v == "STUCK" and _d.startswith("Stop building a third planner")
          and "Deliberating" not in _d)
    check("retro: markdown-decorated verdict lines still parse",
          _pv("thoughts\n\n**VERDICT: STUCK**\nName the pattern.")[0] == "STUCK")
    check("retro: the LEGACY terse contract still parses (old prompt, old windows)",
          _pv("PROGRESSING")[0] == "PROGRESSING"
          and _pv("STUCK\nDo something else.") == ("STUCK", "Do something else."))
    check("retro: a bare verdict alone on a line is a last-resort read",
          _pv("I considered the digest.\n\nSTUCK\n")[0] == "STUCK")
    check("retro: genuinely unreadable prose stays unparseable (fails open, loudly)",
          _pv("The agent seems fine to me, broadly speaking.")[0] is None
          and _pv("")[0] is None)

    _J = __import__("json")   # shadow-proof: `_js`/`json` are rebound later in this function
    # ---- STALE-FALLBACKS (2026-08-06): printed since Aug 2, never read ----
    _fb_built = {"title": "already_built_probe", "brief": "do a thing"}
    open(os.path.join(TMP, "tools", "own", "already_built_probe"), "w").write("print(1)\n")
    check("stale fallbacks: a fallback naming an existing tool is detected",
          _lp._fallback_is_stale(_fb_built) is True)
    check("stale fallbacks: one naming an unbuilt tool is not",
          _lp._fallback_is_stale({"title": "nothing_like_this_exists"}) is False)
    _up = _lp._as_upgrade(_fb_built)
    check("stale fallbacks: an all-stale pool becomes IN-PLACE UPGRADES, not duplicates",
          _up["upgrade_of"] == "already_built_probe"
          and "ALREADY EXISTS" in _up["brief"]
          and "_v2" in _up["brief"])
    check("stale fallbacks: a fresh pool is returned untouched",
          _lp._fresh_fallbacks([{"title": "nothing_like_this_exists", "brief": "b"}])
          == [{"title": "nothing_like_this_exists", "brief": "b"}])

    # ---- P4-F11 / P1-F21 (2026-08-06): quoted keys, and a chip that admits it ----
    check("P4-F11: a QUOTED key is matched now (was invisible to the done-gate)",
          bool(_lp.DONE_MARK_RE.search('remember "current-phase" done'))
          and bool(_lp.DONE_MARK_RE.search("remember current-phase done"))
          and bool(_lp.PROJECT_SET_RE.search('remember "current-project" x')))
    _psm = _lp._PROJECT_SET_RE.search('remember "current-project" archive indexer')
    check("P4-F11: and the project NAME still extracts from a quoted form",
          bool(_psm) and _psm.group(1).startswith("archive indexer"))
    check("P4-F11: an unrelated remember is still not a done-mark",
          not _lp.DONE_MARK_RE.search("remember current-phase testing"))

    # ---- P2-F2 / P2-F14 (2026-08-06): one answer to "is this a tool" ----
    _td = os.path.join(TMP, "tools", "own")
    os.makedirs(os.path.join(_td, "a_directory_named_like_a_tool"), exist_ok=True)
    open(os.path.join(_td, "real_one.py"), "w").write("print(1)\n")
    open(os.path.join(_td, "notes.md"), "w").write("# notes\n")
    open(os.path.join(_td, "real_one.py.bak_1"), "w").write("print(1)\n")
    _listed = vtools.list_tools(_td)
    check("P2-F2: a DIRECTORY with a tool-shaped name is not a tool",
          "a_directory_named_like_a_tool" not in _listed)
    check("P2-F2: docs and .bak backups are not tools either",
          "notes.md" not in _listed and "real_one.py.bak_1" not in _listed)
    check("P2-F2: loop and the canonical lister agree on the same directory",
          set(_lp._own_tool_names()) == set(_listed))
    check("P2-F14: one stem definition -- .bash and .txt strip like .py and .sh",
          (vtools.tool_stem("x.bash"), vtools.tool_stem("x.txt"),
           vtools.tool_stem("x.py"), vtools.tool_stem("x.sh"),
           vtools.tool_stem("x")) == ("x", "x", "x", "x", "x"))
    check("P2-F14: a non-tool extension is left alone",
          vtools.tool_stem("report.pdf") == "report.pdf")

    # ---- P2-F9 (2026-08-06): ONE cluster taxonomy, not two ----
    check("P2-F9: every cluster shown to the model also has title keywords",
          all(len(_row) == 3 and _row[0] and _row[1] and _row[2]
              for _row in _lp.TOOL_CLUSTERS))
    _labels = [r[0] for r in _lp.TOOL_CLUSTERS]
    check("P2-F9: the two clusters the checker used to be blind to are present",
          any("research" in l for l in _labels)
          and any("question" in l for l in _labels))
    check("P2-F9: labels are unique, so the summary cannot double-count a cluster",
          len(set(_labels)) == len(_labels))
    _mem_kw = [k for r in _lp.TOOL_CLUSTERS for k in r[1]]
    check("P2-F9: no member keyword is claimed by two clusters (first match wins)",
          len(set(_mem_kw)) == len(_mem_kw))

    # ---- P2-F6/F13/F16 (2026-08-06): the anti-drift guards ----
    from volume import paths as _paths_mod
    check("P2-F13: one derivation of the mind root, and VOLUME_MOUNT wins",
          _paths_mod.mind_root() == os.environ.get("VOLUME_MOUNT")
          or os.environ.get("VOLUME_MOUNT") is None)

    _p6 = os.path.join(TMP, "tools", "own", "desc_probe")
    os.makedirs(os.path.dirname(_p6), exist_ok=True)
    open(_p6, "w").write("#!/usr/bin/env python3\n"
                         "# does: chain the archive search into a digest\n"
                         "print(1)\n")
    check("P2-F6: catalogue and dedup now read the SAME description",
          vtools.tool_description(_p6) == idea_gate.extract_description(_p6)
          == "chain the archive search into a digest")
    _p6b = os.path.join(TMP, "tools", "own", "desc_probe_late")
    open(_p6b, "w").write("#!/usr/bin/env python3\n" + "x = 1\n" * 40 +
                          "# does: a purpose line far below the old 25-line window\n")
    check("P2-F6: dedup no longer misses a does: line the catalogue can see",
          idea_gate.extract_description(_p6b) ==
          "a purpose line far below the old 25-line window")

    mem.store(TMP, "twin_probe", "v")
    check("P2-F16a: memory.delete delegates to forget (one implementation)",
          mem.delete(TMP, "twin_probe") is True
          and mem.retrieve(TMP, "twin_probe") is None)

    # ---- P1-F19 (2026-08-06): a corrupt meta must disarm image reaping ----
    from volume import savegame as _sg
    _sgroot = os.path.join(TMP, "savegames_f19")
    os.makedirs(_sgroot, exist_ok=True)
    _J.dump({"ts": 1, "body_image": "img:good", "label": "ok"},
             open(os.path.join(_sgroot, "meta-good.json"), "w"))
    open(os.path.join(_sgroot, "meta-broken.json"), "w").write("{not json")
    _sg.CORRUPT_METAS.clear()
    _saves = _sg.list_saves(_sgroot)
    check("P1-F19: an unreadable meta is RECORDED, not silently skipped",
          len(_saves) == 1 and "meta-broken.json" in _sg.CORRUPT_METAS)

    # ---- P1-F20: a repair must not eat appends that land mid-repair ----
    _jp = os.path.join(TMP, "journal.jsonl")
    with open(_jp, "w") as _jf:
        _jf.write(_J.dumps({"ts": 1, "kind": "a", "content": "one"}) + "\n")
        _jf.write("{torn fragment without close\n")
    _H.MIND = TMP
    _res20 = _H.journal_integrity()
    _after = [l for l in open(_jp).read().splitlines() if l.strip()]
    check("P1-F20: repair keeps the good line and writes atomically",
          "JOURNAL:" in _res20 and len(_after) >= 1
          and _J.loads(_after[0])["content"] == "one")
    check("P1-F20: no .repair.tmp left behind",
          not os.path.exists(_jp + ".repair.tmp"))

    # ---- P1-F13 (2026-08-06): a re-stored memory must climb back ----
    mem.store(TMP, "sinker", "first value", tags=["t"])
    for _i in range(8):
        mem.store(TMP, f"filler_{_i}", f"v{_i}")
    _l1 = [r["key"] for r in mem.layer1(TMP)]
    check("P1-F13: an old memory has indeed sunk out of working memory",
          "sinker" not in _l1)
    time.sleep(0.01)
    mem.store(TMP, "sinker", "REFRESHED value")
    _l1b = [r["key"] for r in mem.layer1(TMP)]
    check("P1-F13: re-storing it brings it BACK (was insertion-ordered, so it never did)",
          _l1b[0] == "sinker")
    check("P1-F13: and the refreshed VALUE is what surfaces",
          mem.retrieve(TMP, "sinker")["value"] == "REFRESHED value")

    # ---- P1-F14/P2-F8: exact-key lookup, not substring search ----
    mem.store(TMP, "current_focus", "build the archive indexer")
    mem.store(TMP, "unrelated_note", "current_focus is a red herring string")
    _ft = _lp._current_focus_text()
    check("P1-F14: focus text is the exact key's VALUE, not a list repr",
          _ft == "build the archive indexer"
          and not _ft.startswith("[") and "'key'" not in _ft)

    # ---- P1-F10/P2-F4/P3-D5 (2026-08-06): read the key the writer writes ----
    from executive import runtime as _rt

    class _FakeKC:
        def __init__(self, st): self.state = st; self.providers = [{"key": "a"}, {"key": "b"}]
    check("sleep estimate: uses the measured last_recovery_secs",
          abs(_rt.sleep_duration_seconds(
              _FakeKC({"a": {"last_recovery_secs": 600},
                       "b": {"last_recovery_secs": 200}})) - 220.0) < 1)
    check("sleep estimate: the never-written last_window_duration is no longer consulted",
          _rt.sleep_duration_seconds(
              _FakeKC({"a": {"last_window_duration": 600}})) == 3600)
    check("sleep estimate: floor of 60s still holds",
          _rt.sleep_duration_seconds(_FakeKC({"a": {"last_recovery_secs": 5}})) == 60.0)

    # ---- P1-F2 (2026-08-06): the in-place-edit metric must earn both words ----
    _m6 = os.path.join(TMP, "tools", "own")
    os.makedirs(_m6, exist_ok=True)
    for _n in list(os.listdir(_m6)):
        try: os.remove(os.path.join(_m6, _n))
        except OSError: pass
    for _n in ("old_tool", "old_tool.bak_1786000000", "newborn_tool", "stale_tool"):
        open(os.path.join(_m6, _n), "w").write("print(1)\n")
    _ancient = time.time() - 9 * 86400
    os.utime(os.path.join(_m6, "stale_tool"), (_ancient, _ancient))
    _lp._save_retro_state({"snapshot": {"tool_names": ["old_tool", "stale_tool"]}})
    _mm = _lp._collect_metrics()
    check("P1-F2: a .bak backup no longer double-counts one genuine edit",
          "old_tool.bak_1786000000" not in _mm.get("tool_names", []))
    check("P1-F2: a tool born inside the window is not an 'in-place edit'",
          _mm["edited_existing_6h"] == 1 and _mm["edit_count_basis"] == "vs-prev-snapshot")
    check("P1-F2: a tool untouched for 9 days is not counted either",
          "stale_tool" in _mm.get("tool_names", []))
    _lp._save_retro_state({})
    _mm2 = _lp._collect_metrics()
    check("P1-F2: with no prior snapshot it degrades to counting recent, junk-free files",
          _mm2["edited_existing_6h"] == 2 and _mm2["edit_count_basis"] == "first-window")
    for _n in ("old_tool", "old_tool.bak_1786000000", "newborn_tool", "stale_tool"):
        try: os.remove(os.path.join(_m6, _n))
        except OSError: pass

    # ---- crash-net (2026-08-06): the rollback had NEVER fired in the project's
    # life, because only a FAST crash-loop could reach it. Bench-tested, fixed,
    # pinned here. Fake savegame/chat: nothing live is touched.
    from executive import self_restart as _SR

    class _FakeSave:
        def __init__(self): self.restored = []
        def brain_diff(self, a, b): return "fake-diff"
        def restore_brain(self, c): self.restored.append(c)

    class _FakeChat:
        def __init__(self): self.msgs = []
        def enqueue(self, vm, m): self.msgs.append(m)

    _cn_seq = [0]

    def _boot(ago, starts):
        _cn_seq[0] += 1
        vm = os.path.join(TMP, "crashnet_%d" % _cn_seq[0])
        os.makedirs(vm, exist_ok=True)
        json.dump({"in_flight": True, "good_commit": "AAA", "bad_commit": "BBB",
                   "armed_at": time.time() - ago, "starts_since_arm": starts,
                   "good_save_tag": "save-A"},
                  open(os.path.join(vm, _SR.STATE_FILE), "w"))
        sv, ch = _FakeSave(), _FakeChat()
        rolled = _SR.boot_check(vm, sv, ch)
        st = json.load(open(os.path.join(vm, _SR.STATE_FILE)))
        return rolled, sv.restored, st.get("in_flight"), ch.msgs

    _r, _rest, _armed, _msgs = _boot(10, 2)
    check("crash-net: a FAST crash-loop rolls back and tells the creature why",
          _r is True and _rest == ["AAA"] and _armed is False
          and _msgs and "rolled back" in _msgs[0])
    _r, _rest, _armed, _ = _boot(120, 2)
    check("crash-net: a SLOW crash-loop rolls back too (used to disarm as SUCCESS)",
          _r is True and _rest == ["AAA"] and _armed is False)
    _r, _rest, _armed, _ = _boot(300, 5)
    check("crash-net: a very slow loop is not left armed-and-inert forever",
          _r is True and _armed is False)
    _r, _rest, _armed, _ = _boot(300, 0)
    check("crash-net: a healthy self-restart disarms without rolling back",
          _r is False and _rest == [] and _armed is False)
    _r, _rest, _armed, _ = _boot(7200, 4)
    check("crash-net: a stale arm disarms, never reverts an hours-old change",
          _r is False and _rest == [] and _armed is False)

    # ---- A leftovers (2026-08-06): container keys + a sensor that can fail ----
    from executive import sandbox as _sb
    _cfgk = {"providers": [
        {"key": "gemini_flash", "api_key": "k1", "enabled": True},
        {"key": "groq", "api_key": "k2", "enabled": True},
        {"key": "google_gemma", "api_key": "k3", "enabled": True},
        {"key": "openrouter_super", "api_key": "k4", "enabled": True},
        {"key": "openrouter_gemma", "api_key": "k5", "enabled": False},
        {"key": "nokey", "api_key": "", "enabled": True}]}
    _env = _sb.container_api_env(_cfgk)
    check("container keys: every ENABLED provider reaches the body (was 2 of 13)",
          _env.get("GEMINI_FLASH_API_KEY") == "k1"
          and _env.get("GOOGLE_GEMMA_API_KEY") == "k3"
          and _env.get("OPENROUTER_SUPER_API_KEY") == "k4")
    check("container keys: legacy names the creature's own tools use still resolve",
          _env.get("GROQ_API_KEY") == "k2" and _env.get("GEMINI_API_KEY") == "k1")
    check("container keys: benched providers and keyless entries stay out",
          "OPENROUTER_GEMMA_API_KEY" not in _env and "NOKEY_API_KEY" not in _env)

    _ladder = {"providers": [
        {"key": "gemini_flash", "enabled": True}, {"key": "groq", "enabled": True},
        {"key": "cerebras", "enabled": False}, {"key": "google_gemma", "enabled": True},
        {"key": "openrouter_super", "enabled": True},
        {"key": "openrouter_nemotron", "enabled": True}]}
    _prim = _H.primary_rungs(_ladder)
    check("severity: traffic carriers are the rungs above the openrouter floor",
          _prim == {"gemini_flash", "groq", "google_gemma"})
    check("severity: a silent WORKHORSE fails the unit (the 55h outage shape)",
          _H.exit_code({"google_gemma"}, _prim) == 1)
    check("severity: a quiet low rung is expected, not a fault (no crying wolf)",
          _H.exit_code({"openrouter_nemotron", "openrouter_super"}, _prim) == 0)
    # YAML's Norway problem: a bare off/on/yes/no key parses as a BOOLEAN, and the
    # suite's own flatline fixture has `key: off`. Both readers must survive it.
    _norway = {"providers": [{"key": False, "api_key": "k", "enabled": True}]}
    check("config keys: a YAML-bool key (off/on/no) does not crash either reader",
          _H.primary_rungs(_norway) == {"False"}
          and _sb.container_api_env(_norway).get("FALSE_API_KEY") == "k")

    check("retro hysteresis: first strike watches, second fires",
          _f1 is False and _st.get("stuck_pending") is False and _f2 is True)
    _st2 = {"directive": "[architect] chain, do not sibling", "directive_cycles_left": 9}
    _sfx = _lp._apply_reviewer_directive(_st2, "expand now", 20)
    check("directive arbitration: architect slot protected mid-window",
          _st2["directive"].startswith("[architect]") and "protected" in _sfx)
    _st3 = {"directive": "old reviewer note", "directive_cycles_left": 0}
    _lp._apply_reviewer_directive(_st3, "expand now", 20)
    check("directive arbitration: expired/plain slots are writable",
          _st3["directive"] == "expand now" and _st3["directive_cycles_left"] == 20)

    # ---- tool-find membrane (2026-08-03): host answers over /mind/state ----
    from executive import toolfind as _tfm
    _ok, _err = _tfm.answer("")
    check("toolfind: empty query answered honestly", _ok is False and "empty" in _err)
    check("toolfind: birth accidents and backups are never recommended",
          all(_tfm._is_junk(n) for n in
              ["--show", "own", "dummy", "x.bak", "x.bak_1785553447",
               "y.broken_20260709164649", ".hidden", "z.tmp"])
          and not any(_tfm._is_junk(n) for n in
                      ["step-planner-tracker", "wake_catchup_fetcher.real",
                       "knowledge_gap_filler", "own_news_digest"]))
    from executive import embed_gate as _eg
    # 2026-08-05: these two tests used to query the LIVE index -- embed_gate had
    # frozen the real mind dir at import, so they passed by reading production
    # data. Now that the suite is isolated they need their own corpus, which also
    # makes them a real end-to-end check instead of a smoke test.
    _tf_own = os.path.join(TMP, "tools", "own")
    for _nm, _doc in (
            ("plan_from_question", "Turn a question into an ordered plan of steps"),
            ("archive_search", "Search the keyword archive and return matching notes"),
            ("rss_timeline", "Render archived events onto a timeline")):
        open(os.path.join(_tf_own, _nm), "w").write(
            "#!/usr/bin/env python3\n# tool: %s\n# does: %s\nprint('ok')\n" % (_nm, _doc))
    if _eg.available():
        # refresh() self-throttles on _REFRESH_INTERVAL (correct in production --
        # it must not re-embed every wake). An earlier test in this file already
        # tripped it, so without resetting the clock this refresh is discarded and
        # the query runs against an empty index.
        _eg._last_refresh = 0
        _eg.refresh({"live": _tf_own})
        _ok2, _res2 = _tfm.answer("make a plan from a question", k=5)
        if _ok2:
            check("toolfind: live index returns bare live names",
                  0 < len(_res2) <= 5 and all(":" not in n for n, _ in _res2))
            import tempfile, json as _j
            with tempfile.TemporaryDirectory() as _td:
                _j.dump({"id": "t1", "q": "search the archive", "k": 3},
                        open(os.path.join(_td, "toolfind_req.json"), "w"))
                _tfm._handle_once(_td)
                _r = _j.load(open(os.path.join(_td, "toolfind_res_t1.json")))
                _names = [n for n, _ in _r.get("results", [])]
                # The temp corpus also holds tools other tests wrote, so assert the
                # SEMANTICS: bare names, and the archive query ranks the archive
                # tool first. A mere non-empty check passed for months against the
                # live index and proved nothing.
                check("toolfind: round-trip ranks the right tool first, bare names",
                      _r.get("ok") is True and _names
                      and all(":" not in n for n in _names)
                      and _names[0] == "archive_search",
                      extra=str(_names[:4]))
        else:
            print("SKIP toolfind live tests (index busy)")
    else:
        print("SKIP toolfind live tests (embed unavailable)")

    # ---- Meta-Architect v1 (2026-08-01) ----
    from executive import architect as arch
    _r = ("<thought>Let me weigh these.</thought>\nThe library is bloated.\n"
          "ARCHITECT:\nIDEA 1: KEEP | chain fetch_gap_plan into it, edit in place\n"
          "IDEA 2: DROP | duplicate of archive_backed_query\n"
          "IDEA 3: RESHAPE | a tool that verifies archived claims against sources\n"
          "DIRECTIVE: edit files in place; no _v2 siblings\nWANTED: truth audit; diff view; nothing\n")
    _n, _d, _dir, _w = arch.parse_architect(_r, 3)
    check("architect parse: 3/3 verbs through thought-preamble and prose",
          _n == 3 and _d[0][0] == "KEEP" and _d[1][0] == "DROP" and _d[2][0] == "RESHAPE")
    check("architect parse: directive and wanted-list extracted",
          "in place" in _dir and _w[:2] == ["truth audit", "diff view"])
    check("architect parse: prose-only reply fails open (0 ruled)",
          arch.parse_architect("These all look fine to me, carry on.", 3)[0] == 0)
    _items = [{"title": "a", "brief": "ba"}, {"title": "b", "brief": "bb", "gate": ("DUPLICATE", "x")},
              {"title": "c", "brief": "bc", "gate": ("EXTEND", "y")}]
    _kept, _drp = arch.apply_architect(_items, _d)
    check("architect apply: drop removes, reshape sheds gate, keep annotates",
          _drp == 1 and len(_kept) == 2 and "[architect]" in _kept[0]["brief"]
          and _kept[1]["brief"].startswith("a tool that verifies") and "gate" not in _kept[1])
    check("architect lineage census: suffix drift detected",
          bool(arch.LINEAGE_RE.search("subagent_summarize_archive_upgraded"))
          and bool(arch.LINEAGE_RE.search("catchup_x_v2.py"))
          and not arch.LINEAGE_RE.search("plan_from_question"))
    import tempfile as _tmpf
    with _tmpf.TemporaryDirectory() as _d:
        for _n in ["DigestPlanner", "DigestPlanner.py", "solo_tool",
                   "helper.sh", "helper", "junk.bak", "solo2.py"]:
            open(os.path.join(_d, _n), "w").write("x")
        _ev2 = arch.gather_evidence(_d, os.path.join(_d, "nojournal"))
        check("architect evidence: extension twins counted as lineage drift",
              _ev2["lineage_count"] == 4
              and "DigestPlanner.py" in _ev2["lineage_variants"]
              and "helper" in _ev2["lineage_variants"]
              and "solo_tool" not in _ev2["lineage_variants"]
              and "junk.bak" not in _ev2["lineage_variants"])
    _ev_t = {"total": 350, "zero_use_count": 100, "lineage_count": 5,
             "top_used": [("a", 3)], "born_24h": [], "lineage_variants": []}
    _pr = arch.build_prompt([{"title": "x", "brief": "y",
                              "gate": ("DUPLICATE", "tool_x")}], _ev_t)
    check("architect prompt: covered ideas are upgrade candidates, not deletions",
          "an UPGRADE of tool_x, not a new file" in _pr
          and "KEEP them unless X itself is not worth deepening" in _pr
          and "is NOT a keep -- it is a keep with no guidance" in _pr)
    # 2026-08-05: "KEEP them by default" read as licence to omit the line;
    # a fork's guidance IS the ruling, so the contract now states the count.
    _pr3 = arch.build_prompt([{"title": "a", "brief": "b"},
                              {"title": "c", "brief": "d",
                               "gate": ("EXTEND", "tool_c")},
                              {"title": "e", "brief": "f"}], _ev_t)
    check("architect prompt: block contract demands a line for every idea",
          "IDEA 1 through IDEA 3, in order" in _pr3
          and "All 3 lines are required, covered and new alike" in _pr3
          and "continuing to IDEA 3" in _pr3)

    # ---- canonical junk predicate (2026-08-05) ----
    # Three copies of "is this file actually a tool?" had drifted: b741e07
    # taught only tool-find about --show / dummy / X.bak_<epoch>, so those kept
    # reaching the embed index and the wake catalogue. embed_gate is now the
    # single source and the other two delegate; this asserts they stay agreed.
    from executive import embed_gate as _eg
    from executive import idea_gate as _ig
    from executive import toolfind as _tf
    _junk_yes = ["--show", "dummy", "own", "x.bak", "x.bak_1785553447",
                 "wake_orient_digest.broken_20260709164649", ".hidden",
                 "keyword-archive.jsonl", "notes.md", "state.json", "a.log"]
    _junk_no = ["plan_from_question", "wake_catchup_fetcher.real", "tool_v2",
                "subagent_memory_helper.py", "helper.sh", "ascii_plot",
                "NewsInsightGenerator", "backup_workspace"]
    check("junk predicate: birth accidents, timestamped .bak and data files caught",
          all(_eg._is_junk(_n) for _n in _junk_yes))
    check("junk predicate: real tools survive (.py/.sh/_v2/.real/backup_ names)",
          not any(_eg._is_junk(_n) for _n in _junk_no))
    check("junk predicate: all three modules agree (they drifted once)",
          all(_eg._is_junk(_n) == _tf._is_junk(_n) == _ig._is_junk(_n)
              for _n in _junk_yes + _junk_no))

    # ---- suite isolation (2026-08-05) ----
    # self_restart.py runs THIS FILE on the live host at every deploy-self. Any
    # module-level path still aimed at the real mind dir is live state this suite
    # mutates -- and _clear_project_state(), called six times below, deletes the
    # done-gate's arming file outright.
    _leaked = sorted(_n for _n in dir(loop) if _n.isupper()
                     and isinstance(getattr(loop, _n), str)
                     and getattr(loop, _n).startswith(REAL_MIND))
    check("suite isolation: no loop path still aims at the live mind dir",
          not _leaked, extra=(", ".join(_leaked) if _leaked else ""))
    # Asserts the CONTRACT (the arming file lives inside TMP), not the mechanism.
    # 2026-08-06: with volume.paths.mind_root() honouring VOLUME_MOUNT -- which
    # this file sets before importing loop -- the derived paths are ALREADY in TMP
    # at import, so _repoint_all correctly finds nothing to rewrite and REPOINTED
    # is legitimately empty. Isolation improved; the old assertion measured the
    # rewrite instead of the outcome. (Same trap as the `pend_` oracle test.)
    check("suite isolation: the done-gate arming file lives inside TMP",
          loop.GATE_CHOICE_STATE_PATH.startswith(TMP))
    check("suite isolation: embed_gate took the temp mind dir at import",
          _eg._MIND == TMP)

    # ---- transport: truncation used to be invisible system-wide ----
    from keychain import provider as _prov
    from keychain.keychain import classify_error as _cls

    def _resp(content=None, reasoning=None, finish="stop", tokens=7):
        return {"choices": [{"finish_reason": finish,
                             "message": {"content": content,
                                         "reasoning": reasoning}}],
                "usage": {"total_tokens": tokens}}

    _t, _tok, _fin, _ro = _prov._extract_text_tokens(_resp("hello"))
    check("transport: a normal completion reports finish_reason and no reasoning-only",
          _t == "hello" and _fin == "stop" and _ro is False and _tok == 7)
    _t, _tok, _fin, _ro = _prov._extract_text_tokens(
        _resp(content=None, reasoning="Let me think about this", finish="length"))
    check("transport: reasoning-only is flagged, not silently returned as the answer",
          _ro is True and _fin == "length" and _t == "Let me think about this")
    _t, _tok, _fin, _ro = _prov._extract_text_tokens(
        _resp(content=None, reasoning=None, finish="length", tokens=None))
    check("transport: both-null survives (the 2026-07-17 len(None) crash)",
          _t == "" and _tok == 0 and _fin == "length" and _ro is False)
    check("transport: a truncated reply is distinguishable from a finished one",
          _prov._extract_text_tokens(_resp("x", finish="length"))[2] == "length"
          and _prov._extract_text_tokens(_resp("x"))[2] == "stop")
    check("transport: reasoning-only routes to the flaky class (hop, do not parse)",
          _cls("empty completion (reasoning-only, answer truncated)") == "flaky"
          and _cls("empty completion (content and reasoning both null)") == "flaky")

    # ---- judge honesty + the parser precedence fixes (2026-08-05) ----
    import json as _js
    _bji = [{"title": "T1", "brief": "b1"}, {"title": "T2", "brief": "b2"},
            {"title": "T3", "brief": "b3"}]
    _bjr = {"fetch_url": "fetch a page"}
    _calls = []

    async def _bj_trunc(prompt, max_tokens=None):
        _calls.append(max_tokens)
        # First call: deliberation only, no terminal block (the live 0/7 shape).
        # Retry at double budget: the block arrives.
        if len(_calls) == 1:
            return "We should weigh each. We used: 1 DUPLICATE" + ("x" * 6000)
        return "VERDICTS:\n1: DUPLICATE:fetch_url\n2: NEW\n3: NEW"

    _st = {}
    _out = await idea_gate.batch_judge(_bji, _bjr, _bj_trunc, stats=_st)
    check("judge: a 0-parse on a truncated reply is retried once at 2x budget",
          len(_calls) == 2 and _calls[1] == _calls[0] * 2
          and _st.get("parsed") == 3 and _out.get(0) == ("DUPLICATE", "fetch_url"))
    _st2, _calls2 = {}, []

    async def _bj_prose2(prompt, max_tokens=None):
        _calls2.append(max_tokens)
        return "I think they all look new to me."

    await idea_gate.batch_judge(_bji, _bjr, _bj_prose2, stats=_st2)
    check("judge: a short prose reply is NOT retried (nothing was truncated)",
          len(_calls2) == 1 and _st2.get("parsed") == 0)
    check("judge: stats let a caller tell 'cleared' from 'never ran'",
          _st2.get("items") == 3 and _st2.get("covered") == 0)
    _p, _h = idea_gate._scan_verdict_lines(
        "1: EXTENDed the archive tool earlier\nVERDICTS:\n1: NEW", 1)
    check("judge: \\b stops 'EXTENDed' in prose from parsing as an EXTEND verdict",
          _h.get(0, ("", ""))[0] == "NEW")
    _p2, _h2 = idea_gate._scan_verdict_lines("1: NEW\n1: NEW\n1: DUPLICATE:x", 1)
    check("judge: the parse count is distinct ideas, not matching lines",
          _p2 == 1)

    _ar = ("IDEA 1: KEEP or DROP? let me check the census first\n"
           "ARCHITECT:\nIDEA 1: DROP | the target is dead\n"
           "DIRECTIVE: edit in place\nWANTED: a; b\n")
    _an, _ad, _adir, _aw = arch.parse_architect(_ar, 1)
    check("architect: LAST wins, so the terminal block beats the deliberation",
          _an == 1 and _ad[0][0] == "DROP" and "target is dead" in _ad[0][1])

    _ex = loop._composition_batch_prompt(3, "<horizon>")
    _blk = _ex[_ex.find("["):_ex.find("]", _ex.find("[")) + 1]
    check("composition prompt: its own STRICT-JSON example is valid JSON",
          len(_js.loads(_blk)) == 2)

    _reg_many = {"archive_backed_query": "query the archive",
                 "keyword_archive_store": "store notes",
                 "fetch_url": "fetch a page"}
    check("judge: a 2-char target no longer binds to an arbitrary tool",
          idea_gate._resolve_batch_target("EXTEND", "ed", "x", _reg_many, None)
          == ("NEW", None))
    check("judge: a generic short target is refused rather than guessed",
          idea_gate._resolve_batch_target("DUPLICATE", "arch", "x", _reg_many, None)
          == ("NEW", None))
    check("judge: an exact name still binds, and a long substring still binds",
          idea_gate._resolve_batch_target("DUPLICATE", "fetch_url", "x", _reg_many,
                                          None) == ("DUPLICATE", "fetch_url")
          and idea_gate._resolve_batch_target("EXTEND", "archive_backed", "x",
                                              _reg_many, None)
          == ("EXTEND", "archive_backed_query"))

    # ---- cluster F: state integrity (2026-08-05) ----
    _aj = os.path.join(TMP, "state", "aj_probe.json")
    loop.journal.atomic_json(_aj, {"k": [1, 2, 3]}, indent=2)
    check("atomic_json: writes valid json and leaves no .tmp behind",
          json.load(open(_aj)) == {"k": [1, 2, 3]}
          and not os.path.exists(_aj + ".tmp"))
    loop._save_retro_state({"cycle_count": 9})
    check("retro state save is atomic (loader round-trips, no tmp)",
          loop._load_retro_state().get("cycle_count") == 9
          and not os.path.exists(loop.RETRO_STATE_PATH + ".tmp"))

    from executive import chat as _chat
    _chat.enqueue(TMP, "hello creature")
    _ts0 = _chat.peek_unread(TMP)[0]
    # the lost-update shape: an append lands between the executive's read and
    # its rewrite. With the flock the rewrite path serialises against enqueue;
    # here we assert the atomic rewrite preserves a message appended just before.
    _chat.enqueue(TMP, "second message")
    check("chat: mark_read flips only its target and keeps the later append",
          _chat.mark_read(TMP, _ts0) is True
          and _chat.peek_unread(TMP)[1] == "second message"
          and os.path.exists(os.path.join(TMP, "chat.jsonl.lock")))

    # ---- journal_lines: unreadable must not become an all-history window ----
    _snap_none = {"journal_lines": None, "completions": 0, "memories": 0}
    _now2 = {"completed": [], "completions": 0, "memories": 0, "tools": 1,
             "edited_existing_6h": 0}
    _win_unavail = {"project_sets": 0, "distinct_projects": [], "blocks": 0,
                    "spin_fires": 0, "tool_reuse": 0, "forced_clears": 0,
                    "unavailable": True}
    _dgu = loop._build_digest(_snap_none, _now2, _win_unavail, 5)
    check("retro digest: missing journal anchor is SAID, not shown as zeros",
          "window stats unavailable" in _dgu
          and "project switches in window" not in _dgu)

    # ---- memory unreadable != memory empty ----
    _real_l1 = loop.mem.layer1
    try:
        loop.mem.layer1 = lambda *_a, **_k: (_ for _ in ()).throw(OSError("locked"))
        _mc = loop._build_memory_context()
    finally:
        loop.mem.layer1 = _real_l1
    check("memory context: a locked DB reports itself instead of reading as amnesia",
          "unreadable this cycle" in _mc and "NOT an empty memory" in _mc)

    # ---- catalogue fat-listing revert is loud above curation size ----
    import contextlib as _ctx2, io as _io2
    _own_dir2 = os.path.join(loop.VOLUME_MOUNT, "tools", "own")
    _pre = set(os.listdir(_own_dir2))
    for _i in range(70):
        open(os.path.join(_own_dir2, f"bulk_tool_{_i:02d}"), "w").write(
            "#!/bin/sh\n# does: bulk probe\necho ok\n")
    _real_avail = loop.embed_gate.available
    _buf3 = _io2.StringIO()
    try:
        loop.embed_gate.available = lambda: False
        with _ctx2.redirect_stdout(_buf3):
            loop._build_tool_catalogue()
    finally:
        loop.embed_gate.available = _real_avail
        for _n in set(os.listdir(_own_dir2)) - _pre:
            os.unlink(os.path.join(_own_dir2, _n))
    check("catalogue: embedder-down fallback to the FULL listing announces itself",
          "FULL" in _buf3.getvalue())

    # ---- the gate that gates deploy-self must actually be able to fail ----
    # Deliberately a SOURCE assertion, not an end-to-end spawn. The end-to-end
    # version copied this suite, injected a failure and ran the copy -- and the
    # copy spawned its own copy, each loading the embedding model, until the host
    # OOMed and had to be power-cycled (2026-08-05, my doing). An env-var guard
    # would have prevented the recursion, but the honest trade is that running
    # the whole suite twice on every creature-requested deploy-self is not worth
    # it. This catches the actual regression -- someone moving the exit back
    # inside the coroutine -- at zero cost and zero risk.
    _own_src = open(_suite_path, encoding="utf-8").read()
    _main_body = _own_src[_own_src.index("async def main():"):_own_src.index("\n_rc = 1")]
    # The tokens are BUILT, not written, because this check lives inside main()
    # and a literal would match its own source -- which it did, twice, while
    # being written. rindex for the same reason: take the last occurrence, which
    # is the real module-level one, not this description.
    _E = "sys." + "exit"
    _R = "asyncio." + "run(main())"
    check("gate integrity: the failure path RETURNS 1 and the exit happens "
          "outside the coroutine, where asyncio cannot swallow it",
          "        return 1" in _main_body
          and (_E + "(1)") not in _main_body
          and (_E + "(_rc)") in _own_src
          and _own_src.rindex(_E + "(_rc)") > _own_src.rindex(_R))

    # chat lock must not be an import-time landmine off POSIX
    check("chat: fcntl is optional so the suite imports on a Windows checkout",
          "try:" in open(os.path.join(
              os.path.dirname(os.path.dirname(_suite_path)),
              "executive", "chat.py"), encoding="utf-8").read().split(
              "import contextlib")[1][:120])

    # ---- fork targets are validated at USE, not just at gate time ----
    # 2026-08-05: a gate tag frozen at refill time pointed at `--show`, a birth
    # accident that cannot be invoked as a command. The creature was handed
    # "upgrade --show", wrote a real 3KB tool into it, then started building
    # `--show-wrapper` to work around the filename.
    _own_dir = os.path.join(loop.VOLUME_MOUNT, "tools", "own")
    os.makedirs(_own_dir, exist_ok=True)
    open(os.path.join(_own_dir, "a_real_tool"), "w").write("#!/bin/sh\necho hi\n")
    check("fork target: junk, missing and empty targets are not forkable",
          not loop._fork_target_ok("--show")
          and not loop._fork_target_ok("dummy")
          and not loop._fork_target_ok("no_such_tool_xyz")
          and not loop._fork_target_ok("")
          and not loop._fork_target_ok(None))
    check("fork target: a real present tool still forks",
          loop._fork_target_ok("a_real_tool"))

    # ---- retro digest: the judge was asked to weigh two facts it never saw ----
    _now_m = {"completed": ["a", "b"], "completions": 2, "memories": 5,
              "tools": 300, "edited_existing_6h": 11}
    _snap_m = {"completions": 2, "memories": 4}
    _win_forced = {"project_sets": 6, "distinct_projects": ["x"], "blocks": 3,
                   "spin_fires": 0, "tool_reuse": 9, "forced_clears": 5}
    _dg = loop._build_digest(_snap_m, _now_m, _win_forced, 20)
    check("retro digest: in-place edits of existing tools are shown",
          "IN-PLACE EDITS of existing tools in the last 6h: 11" in _dg)
    check("retro digest: the reviewer's own clears are not the agent's churn",
          "of which 5 were this reviewer" in _dg)
    _win_clean = dict(_win_forced, forced_clears=0)
    check("retro digest: no forced-clear clause when the reviewer stayed out",
          "this reviewer" not in loop._build_digest(_snap_m, _now_m, _win_clean, 20))

    # ---- tool-edit: the verb the fork law needed and the toolkit lacked ----
    # 2026-08-05: the gate says "edit /mind/tools/own/X ITSELF" for nearly every
    # project, tool-new REFUSES to overwrite, and no edit primitive existed. The
    # creature reached for apply_patch ~1685 times and tool-edit ~140 times
    # across the journal -- verbs from its training prior that did not exist
    # here -- and never once wrote one itself.
    import subprocess as _sp
    _te = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "framework-tools", "tool-edit")
    _te_own = os.path.join(TMP, "te_own")
    os.makedirs(_te_own, exist_ok=True)
    _env = dict(os.environ, SPINE_OWN_DIR=_te_own)

    def _run_te(arg, stdin_text):
        return _sp.run([sys.executable, _te, arg], input=stdin_text, env=_env,
                       capture_output=True, text=True)

    check("tool-edit: exists and is executable", os.access(_te, os.X_OK))
    _victim = os.path.join(_te_own, "victim")
    open(_victim, "w").write("#!/bin/sh\necho v1\n")
    os.chmod(_victim, 0o755)
    check("tool-edit: refuses a tool that does not exist, points at tool-new",
          _run_te("nope_xyz", "x\n").returncode == 1
          and "tool-new nope_xyz" in _run_te("nope_xyz", "x\n").stdout)
    check("tool-edit: refuses empty stdin rather than blanking a live tool",
          _run_te("victim", "").returncode == 1
          and open(_victim).read() == "#!/bin/sh\necho v1\n")
    check("tool-edit: refuses a no-op rewrite (an upgrade must change the file)",
          _run_te("victim", "#!/bin/sh\necho v1\n").returncode == 1)
    _r = _run_te("victim", "#!/bin/sh\n# does: v2\necho v2\n")
    check("tool-edit: rewrites in place, keeps the exec bit, leaves one backup",
          _r.returncode == 0
          and open(_victim).read().endswith("echo v2\n")
          and os.access(_victim, os.X_OK)
          and os.path.exists(_victim + ".bak")
          and open(_victim + ".bak").read() == "#!/bin/sh\necho v1\n")
    check("tool-edit: accepts a full path as well as a bare name",
          _run_te(_victim, "#!/bin/sh\necho v3\n").returncode == 0
          and open(_victim).read().endswith("echo v3\n"))
    check("tool-edit: its catalogue line describes itself, not its example",
          "Rewrite one of your own existing tools in place"
          in vtools._first_doc_line(_te))

    # ---- (a) partial-parse diagnostics (2026-08-05): a 3/17 run used to
    # print like a success while 14 ideas sailed through unruled ----
    check("architect ruled-index runs: leading run vs scattered vs none",
          arch._fmt_ruled({0: ("KEEP", ""), 1: ("DROP", ""), 2: ("KEEP", "")})
          == "1-3"
          and arch._fmt_ruled({0: ("KEEP", ""), 4: ("DROP", "")}) == "1,5"
          and arch._fmt_ruled({}) == "none")
    import contextlib as _ctx
    import io as _io
    _items5 = [{"title": str(_i), "brief": "b"} for _i in range(5)]
    _partial_reply = ("Let me weigh all five.\nARCHITECT:\n"
                      "IDEA 1: KEEP | deepen it\nIDEA 2: DROP | dead target\n"
                      "IDEA 3: KEEP | chain it\n")

    async def _stub_partial(prompt, max_tokens=0):
        return _partial_reply

    _buf = _io.StringIO()
    with _ctx.redirect_stdout(_buf):
        _k5, _drp5, _dir5, _w5 = await arch.run_architect(
            _items5, _ev_t, _stub_partial)
    _out = _buf.getvalue()
    check("architect report: partial parse names fail-opens, run and budget",
          "3/5 ruled [1-3]" in _out and "(2 fail-open)" in _out
          and "2 unruled" in _out and "vs budget 1600 tok" in _out
          and "... tail:" in _out and len(_k5) == 4 and _drp5 == 1)

    async def _stub_full(prompt, max_tokens=0):
        return "ARCHITECT:\n" + "".join(
            f"IDEA {_i}: KEEP | ok\n" for _i in range(1, 6))

    _buf2 = _io.StringIO()
    with _ctx.redirect_stdout(_buf2):
        await arch.run_architect(_items5, _ev_t, _stub_full)
    check("architect report: a full parse prints no diagnostic noise",
          "5/5 ruled [1-5]" in _buf2.getvalue()
          and "fail-open" not in _buf2.getvalue()
          and "unruled" not in _buf2.getvalue())
    check("batch judge scan: gemma <thought> preamble does not block the block",
          _scan_verdict_lines("<thought>musing</thought>\nVERDICTS:\n1: NEW\n2: NEW\n3: NEW", 3)[0] == 3)

    # ---- openrouter tier-check diff (weekly rotating-shelf sensor) ----
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("otc", "scripts/openrouter_tier_check.py")
    _otc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_otc)
    _lines = _otc.diff_report(["a:free", "b:free"], ["b:free", "c:free"],
                              {"a:free": "openrouter_coder"})
    check("tier diff: new model detected", any("c:free" in l and l.startswith("NEW") for l in _lines))
    check("tier diff: gone model detected", any("a:free" in l and l.startswith("GONE") for l in _lines))
    check("tier diff: vanished configured rung flagged loudly",
          any("VANISHED" in l and "openrouter_coder" in l for l in _lines))

    # ---- embed top_matches exclusion (the replay self-match corruption) ----
    from executive import embed_gate as eg
    if eg.available():
        q = "plan_from_question: turn a question into an actionable plan"
        r1 = eg.top_matches(q, k=3)
        if r1:
            top_name = r1[0][0].split(":", 1)[1]
            r2 = [n.split(":", 1)[1] for n, _ in eg.top_matches(q, k=3, exclude={top_name})]
            check("embed exclude: excluded top-1 vanishes, results remain",
                  top_name not in r2 and len(r2) > 0)
        else:
            print("SKIP embed exclude test (empty index)")
    else:
        print("SKIP embed exclude tests (embed unavailable)")

    print()
    if fails:
        print("FAILURES: " + ", ".join(fails))
        return 1
    print("ALL TESTS PASS")
    return 0


# sys.exit() INSIDE the coroutine is swallowed by asyncio.run on Python 3.12+
# (verified 2026-08-05: exit 0 with failures present under 3.12.3, exit 1 under
# this host's 3.11.2). self_restart.py gates every creature-requested
# deploy-self on this file's exit code, so a host Python upgrade would have
# silently disarmed that gate. main() now RETURNS the code and the exit happens
# at module level, where nothing can swallow it.
_rc = 1
try:
    _rc = asyncio.run(main())
finally:
    shutil.rmtree(TMP, ignore_errors=True)
sys.exit(_rc)
