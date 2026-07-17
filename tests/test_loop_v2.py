"""
Regression test for the v2 re-architecture patch (toolsmith framing + reuse keystone).
Runs against a fresh temp dir with an empty-but-valid memory DB -- no live
memory.db or container needed. Safe to run anywhere the repo is checked out.

Usage (from repo root):
    python tests/test_loop_v2.py
Must print ALL TESTS PASS.
"""
import asyncio, json, os, shutil, sys, tempfile, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from executive import loop
from volume import memory as mem

TMP = tempfile.mkdtemp(prefix="spine_v2_")
os.makedirs(os.path.join(TMP, "tools", "own"), exist_ok=True)
mem.init_db(TMP)

# Redirect all state to TMP
loop.VOLUME_MOUNT = TMP
loop.IDEATION_STATE_PATH = os.path.join(TMP, "ideation_state.json")
loop.RETRO_STATE_PATH = os.path.join(TMP, "retrospective_state.json")
loop.DONE_BLOCK_PATH = os.path.join(TMP, "done_block.txt")
loop.PROJECT_BLOCK_PATH = os.path.join(TMP, "project_block.txt")
loop.TOOL_USAGE_PATH = os.path.join(TMP, "tool_usage.json")
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


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
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

    # B7: junk catalogue lines filtered
    orig = loop.toolmod.build_catalogue
    loop.toolmod.build_catalogue = lambda vm: (
        "Built-in:\n  remember - Save a fact.\n"
        "Made:\n  foo - Provides the foo functionality.\n"
        "  baz - Archives notes under keywords.\n")
    cat = loop._build_tool_catalogue()
    loop.toolmod.build_catalogue = orig
    check("B7 junk lines removed + real kept",
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
    check("oracle assigns finish_stub when backlog over tolerance",
          spec.get("category") == "finish_stub" and spec.get("title", "").startswith("pend_"))
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
    from keychain import provider as kc_provider
    pt, pn = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": "hi"}}], "usage": {"total_tokens": 7}})
    check("provider extract: normal content + usage", pt == "hi" and pn == 7)
    pt, pn = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": None, "reasoning": "thought"}}], "usage": None})
    check("provider extract: null content falls to reasoning, null usage safe",
          pt == "thought" and pn == len("thought") // 4)
    pt, pn = kc_provider._extract_text_tokens(
        {"choices": [{"message": {"content": None, "reasoning": None}}]})
    check("provider extract: both null -> empty text, no len(None)",
          pt == "" and pn == 0)

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
        sys.exit(1)
    print("ALL TESTS PASS")


try:
    asyncio.run(main())
finally:
    shutil.rmtree(TMP, ignore_errors=True)
