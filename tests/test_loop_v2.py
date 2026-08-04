"""
Regression test for the v2 re-architecture patch (toolsmith framing + reuse keystone).
Runs against a fresh temp dir with an empty-but-valid memory DB -- no live
memory.db or container needed. Safe to run anywhere the repo is checked out.

Usage (from repo root):
    python tests/test_loop_v2.py
Must print ALL TESTS PASS.
"""
import asyncio, json, os, shutil, sys, tempfile, inspect, time
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
    check("curated catalogue: honest tail names how many are hidden + how to find them",
          "more. Run `tools`" in _cat and "tool-find" in _cat)

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
    if _eg.available():
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
                check("toolfind: request file round-trip answers",
                      _r.get("ok") is True and len(_r.get("results", [])) > 0)
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
        sys.exit(1)
    print("ALL TESTS PASS")


try:
    asyncio.run(main())
finally:
    shutil.rmtree(TMP, ignore_errors=True)
