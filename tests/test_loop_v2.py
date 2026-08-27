"""
Regression test for the v2 re-architecture patch (toolsmith framing + reuse keystone).
Runs against a fresh temp dir with an empty-but-valid memory DB -- no live
memory.db or container needed. Safe to run anywhere the repo is checked out.

Usage (from repo root):
    python tests/test_loop_v2.py
Must print ALL TESTS PASS.
"""
import asyncio, ast, json, os, shutil, sys, tempfile, inspect, time

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

    # ---- the observation keyhole and the loop warning (2026-08-25) ----------
    # The old B4 test stood exactly here and asserted the MECHANISM -- that the
    # source contained the phrase "reworded form". That phrase WAS the trap: the
    # detector saw only exact strings, the ban covered every rewording, and the
    # creature spent three cycles hunting a legal way to read a file it was
    # upgrading. A 14-day census: 127 streaks, 102 with silently-capped output,
    # 44 where "the same result" was false, 23 distinct commands collapsed into
    # false repeats by the 200-char journal cap. Contract tests replace it.

    # Truncation announces itself, with the exact loss named.
    _cap310 = loop._capped("x" * 310, 300)
    # Contract, not format: the marker must name the exact loss and carry the
    # ellipsis. It gained a "; window N" suffix on 2026-08-27, and asserting the
    # literal old tail here is what went red -- the mechanism test this file
    # warns about, in this file.
    check("keyhole: a cut names exactly what was lost",
          loop._TRUNC_MARK_RE.findall(_cap310) == ["10"]
          and chr(8230) in _cap310)
    check("keyhole: text within the cap is untouched",
          loop._capped("short", 300) == "short"
          and loop._capped("", 300) == "")

    # Nested truncation. Found 2026-08-26 by gs-bug-daily: the writer caps exec
    # stdout at 300 and appends a marker, then the render caps the whole journal
    # record at 300 again -- and the second cut replaced the first cut's honest
    # number with its own. Against the live 00:35 record, 3,319 characters were
    # withheld and the creature was shown "+40 chars cut". It then asked for
    # 100-line ranges 97 times in 15.6 h. A marker that under-reports by two
    # orders of magnitude reads as reassurance, which is worse than no marker at
    # all; these tests are the contract that it cannot.
    _big = "#!/usr/bin/env python3" + chr(10) + ("X" * 3583)
    _rec = ("exit=0 stdout=%s stderr=%s"
            % (loop._capped(_big, loop.EXEC_STDOUT_JOURNAL_CHARS),
               loop._capped("", loop.EXEC_STDERR_JOURNAL_CHARS)))
    _seen = loop._capped(_rec, loop.JOURNAL_RENDER_CHARS)
    _n = int(loop._TRUNC_MARK_RE.findall(_seen)[-1])
    check("nested truncation: the marker reports thousands, not tens", _n > 3000)
    check("nested truncation: the number is within 1% of what is withheld",
          abs(_n - (len(_big) - 286)) <= max(40, len(_big) // 100))
    check("nested truncation: a second cut never shrinks the reported loss",
          _n >= int(loop._TRUNC_MARK_RE.findall(_rec)[-1]))
    check("nested truncation: exactly one marker survives, at the end",
          len(loop._TRUNC_MARK_RE.findall(_seen)) == 1
          and loop._TRUNC_MARK_RE.search(_seen).end() == len(_seen))
    # A marker sliced in half by the outer cut is noise and must not survive.
    # Swept across every cap that can land inside it, because the one that
    # breaks is the one nobody would have picked by hand.
    _straddle = loop._capped("y" * 500, 300)
    _half = [_c for _c in range(290, 340)
             if any(_s in loop._TRUNC_MARK_RE.sub("", loop._capped(_straddle, _c))
                    for _s in (chr(8230), "[+", "chars cut"))]
    check("nested truncation: no half-marker survives at any cap", _half == [])

    # The marker names the WINDOW as well as the loss. Added 2026-08-27 after
    # the 08-26 window measured what invariant 1 alone achieved: the creature
    # was told the loss 724 times and the ceiling 6 times, and responded by
    # abandoning ranged reads instead of sizing them -- sed ranges 143 -> 5 (all
    # five still asking for 100 lines) while raw cat rose 349 -> 387 and capped
    # results rose 67.4% -> 73.8%. A measurement its reader cannot interpret is
    # not yet a measurement: the loss alone never says how much to ask for next.
    _wmark = loop._capped("q" * 5000, 300)
    check("marker names the window it applied", "window 300" in _wmark)
    check("marker still names the loss, and first",
          _wmark.index("chars cut") < _wmark.index("window"))
    for _cap in (200, 300, 1000):
        check("marker's window equals the cap actually applied (%d)" % _cap,
              ("window %d]" % _cap) in loop._capped("q" * 9000, _cap))
    check("the loss capture group is unaffected by the window suffix",
          loop._TRUNC_MARK_RE.findall(_wmark) == ["4700"])
    check("window naming survives nesting, reporting the OUTER window",
          loop._capped(loop._capped("q" * 9000, 1000), 300)
          .endswith("window 300]"))
    check("a nested marker still sums the total loss, not the outer cut alone",
          int(loop._TRUNC_MARK_RE.findall(
              loop._capped(loop._capped("q" * 9000, 1000), 300))[-1]) >= 8600)
    check("nested truncation: three cuts still sum to the original loss",
          int(loop._TRUNC_MARK_RE.findall(
              loop._capped(loop._capped(loop._capped("z" * 9000, 3000),
                                        1000), 400))[-1]) >= 8500)

    # oracle_rest: the effort funnel's early-rejection stage. Added 2026-08-26
    # after that stage read exactly zero on three consecutive runs -- the stub
    # janitor's "aged-out 0" disease inside one of our own instruments. The
    # decision existed only on stdout, so it landed in journald while the metric
    # reads journal.jsonl. Two contracts, and they pull in opposite directions:
    # the funnel must be able to COUNT it, and the creature must never SEE it.
    check("oracle_rest never reaches the creature's wake context",
          "oracle_rest" not in loop.MEANINGFUL_KINDS)
    # The suite preamble stubs journal.append to a no-op, so write the FILE
    # directly -- the same pattern the loop-warning and throughput tests use.
    from executive import journal as _jr
    _orpath = _jr._host_journal_path(TMP)
    with open(_orpath, "a", encoding="utf-8") as _orf:
        _orf.write(json.dumps({"ts": time.time(), "kind": "oracle_rest",
                               "content": "category=archive already built; "
                                          "only a rebuild fallback -- rested"},
                              ensure_ascii=False) + chr(10))
    _back = _jr.last_of_kind(TMP, "oracle_rest")
    check("oracle_rest is readable back from the journal the funnel reads",
          _back is not None and "rested" in _back["content"])
    _rendered = "".join(_e["content"] for _e in _jr.recent(TMP, 60)
                        if _e["kind"] in loop.MEANINGFUL_KINDS)
    check("oracle_rest text is absent from everything rendered to the creature",
          "category=archive already built" not in _rendered)
    check("keyhole: writer and render share the one helper and constants",
          "_capped(cmd, EXEC_CMD_JOURNAL_CHARS)" in inspect.getsource(loop.run_cycle)
          and "_capped(stdout, EXEC_STDOUT_JOURNAL_CHARS)" in inspect.getsource(loop.run_cycle)
          and "JOURNAL_RENDER_CHARS" in inspect.getsource(loop._build_context))

    # The warning, on checked facts. Built against the TMP journal.
    # The suite preamble stubs journal.append to a no-op, so these write the
    # journal FILE directly -- the same pattern the throughput tests use.
    from executive.journal import _host_journal_path as _jpath_of
    _jpath = _jpath_of(TMP)
    mem.store(TMP, "current-phase", "code")
    check("loop-warning tests write to the TMP journal, not the real one",
          loop.VOLUME_MOUNT == TMP and _jpath.startswith(TMP))

    def _japp(kind, content):
        with open(_jpath, "a", encoding="utf-8") as _jf:
            _jf.write(json.dumps({"ts": time.time(), "kind": kind,
                                  "content": content}, ensure_ascii=False) + chr(10))

    def _pad(tag, k=10):
        for i in range(k):
            _japp("exec_start", "Block 1: echo pad-%s-%d" % (tag, i))
            _japp("exec_end", "exit=0 stdout=pad-%s-%d stderr=" % (tag, i))

    def _repeat(cmd, out, k=4):
        for _ in range(k):
            _japp("exec_start", "Block 1: " + cmd)
            _japp("exec_end", out)

    # Case 1: identical AND complete -> act, and no ban on different extraction.
    _pad("c1")
    _repeat("step-planner-tracker list", "exit=0 stdout=goal-1 pending stderr=")
    _w1 = loop._build_loop_warning()
    check("complete+identical: says the result is complete and says act",
          "same complete result" in _w1 and "act on what it already told you" in _w1)
    check("complete+identical: explicitly allows extracting different information",
          "DIFFERENT information is fine" in _w1)

    # Case 2: output was CAPPED -> the truth is starvation, and the ramp is
    # extraction or in-block transformation. Legacy shape: exactly-at-cap stdout
    # with no marker, as every pre-fix journal record has it.
    _pad("c2")
    _repeat("cat /mind/tools/own/big_tool", "exit=0 stdout=" + "y" * 300 + " stderr=")
    _w2 = loop._build_loop_warning()
    check("truncated: names the window and that repetition cannot widen it",
          str(loop.JOURNAL_RENDER_CHARS) in _w2
          and "repetition cannot widen" in _w2)
    check("truncated: gives the in-block ramp and the extraction ramp",
          "inside one bash block" in _w2 and "sed -n" in _w2)
    check("truncated: never claims it already has the information",
          "already have this information" not in _w2)

    # Marker shape (new writer) is recognised too.
    _pad("c2b")
    _repeat("cat /mind/tools/own/big2",
            "exit=0 stdout=" + "z" * 60 + chr(8230) + "[+3121 chars cut] stderr=")
    check("truncated: the explicit marker is recognised as truncation",
          "repetition cannot widen" in loop._build_loop_warning())

    # Case 3: results DIFFERED -> the old "same result" claim must not appear.
    _pad("c3")
    for i in range(4):
        _japp("exec_start", "Block 1: date +%s")
        _japp("exec_end", "exit=0 stdout=17240%d stderr=" % i)
    _w3 = loop._build_loop_warning()
    check("differing: says the results differ instead of asserting sameness",
          "DIFFERENT on different runs" in _w3)

    # Case 4: identity destroyed by the cmd cap -> not counted at all. Four
    # IDENTICAL capped commands (the tool-edit heredoc class) stay silent.
    _pad("c4")
    _capped_cmd = ("tool-edit big_tool <<'EOF' #!/usr/bin/env python3 # tool: "
                   + "b" * 160)[:200]
    _repeat(_capped_cmd, "exit=0 stdout=Rewrote big_tool stderr=")
    check("identity destroyed: a capped command is never counted as a repeat",
          loop._build_loop_warning() == "")

    # Case 5: below threshold -> silence.
    _pad("c5")
    _repeat("echo once", "exit=0 stdout=once stderr=", k=3)
    check("below threshold: three repeats say nothing",
          loop._build_loop_warning() == "")

    # ---- tool-edit write-time startability feedback (2026-08-26) ------------
    # The 2026-08-19 named trigger fired: the broken-tool count sat at 32 for
    # four days with engagement but no repair, so the fact now arrives at
    # authorship. tool-edit runs INSIDE the container where volume/tools.py does
    # not exist, so it carries a VERBATIM mirror of the four canonical functions
    # -- and this test is the only thing standing between mirror and drift.
    # Subprocess only: importing would write __pycache__ into framework-tools,
    # which once emptied the creature's toolset for four days.
    NL = chr(10)
    import re as _re_te, subprocess as _sp_te
    _te_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "framework-tools", "tool-edit")
    with open(_te_path, encoding="utf-8") as _tf:
        _te_src = _tf.read()
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "volume", "tools.py"),
            encoding="utf-8") as _cf:
        _canon_src = _cf.read()
    _mirror = _te_src.split("BEGIN startability mirror")[1]                      .split("END startability mirror")[0]
    _drift = []
    for _fn in ("looks_like_python", "tool_syntax_error", "_shell_syntax_ok",
                "tool_start_failure"):
        _m = _re_te.search(r"(?ms)^def " + _fn + r"\(.*?(?=^def |^class |\Z)",
                           _canon_src)
        if not (_m and _m.group(0).rstrip() in _mirror):
            _drift.append(_fn)
    check("tool-edit's startability mirror is verbatim-identical to the "
          "canonical (drift breaks this test)", _drift == [])

    _te_own = os.path.join(TMP, "te_own")
    os.makedirs(_te_own, exist_ok=True)
    with open(os.path.join(_te_own, "victim"), "w", encoding="utf-8") as _vf:
        _vf.write("#!/usr/bin/env python3" + NL + "print(1)" + NL)
    _te_env = dict(os.environ, SPINE_OWN_DIR=_te_own)
    _BSq = chr(92) + chr(34)
    _broken_body = ("#!/usr/bin/env python3" + NL + "p = f" + _BSq + _BSq + _BSq
                    + "hi" + NL + "import sys" + NL + "print(sys.argv)" + NL)

    _r = _sp_te.run([sys.executable, _te_path, "victim"], input=_broken_body,
                    capture_output=True, text=True, env=_te_env, timeout=60)
    check("tool-edit: a broken file is SAVED (warning, never a refusal)",
          _r.returncode == 0 and "Rewrote" in _r.stdout
          and open(os.path.join(_te_own, "victim"),
                   encoding="utf-8").read() == _broken_body)
    check("tool-edit: and stderr says it cannot START, with the line",
          "cannot START" in _r.stderr and "line 2" in _r.stderr
          and "must be able to start" in _r.stderr)

    _healthy = ("#!/usr/bin/env python3" + NL + "import sys" + NL
                + "print(sys.argv)" + NL)
    _r2 = _sp_te.run([sys.executable, _te_path, "victim"], input=_healthy,
                     capture_output=True, text=True, env=_te_env, timeout=60)
    check("tool-edit: a healthy file draws no warning",
          _r2.returncode == 0 and _r2.stderr.strip() == "")

    _r3 = _sp_te.run([sys.executable, _te_path, "victim"], input="",
                     capture_output=True, text=True, env=_te_env, timeout=60)
    check("tool-edit: the empty-stdin refusal still stands (regression)",
          _r3.returncode == 1 and "Refusing to write empty content" in _r3.stdout)

    # The contract that replaces old B4: the ban is GONE from every message.
    for _w in (_w1, _w2, _w3):
        pass
    check("no message bans rewording, in any case",
          all("reworded" not in w for w in (_w1, _w2, _w3)))

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

    # ---- the greenlight must require that the tool can START (2026-08-19) ----
    # Ten tools sat in the library unable to run one line, two of them still being
    # invoked 30 and 12 times a week, and nothing in the done-gate had ever asked
    # whether a tool could start. The gate was also watching the wrong door:
    # _hollow_tools_touched matches only tool-new, and all ten were written with
    # tool-edit -- 185 edits against 90 creates that week.
    _BS = chr(92)
    _NL = chr(10)
    # REAL fault shapes from the live library, not authored to match the detector.
    with open(os.path.join(owndir, "esc_quotes"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3" + _NL
                + "p = f" + _BS + chr(34) + _BS + chr(34) + _BS + chr(34) + "hi" + _NL
                + "import sys" + _NL + "print(sys.argv)" + _NL
                + "total = sum(range(4))" + _NL)
    with open(os.path.join(owndir, "hdr_no_hash"), "w", encoding="utf-8") as f:
        f.write("tool: hdr_no_hash" + _NL + "call: hdr_no_hash" + _NL
                + "#!/usr/bin/env python3" + _NL + "import sys" + _NL
                + "print(sys.argv)" + _NL + "total = 2 + 2" + _NL)
    with open(os.path.join(owndir, "u2011"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3" + _NL + "x = keyword" + chr(8209)
                + "archive" + _NL + "import sys" + _NL + "print(sys.argv)" + _NL)
    # and the purest case: an error message written into the file AS the tool
    with open(os.path.join(owndir, "err_as_tool"), "w", encoding="utf-8") as f:
        # Faithful to the live file: the captured error is truncated mid-JSON, so
        # it leaves an unbalanced quote. A single line of prose CAN be valid shell,
        # so this class is caught only when it leaves something unterminated --
        # stated here rather than overclaimed.
        f.write('Error: LLM call failed: ask: HTTP 429 from provider: '
                '{"error":{"message":"Rate limit rea' + _NL)

    # A real tool IS executable -- tool-new/tool-edit set the bit, and only 2 of
    # 485 live tools lack it. A fixture written with open() has no +x, so on POSIX
    # (where the bit is real) the healthy fixtures read as unstartable and this
    # block went red on the laptop while passing on the PC. Make the fixtures
    # resemble the thing they stand for.
    if os.name == "posix":
        import stat as _stat_g
        for _f in ("esc_quotes", "hdr_no_hash", "u2011", "err_as_tool",
                   "real_tool", "hollow_tool"):
            _fp = os.path.join(owndir, _f)
            if os.path.exists(_fp):
                os.chmod(_fp, os.stat(_fp).st_mode | _stat_g.S_IXUSR)

    check("both doors are watched: tool-edit is no longer invisible",
          loop._tools_touched([("tool-edit esc_quotes", 0)]) == {"esc_quotes"}
          and loop._tools_touched([("tool-new a", 0), ("tool-edit b", 0)])
          == {"a", "b"})

    _uns = loop._unstartable_tools_touched(
        [("tool-edit esc_quotes", 0), ("tool-edit hdr_no_hash", 0),
         ("tool-edit u2011", 0), ("tool-edit err_as_tool", 0),
         ("tool-edit real_tool", 0)])
    check("escaped triple quotes are caught", "esc_quotes" in _uns)
    check("a header written without the # is caught", "hdr_no_hash" in _uns)
    check("a U+2011 typographic hyphen is caught", "u2011" in _uns)
    check("an error message written in as the tool is caught",
          "err_as_tool" in _uns)
    check("a healthy tool written the same cycle is NOT flagged",
          "real_tool" not in _uns)

    # A working shell tool must never be condemned by Python's grammar, and a
    # shell script without a shebang still runs under bash -- guessing from the
    # extension would have condemned 26 live files, some of them working.
    with open(os.path.join(owndir, "good_sh"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash" + _NL + "if [ -f x ]; then echo hi; fi" + _NL)
    with open(os.path.join(owndir, "sh_no_shebang"), "w", encoding="utf-8") as f:
        f.write("ls -la" + _NL + "echo done" + _NL)
    if os.name == "posix":
        for _f in ("good_sh", "sh_no_shebang"):
            _fp = os.path.join(owndir, _f)
            os.chmod(_fp, os.stat(_fp).st_mode | _stat_g.S_IXUSR)
    _sh_uns = loop._unstartable_tools_touched(
        [("tool-edit good_sh", 0), ("tool-edit sh_no_shebang", 0)])
    check("a working shell tool is not condemned by Python's grammar",
          _sh_uns == {})

    # The gate itself, through the real entry point.
    _m.store(TMP, "current-project", "esc_quotes: a summariser")
    _m.store(TMP, "current-phase", "done")
    _g3 = loop._enforce_done_gate([("tool-edit esc_quotes", 0),
                                   ('remember current-phase "done"', 0)])
    check("the done-gate refuses a greenlight on a tool that cannot start",
          _g3 is False)
    # Assert the CONTRACT the creature actually receives -- the reason written to
    # the done-block -- not which memory key holds the phase.
    with open(loop.DONE_BLOCK_PATH, encoding="utf-8") as _bf:
        _breason = _bf.read()
    check("the block tells it plainly that the tool cannot start",
          "cannot start" in _breason and "esc_quotes" in _breason)

    # Remove the broken fixtures BEFORE the next assertion: a one-line broken file
    # also counts as hollow, and left in place they pushed the library backlog past
    # its tolerance so a LATER branch blocked everything -- which would have made
    # the next check pass or fail for entirely the wrong reason.
    for _n in ("esc_quotes", "hdr_no_hash", "u2011", "err_as_tool", "good_sh",
               "sh_no_shebang"):
        try:
            os.remove(os.path.join(owndir, _n))
        except Exception:
            pass

    # It must NOT be the reason a genuine completion is refused. Asserted against
    # THIS branch rather than against the gate's overall verdict: by this point the
    # suite has deliberately armed the gate-choice file and left a hollow tool
    # behind, so a composite "was it allowed through" would pass or fail on five
    # other branches' state and tell us nothing about this one.
    _m.store(TMP, "current-project", "real_tool: a json fetcher")
    _m.store(TMP, "current-phase", "done")
    try:
        os.remove(loop.DONE_BLOCK_PATH)
    except OSError:
        pass
    loop._enforce_done_gate([("tool-edit real_tool", 0),
                             ('remember current-phase "done"', 0)])
    try:
        with open(loop.DONE_BLOCK_PATH, encoding="utf-8") as _bf2:
            _r2 = _bf2.read()
    except OSError:
        _r2 = ""
    check("a healthy tool is never refused for being unstartable",
          "cannot start" not in _r2)
    check("and the scope is this cycle, so the library's broken tools cannot "
          "wedge the gate",
          loop._unstartable_tools_touched([("tool-edit real_tool", 0)]) == {})

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
    from volume import tools as _vtools_g
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
    # This asserted == "hard" until 2026-08-19 and was testing the very default
    # that killed 651 cycles: "hard" raises and aborts the whole chain, so an error
    # nobody had enumerated yet took down cognition that four open rungs could have
    # served. Assert the CONTRACT -- an unrecognised error must never be the reason
    # a ladder with open rungs stops.
    check("classify: an unrecognised error never hard-raises the chain",
          classify_error("something exploded weirdly") == "unknown")
    # REAL string, from the creature's journal at 17:26 on 2026-08-19, not authored.
    # Mistral answers a spent MONTHLY allowance with 402 and the word subscription:
    # no "quota", no "billing", no "exceeded", no 429 anywhere in it.
    _m402 = ('HTTP 402: {"detail":"Check your subscription on '
             'https://admin.mistral.ai/subscription"}')
    check("classify: a 402 spent-allowance is quota, so the rung gets walled",
          classify_error(_m402) == "quota")
    # Found by gs-bug-daily on 2026-08-25 via the `unknown` path: google_gemma
    # returned HTTP 499 twice and nothing recognised it. 499 is "client closed
    # request" -- transport-level and transient, the same family as a timeout, so
    # it routes onward and must never wall the account. REAL string from the
    # journal, not authored.
    _NL499 = chr(10)
    _g499 = ('HTTP 499: [{' + _NL499 + '  "error": {' + _NL499 + '    "code": 499,' + _NL499
             + '    "message": "The request was cancelled."' + _NL499 + '  }' + _NL499 + '}]')
    check("classify: a 499 cancelled request is flaky, not unknown",
          classify_error(_g499) == "flaky")
    check("classify: a 499 never walls the account",
          classify_error(_g499) not in ("quota", "too_large"))

    # Cloudflare edge codes. Real journal string, 2026-08-26 00:08: the whole
    # chain failed and the raise carried "mistral: HTTP 520: error code: 520" --
    # the `unknown` path doing its job again, and the second time in two days
    # that it handed us a shape to classify. 520-527 are edge/origin failures,
    # transient, and say nothing about the account.
    _cf520 = "HTTP 520: error code: 520"
    check("classify: a Cloudflare 520 is retryable, not unknown",
          classify_error(_cf520) == "retryable")
    for _code in ("521", "522", "523", "524", "525", "526", "527"):
        check("classify: Cloudflare " + _code + " is retryable",
              classify_error("HTTP " + _code + ": error code: " + _code)
              == "retryable")
    check("classify: no Cloudflare edge code ever walls the account",
          all(classify_error("HTTP %s: error code: %s" % (c, c))
              not in ("quota", "too_large", "gone")
              for c in ("520", "521", "522", "523", "524", "525", "526", "527")))

    # Cloudflare Workers AI plan restriction. Real body, measured 2026-08-26:
    # the model-search API lists kimi-k2.6, glm-5.2, glm-5.3-flash and
    # deepseek-v4-pro, and the Workers FREE plan refuses all four. The id has
    # left OUR shelf while the account is perfectly fine, which is exactly what
    # `gone` means -- and a single-model rung must be walled WITH a log line,
    # per the 2026-08-17 scar where groq retired in total silence.
    _cf5035 = ('{"errors":[{"message":"AiError: Model @cf/moonshotai/kimi-k2.6 '
               'is not available on the Workers Free plan: Model '
               '@cf/moonshotai/kimi-k2.6 is not available on the Workers Free '
               'plan. Upgrade to access this model: '
               'https://dash.cloudflare.com/?to=/:account/workers/plans '
               '(155b925f-e633-4cd0-b73b-29736dbafe25)","code":5035}],'
               '"success":false,"result":{},"messages":[]}')
    check("classify: a Cloudflare plan restriction is gone, not unknown",
          classify_error(_cf5035) == "gone")
    check("classify: a plan restriction never walls the ACCOUNT as quota",
          classify_error(_cf5035) not in ("quota", "too_large"))
    check("classify: payment/insufficient wording is also quota",
          classify_error("HTTP 402 payment required") == "quota"
          and classify_error("insufficient balance for this request") == "quota")
    # These two asserted `== "quota"` until 2026-08-10 and went red the moment the
    # mechanism improved, which is the scar in section 5: assert the CONTRACT. The
    # contract a dead model id must satisfy is "never hard-raise, and do not spend
    # the account" -- it is now its own class so a rung with other models falls to
    # the next one instead of walling a live account over one stale id.
    _dead404 = classify_error('HTTP 404: {"error":{"message":"No endpoints found '
                              'for qwen/qwen3-coder:free"}}')
    _deadname = classify_error("model_not_found: that model id does not exist")
    check("classify: a dead model id never hard-raises",
          _dead404 != "hard" and _deadname != "hard")
    check("classify: a dead model id is not charged to the account budget",
          _dead404 == "gone" and _deadname == "gone")
    check("classify: a real daily 429 still spends the account",
          classify_error('HTTP 429: {"error":{"message":"Rate limit exceeded: '
                         'free-models-per-day"}}') == "quota")

    # ---- multi-model rung: one account, models tried in order (2026-08-10) ----
    # record_success/record_exhaustion call save_state(), which writes the WHOLE
    # dict it is handed to keychain/quota_state.json -- a module-level constant with
    # no injection point. The first version of this test passed a fresh {} and
    # flattened every provider's real last_success_at on the live laptop. Same
    # shape as the section 5 scar about _build_tool_catalogue() writing rotation
    # state, which I had read days earlier. Repoint the constant, always.
    from keychain import keychain as _kcmod, provider as _provmod, quota_state as _qsmod
    _real_state_file = _qsmod.STATE_FILE
    _qsmod.STATE_FILE = os.path.join(TMP, "quota_state_probe.json")

    def _rung(models):
        k = _kcmod.Keychain.__new__(_kcmod.Keychain)   # skip config/disk load
        k.providers = [{"key": "pool", "endpoint": "e", "api_key": "k",
                        "model_id": models}]
        k.state, k.last_used, k.last_model = {}, None, None
        k.last_finish_reason, k.last_truncated = "", False
        return k

    _seen = []
    _real_call = _provmod.call

    async def _fake(cfg, messages, max_tokens=2048, model=None):
        _seen.append(model)
        if model.startswith("gone/"):
            return {"error": 'HTTP 404: {"error":{"message":"No endpoints found"}}',
                    "text": "", "finish_reason": "", "truncated": False}
        if model.startswith("dry/"):
            return {"error": 'HTTP 429: {"error":{"message":"Rate limit exceeded: '
                             'free-models-per-day"}}',
                    "text": "", "finish_reason": "", "truncated": False}
        return {"error": None, "text": "served", "finish_reason": "stop",
                "truncated": False, "tokens_used": 3}
    _provmod.call = _fake
    try:
        _seen.clear()
        k1 = _rung(["gone/first:free", "good/second:free"])
        _out = await k1.complete("hi")
        check("multi-model rung: a purged first model falls to the next",
              _out == "served" and _seen == ["gone/first:free", "good/second:free"])
        check("multi-model rung: records WHICH model served, not just the account",
              k1.last_model == "good/second:free")
        check("multi-model rung: a fallen-through rung is not walled",
              "exhausted_at" not in k1.state.get("pool", {}))

        _seen.clear()
        k2 = _rung(["dry/first:free", "good/second:free"])
        try:
            await k2.complete("hi")
            _raised = False
        except RuntimeError:
            _raised = True
        check("multi-model rung: a daily 429 ends the rung, it does not try "
              "sibling models on the same spent account",
              _seen == ["dry/first:free"] and _raised)
        check("multi-model rung: a 429 walls the account",
              "exhausted_at" in k2.state.get("pool", {}))

        # A retirement must be AUDIBLE even on a single-model rung. Until
        # 2026-08-17 the gone line printed only when a sibling model existed, so
        # Groq withdrawing llama-3.3-70b-versatile walled the `groq` rung in total
        # silence -- correct behaviour, no cause recorded anywhere.
        import contextlib as _ctxg, io as _iog
        _seen.clear()
        _cap = _iog.StringIO()
        k1b = _rung(["gone/only:free"])
        with _ctxg.redirect_stdout(_cap):
            try:
                await k1b.complete("hi")
            except RuntimeError:
                pass
        _log = _cap.getvalue()
        check("multi-model rung: a single-model retirement is logged, not silent",
              "GONE" in _log and "gone/only:free" in _log)
        check("multi-model rung: the log says the rung was walled, not that it fell through",
              "walling it" in _log)

        # ---- a ladder must not die on an error it cannot name (2026-08-19) ----
        # The fault this replaces: mistral returned 402, classify_error had no
        # branch for it, the default "hard" raised, and the cycle was lost while
        # google_gemma and gemini_flash sat open. 651 times in one day. And because
        # it raised, record_exhaustion never ran, so the rung was never walled and
        # was retried every single cycle.
        def _ladder(*keys):
            k = _kcmod.Keychain.__new__(_kcmod.Keychain)
            k.providers = [{"key": n, "endpoint": "e", "api_key": "k",
                            "model_id": "m"} for n in keys]
            k.state, k.last_used, k.last_model = {}, None, None
            k.last_finish_reason, k.last_truncated = "", False
            return k

        _hit = []

        async def _byrung(cfg, messages, max_tokens=2048, model=None):
            _hit.append(cfg["key"])
            if cfg["key"] == "weird":
                return {"error": "HTTP 418 the server is a teapot",
                        "text": "", "finish_reason": "", "truncated": False}
            if cfg["key"] == "spent":
                return {"error": _m402, "text": "", "finish_reason": "",
                        "truncated": False}
            return {"error": None, "text": "served", "finish_reason": "stop",
                    "truncated": False, "tokens_used": 3}
        _provmod.call = _byrung
        try:
            _hit.clear()
            _kcmod._REPORTED_UNKNOWN.clear()
            kA = _ladder("weird", "healthy")
            _capA = _iog.StringIO()
            with _ctxg.redirect_stdout(_capA):
                _outA = await kA.complete("hi")
            check("an unrecognised error routes to the next rung instead of "
                  "killing the cycle",
                  _outA == "served" and _hit == ["weird", "healthy"])
            check("the rung that failed unrecognisably is NOT walled",
                  "exhausted_at" not in kA.state.get("weird", {}))
            check("the unrecognised error is announced, with its text, so it can "
                  "be classified",
                  "does not recognise" in _capA.getvalue()
                  and "teapot" in _capA.getvalue())

            # Announced once per distinct error, not once per cycle -- a line
            # repeated every cycle is a nag that gets skipped.
            _capB = _iog.StringIO()
            with _ctxg.redirect_stdout(_capB):
                await _ladder("weird", "healthy").complete("hi")
            check("it is announced once per process, not once per cycle",
                  "does not recognise" not in _capB.getvalue())

            # The real mistral case end to end: walled, and the ladder serves on.
            _hit.clear()
            kC = _ladder("spent", "healthy")
            _outC = await kC.complete("hi")
            check("a spent monthly allowance walls its rung and the ladder still "
                  "serves",
                  _outC == "served" and _hit == ["spent", "healthy"]
                  and "exhausted_at" in kC.state.get("spent", {}))

            # If everything fails and one failure was unnameable, the reason must
            # survive: "all providers exhausted" would discard the only copy.
            _kcmod._REPORTED_UNKNOWN.clear()
            _msg = ""
            try:
                with _ctxg.redirect_stdout(_iog.StringIO()):
                    await _ladder("weird").complete("hi")
            except RuntimeError as _re:
                _msg = str(_re)
            check("when every rung fails, the unrecognised reason is carried in "
                  "the raise",
                  "teapot" in _msg and "exhausted" not in _msg.lower())
        finally:
            _provmod.call = _fake

        _seen.clear()
        k3 = _rung(["gone/a:free", "gone/b:free"])
        try:
            await k3.complete("hi")
        except RuntimeError:
            pass
        check("multi-model rung: every model gone walls the rung (2026-07-19 "
              "purge behaviour preserved)",
              "exhausted_at" in k3.state.get("pool", {}))
        check("multi-model rung: the probe wrote to TMP, never to the live "
              "quota_state.json",
              os.path.isfile(_qsmod.STATE_FILE)
              and TMP in _qsmod.STATE_FILE
              and "quota_state_probe" in _qsmod.STATE_FILE)
    finally:
        _provmod.call = _real_call
        _qsmod.STATE_FILE = _real_state_file

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
    from executive import architect as _arch_mod
    # ---- architect WANTED nudge (2026-08-06) ----
    _ap = _arch_mod.build_prompt(
        [{"title": "t", "brief": "b"}],
        {"total": 1, "zero_use_count": 0, "lineage_count": 0,
         "top_used": [], "born_24h": []})
    check("architect: the WANTED contract demands concrete capabilities",
          "CONCRETELY" in _ap and "on what INPUT" in _ap
          and "is a mood" in _ap)
    check("architect: the nudge shows both a good and a bad example",
          "Cross-source timeline synthesis" in _ap
          and "Robust automated plan regeneration" in _ap)

    # ---- census normalisation (2026-08-06, my own regression) ----
    from executive import architect as _arch
    _cd = os.path.join(TMP, "census_probe", "tools", "own")
    os.makedirs(_cd, exist_ok=True)
    for _n in ("lonely_tool.py", "bare_tool"):
        open(os.path.join(_cd, _n), "w").write("print(1)\n")
    _J2 = __import__("json")
    _J2.dump({"lonely_tool": 12, "bare_tool": 5},
             open(os.path.join(TMP, "census_probe", "tool_usage.json"), "w"))
    _ev = _arch.gather_evidence(_cd, os.path.join(TMP, "census_probe", "journal.jsonl"))
    check("census: a used `foo.py` is not reported as never-used (stem mismatch)",
          _ev["zero_use_count"] == 0)
    check("census: and its usage reaches top_used",
          dict(_ev["top_used"]).get("lonely_tool") == 12)

    # ---- chat reply extraction (2026-08-07): thinking leaked to Tue ----
    from executive import chat as _chatx
    _leak = ("<thought>I also need to respond to Tue as requested by the system "
             "prompt (the `<reply>` tag). Plan: 1. Reply. 2. Explore."
             "</thought><reply>Thanks for the fix.</reply>")
    check("chat: a MENTION of the tag inside thinking is not the opening tag",
          _chatx.extract_text_reply(_leak) == "Thanks for the fix.")
    check("chat: the LAST reply pair wins, as with the retro and the architect",
          _chatx.extract_text_reply(
              "<reply>draft</reply> reconsidering <reply>final</reply>") == "final")
    check("chat: <think> blocks are dropped before scanning",
          _chatx.extract_text_reply(
              "<think>musing about <reply> tags</think><reply>answer</reply>")
          == "answer")
    check("chat: an unclosed reply still yields nothing (caller re-queues)",
          _chatx.extract_text_reply("<thought>x</thought><reply>cut off") == "")
    check("chat: a plain tagged reply is unaffected",
          _chatx.extract_text_reply("<reply>hello</reply>") == "hello")

    # ---- tool wiring sensor (2026-08-06): do its tools agree where data lives? ----
    _wown = os.path.join(TMP, "wiring", "tools", "own")
    os.makedirs(_wown, exist_ok=True)
    open(os.path.join(_wown, "writer_tool"), "w").write(
        'out = "/mind/thearchive.jsonl"\n')
    open(os.path.join(_wown, "reader_tool"), "w").write(
        'src = "/mind/sub/thearchive.jsonl"\n')
    open(os.path.join(_wown, "agreeing_tool"), "w").write(
        'p = "/mind/thearchive.jsonl"\n')
    _H.MIND = os.path.join(TMP, "wiring")
    _w = _H.check_tool_wiring()
    check("wiring: two tools naming the same file at different paths is flagged",
          _w.startswith("WIRING:!!") and "thearchivejsonl" in _w)
    check("wiring: tools that AGREE on a path raise nothing by themselves",
          _w.count("(2 paths)") == 1)
    open(os.path.join(_wown, "solo_tool"), "w").write('p = "/mind/only_one.json"\n')
    _w2 = _H.check_tool_wiring()
    check("wiring: a path only one tool uses is not a clash",
          "onlyonejson" not in _w2)

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
          and _chat.peek_unread(TMP)[1] == "second message")
    # The lock FILE is POSIX-only BY DESIGN: chat.py degrades _locked to a no-op
    # when fcntl is missing, so that a Windows checkout can run this suite at all.
    # Asserting the sidecar unconditionally therefore made the entire gate red on
    # the PC peer -- a MECHANISM assertion failing exactly where the mechanism is
    # deliberately absent, which is the §5 scar, in the test written to close a
    # race. The contract above holds on both platforms; the lock is checked where
    # it can exist, i.e. on the live host.
    check("chat: the rewrite path takes the cross-process lock where fcntl exists",
          os.path.exists(os.path.join(TMP, _chat.CHAT_FILENAME + ".lock"))
          if _chat.fcntl is not None else True)

    # ---- P1-F12, the half no test ever covered: the OBSERVER's writer --------
    # Both writes above go through enqueue -- the executive's own locked door. So
    # this passed continuously while observer.py appended to the same file with a
    # bare open(CHAT, "a") and never imported fcntl at all (measured 2026-08-11:
    # `grep -c fcntl observer.py` -> 0). A test that can only reach the file
    # through the locked door cannot see an unlocked one, and the audit read its
    # green as proof the race was closed.
    # observer.py cannot be imported here (PyQt6 + DISPLAY), so read its source --
    # the same instrument as the gate-integrity and fcntl checks further down.
    # PARSED, not grepped: a guard naming one exact string ('open(CHAT, "a"') is
    # one reformat from silent, and `mode=` is a keyword as often as a positional.
    _obs_src = open(os.path.join(os.path.dirname(os.path.dirname(_suite_path)),
                                 "observer.py"), encoding="utf-8").read()
    _obs_ast = ast.parse(_obs_src)
    _obs_chat_writes = []
    for _n in ast.walk(_obs_ast):
        if not (isinstance(_n, ast.Call) and getattr(_n.func, "id", "") == "open"):
            continue
        _pos = dict(enumerate(_n.args))
        _kw = {k.arg: k.value for k in _n.keywords}
        _target = _kw.get("file", _pos.get(0))
        _mode_node = _kw.get("mode", _pos.get(1))
        _mode = _mode_node.value if isinstance(_mode_node, ast.Constant) else ""
        if getattr(_target, "id", "") == "CHAT" and set(str(_mode)) & set("aw+x"):
            _obs_chat_writes.append(_mode)
    check("P1-F12: the observer opens the chat file for READING only -- one "
          "writer for chat.jsonl, and it is the locked one in executive.chat",
          _obs_chat_writes == [])
    check("P1-F12: the observer's send path is executive.chat.enqueue",
          any(isinstance(_n, ast.ImportFrom) and _n.module == "executive.chat"
              and any(a.name == "enqueue" for a in _n.names)
              for _n in ast.walk(_obs_ast)))

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
    NL = chr(10)
    _spec = _ilu.spec_from_file_location("otc", "scripts/openrouter_tier_check.py")
    _otc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_otc)
    _lines = _otc.diff_report(["a:free", "b:free"], ["b:free", "c:free"],
                              {"a:free": "openrouter_coder"})
    check("tier diff: new model detected", any("c:free" in l and l.startswith("NEW") for l in _lines))
    check("tier diff: gone model detected", any("a:free" in l and l.startswith("GONE") for l in _lines))
    check("tier diff: vanished configured rung flagged loudly",
          any("VANISHED" in l and "openrouter_coder" in l for l in _lines))

    # ---- fabricated-feed sensor (2026-08-08: the guard that greenlit a mock) ----
    # The fixture below is NOT authored here: it is the creature's actual mock
    # output, copied from /mind/tools/own/wake_catchup_fetcher as it stood at
    # 17:14 on 2026-08-08. That distinction is the point -- a test that invents
    # its own fixture out of the string the detector hunts passes forever and
    # proves nothing (see the stub-janitor scar). The live sensor scored this
    # exact payload SENSOR:ok(2 fresh) because it looked only for "Mock News Item".
    from volume.tools import is_fabricated_feed as _isff
    _creature_mock = [
        {"url": "https://example.com/article1", "title": "Test Article 1",
         "content": "A new AI model was released. It can improve productivity."},
        {"url": "https://example.com/article2", "title": "Test Article 2",
         "content": "Security patch available for XYZ library. Apply it now."}]
    check("fabricated feed: the mock that fooled the live sensor is caught",
          _isff(_creature_mock))
    check("fabricated feed: a real-shaped feed is not flagged",
          not _isff([{"url": "https://news.ycombinator.com/item?id=44",
                      "title": "Show HN: something real", "content": "body"}]))
    check("fabricated feed: reserved host caught even with an innocent title",
          _isff([{"url": "http://localhost:8000/x", "title": "Quarterly report"}]))
    check("fabricated feed: legacy 'Mock News Item' title still caught",
          _isff([{"url": "https://feeds.acme-news.io/1", "title": "Mock News Item 3"}]))
    check("fabricated feed: empty/garbage input does not raise",
          _isff([]) is False and _isff(None) is False and _isff(["x", 7]) is False)

    # ---- feed shape: the guard that assumed a JSON array (2026-08-09) ----
    # Real fixture: the creature's SECOND mock, written over the real fetcher at
    # 13:37 on 9 Aug to get a duplicate item for testing dedup logic. It emits one
    # object per line, so json.loads(whole) raised and the live sensor degraded to
    # SENSOR:fail(JSONDecodeError) -- is_fabricated_feed() was never reached.
    from volume.tools import parse_feed_items as _pfi
    _mock2 = ('{"title":"Item A","url":"https://example.com/a","summary":"First"}\n'
              '{"title":"Item B","url":"https://example.com/b","summary":"Second"}\n'
              '{"title":"Item A Duplicate","url":"https://example.com/a","summary":"Duplicate"}\n')
    check("feed shape: one-object-per-line output is parsed, not rejected",
          len(_pfi(_mock2) or []) == 3)
    check("feed shape: and the fixture is then caught as fabricated",
          _isff(_pfi(_mock2)))
    check("feed shape: a JSON array still parses",
          len(_pfi('[{"title":"a"},{"title":"b"}]') or []) == 2)
    check("feed shape: empty output is empty, not unparseable",
          _pfi("   ") == [])
    check("feed shape: genuine garbage is unparseable, not silently empty",
          _pfi("<html>502 Bad Gateway</html>") is None)

    # ---- data warning re-speaks when damage doubles (measured 2026-08-09) ----
    _prev = {"files": {"keyword-archive.jsonl": 100}, "fabricated": 3}
    check("data warning: silence while the fault is unchanged",
          not loop._data_state_worsened(
              {"files": {"keyword-archive.jsonl": 100}, "fabricated": 3}, _prev))
    check("data warning: speaks again once the damage has doubled",
          loop._data_state_worsened(
              {"files": {"keyword-archive.jsonl": 216}, "fabricated": 3}, _prev))
    check("data warning: a newly broken store speaks immediately",
          loop._data_state_worsened(
              {"files": {"keyword-archive.jsonl": 100, "other.jsonl": 2},
               "fabricated": 3}, _prev))
    check("data warning: the older list-format state does not wedge it",
          loop._data_state_worsened({"files": {}, "fabricated": 0}, ["x", True]))

    # ---- stuck-tool warning (2026-08-11: 49 orphans, 16h, 1.5 cores) ----
    # Ages below are the real ones measured that day. The warning must NAME the
    # tools -- the creature has a shell and can kill them, but not if it is only
    # told a number. Nothing here kills anything: a framework that reaped silently
    # would hide the fault it exists to expose.
    _sp = [("deep_answer_synth", 57616), ("deep_answer_synth", 57215),
           ("gap_filled_plan_generator", 57616), ("gap_filled_plan_generator", 640)]
    _sw = loop._format_stuck_warning(_sp)
    check("stuck warning: counts the processes and names the tools",
          "4 processes" in _sw and "deep_answer_synth" in _sw
          and "gap_filled_plan_generator" in _sw)
    check("stuck warning: reports the OLDEST age per tool, in hours",
          "16.0h" in _sw)
    check("stuck warning: silent when nothing is stuck",
          loop._format_stuck_warning([]) == "")
    # The CONTRACT holds on every platform: a list, never an exception. The /proc
    # scan and SC_CLK_TCK behind it are POSIX-only, and asserting the mechanism
    # unconditionally aborted the whole PC suite at 249 PASS with an AttributeError
    # on 2026-08-11 -- not a failed check, an abort, so everything after it went
    # unrun. Third POSIX-only assertion to break the PC peer; see 51e1e81.
    check("stuck warning: the scan returns a list on every platform, never raises",
          isinstance(loop._stuck_tool_procs(min_age=10**9), list))
    if hasattr(os, "sysconf") and os.path.isdir("/proc"):
        check("stuck warning: a healthy tool under the threshold is not reported",
              loop._stuck_tool_procs(min_age=10**9) == [])
    else:
        print("SKIP stuck-tool /proc scan (POSIX only)")
    _prev = {"tools": {"deep_answer_synth": 2}}
    check("stuck warning: an unchanged situation does not repeat",
          not loop._stuck_state_worsened({"tools": {"deep_answer_synth": 2}}, _prev))
    check("stuck warning: a NEW stuck tool speaks",
          loop._stuck_state_worsened(
              {"tools": {"deep_answer_synth": 2, "other": 1}}, _prev))
    check("stuck warning: speaks again once the count doubles",
          loop._stuck_state_worsened({"tools": {"deep_answer_synth": 4}}, _prev))
    check("stuck warning: goes quiet after the creature kills them",
          loop._stuck_state_worsened({"tools": {}}, _prev)
          and loop._format_stuck_warning([]) == "")

    # ---- ask: the framework inference primitive (2026-08-14) ----
    # The creature held seven live provider keys while rebuilding echo simulators,
    # because the one worked example (llm_ask_helper) died in /tmp on 23 June.
    # `ask` lives in framework-tools so it is re-materialised every wake and can
    # never be lost the same way. Its contract is the anti-echo contract: stdout
    # carries an answer or nothing; every failure is stderr + nonzero exit.
    #
    # Loaded from a TMP COPY: never import (or py_compile) framework-tools in
    # place -- a planted __pycache__ there once emptied the toolset for four days.
    import contextlib as _ctx
    import importlib.machinery as _ilm
    import importlib.util as _ilu2
    import io as _io
    _ask_src = os.path.join("framework-tools", "ask")
    _ask_tmp = os.path.join(TMP, "ask_copy.py")
    shutil.copyfile(_ask_src, _ask_tmp)
    _spec = _ilu2.spec_from_loader("askmod", _ilm.SourceFileLoader("askmod", _ask_tmp))
    askmod = _ilu2.module_from_spec(_spec)
    _spec.loader.exec_module(askmod)
    askmod.STATE = os.path.join(TMP, "ask_quota_probe.json")
    check("ask: test budget file is repointed into TMP, never /mind",
          TMP in askmod.STATE)  # the quota_state lesson: assert the repoint

    # The answer path. Fixture shape is the OpenAI-compatible reply the
    # production parser in keychain/provider.py already consumes live.
    _ok = json.dumps({"choices": [{"message": {"content": " ALIVE \n"},
                                   "finish_reason": "stop"}]})
    check("ask: extracts exactly the answer text", askmod.extract_answer(_ok) == "ALIVE")
    _trunc = json.dumps({"choices": [{"message": {"content": "half an ans"},
                                      "finish_reason": "length"}]})
    try:
        askmod.extract_answer(_trunc); _raised = False
    except ValueError as e:
        _raised = "ceiling" in str(e)
    check("ask: a truncated reply is a FAILURE, never a silent partial", _raised)
    _empty = json.dumps({"choices": [{"message": {"content": "",
                                                  "reasoning": "mused a lot"},
                                      "finish_reason": "stop"}]})
    try:
        askmod.extract_answer(_empty); _raised = False
    except ValueError:
        _raised = True
    check("ask: a reasoning-only/empty reply is a failure, not an empty answer", _raised)

    # The budget. Attempts counted, UTC rollover, corrupt file = fresh day.
    check("ask: first spend of the day is 1 of cap",
          askmod.spend_budget(now=1000000000) == (1, askmod.DAILY_CAP))
    check("ask: attempts accumulate", askmod.spend_budget(now=1000000000)[0] == 2)
    check("ask: the day rolls over at 00:00 UTC and the counter resets",
          askmod.spend_budget(now=1000000000 + 86400)[0] == 1)
    with open(askmod.STATE, "w", encoding="utf-8") as _f:
        _f.write("{corrupt json")
    check("ask: a corrupt budget file starts a fresh day rather than crashing",
          askmod.spend_budget(now=1000000000)[0] == 1)

    # The anti-echo contract, end to end: every failure path leaves stdout EMPTY.
    def _run_main(argv, stdin_text="", env_key=None, env_name="GROQ_API_KEY"):
        out, err = _io.StringIO(), _io.StringIO()
        old_stdin = sys.stdin
        saved = {n: os.environ.pop(n, None) for n in askmod.ENV_KEYS}
        if env_key is not None:
            os.environ[env_name] = env_key
        sys.stdin = _io.StringIO(stdin_text)
        code = None
        try:
            with _ctx.redirect_stdout(out), _ctx.redirect_stderr(err):
                try:
                    askmod.main(argv)
                except SystemExit as e:
                    code = e.code
        finally:
            sys.stdin = old_stdin
            for n in askmod.ENV_KEYS:
                os.environ.pop(n, None)
            for n, v in saved.items():
                if v is not None:
                    os.environ[n] = v
        return code, out.getvalue(), err.getvalue()

    _c, _o, _e = _run_main(["ask"])
    check("ask: no prompt -> exit 2, stdout empty, usage on stderr",
          _c == 2 and _o == "" and "usage" in _e)
    _c, _o, _e = _run_main(["ask", "hello"])
    check("ask: no provider key -> exit 3, stdout empty, names the missing env vars",
          _c == 3 and _o == "" and "GROQ_API_KEY" in _e
          and "GROQ_OSS120_API_KEY" in _e)
    # Retiring the `groq` rung deletes the GROQ_API_KEY alias from the container
    # (sandbox.py withholds disabled rungs' keys). The tool's own rung name must
    # be enough on its own, or a provider retirement disarms inference silently.
    with open(askmod.STATE, "w", encoding="utf-8") as _f:
        json.dump({"day": time.strftime("%Y-%m-%d", time.gmtime()),
                   "used": askmod.DAILY_CAP}, _f)
    for _n in askmod.ENV_KEYS:
        _c, _o, _e = _run_main(["ask", "hello"], env_key="fake", env_name=_n)
        check("ask: %s alone satisfies the key requirement" % _n,
              _c == 4 and "budget" in _e)   # reached the budget gate => key accepted
    with open(askmod.STATE, "w", encoding="utf-8") as _f:
        json.dump({"day": time.strftime("%Y-%m-%d", time.gmtime()),
                   "used": askmod.DAILY_CAP}, _f)
    _c, _o, _e = _run_main(["ask", "hello"], env_key="fake-key-never-sent")
    check("ask: budget spent -> exit 4 BEFORE any network call, stdout empty",
          _c == 4 and _o == "" and "budget" in _e)

    # ---- load-bearing tools: the blast radius of a name ----
    _dep = loop._dependency_summary()
    check("dependency summary: reports in-degree, not just edge totals",
          "load_bearing" in _dep and isinstance(_dep["load_bearing"], list))

    # ---- jsonl parse rate (the scar that came back 36h after being fixed) ----
    # Both payloads below are the creature's REAL output, not authored here: the
    # multi-line one is what its rewritten keyword-archive-store emits via
    # `cat <<JSON`, the compact one is what the consented `jq -nc` fix produced.
    from volume.tools import jsonl_parse_rate as _jpr
    _p = os.path.join(TMP, "archive_probe.jsonl")
    with open(_p, "w", encoding="utf-8") as _f:
        _f.write('{\n  "keyword": "test-key",\n  "content": "First test note",\n'
                 '  "added_at": "2026-08-08T10:15:16Z"\n}\n')
    check("jsonl: multi-line record is counted as unreadable", _jpr(_p) == (0, 5))
    with open(_p, "w", encoding="utf-8") as _f:
        _f.write('{"keyword":"test-key","content":"First test note"}\n'
                 '{"keyword":"test-key","content":"Second test note"}\n')
    check("jsonl: compact one-per-line records all parse", _jpr(_p) == (2, 2))
    with open(_p, "w", encoding="utf-8") as _f:
        _f.write('{"a":1}\n\n   \n{"b":2}\n')
    check("jsonl: blank lines are not counted against the rate", _jpr(_p) == (2, 2))
    check("jsonl: a missing file reports unreadable, does not raise",
          _jpr(os.path.join(TMP, "no_such_archive.jsonl")) == (None, None))
    # No sampling cap. On 2026-08-11 a runaway wrote 4,309 four-line records; the
    # capped version reported "2000 lines" for a 16,862-line file AND pinned the
    # doubling rule below its own trigger, so the escalation was silent by
    # arithmetic. Magnitude has to be true or it cannot convey urgency.
    with open(_p, "w", encoding="utf-8") as _f:
        _f.write('{\n  "keyword": "Q: command or missing arguments.",\n'
                 '  "content": "deep_answer_synth,qa"}\n' * 3000)
    check("jsonl: counts the whole file, no 2000-line cap",
          _jpr(_p) == (0, 9000))

    # ---- data warning: the fact the creature can never ask for (2026-08-08) ----
    # Both fixtures are real. The multi-line record is what keyword-archive-store
    # emits via `cat <<JSON` since the consented `jq -nc` fix was rewritten away;
    # the example.com line is what the mock fetcher fed to 55 dependent tools.
    # A tool it must CHOOSE to run cannot catch either -- not knowing anything is
    # wrong is the fault -- so the fact has to arrive unasked.
    _ddir = os.path.join(loop.VOLUME_MOUNT, "data")
    os.makedirs(_ddir, exist_ok=True)
    _probe = os.path.join(_ddir, "zz_probe.jsonl")
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write('{\n  "keyword": "test-key",\n  "content": "First test note",\n'
                 '  "added_at": "2026-08-08T10:15:16Z"\n}\n')
    _dw = loop._build_data_warning()
    check("data warning: an unreadable store is stated as a fact",
          "zz_probe.jsonl" in _dw and "parse 0 of them" in _dw)
    check("data warning: states the INVARIANT, not a mechanism to avoid",
          "one record per line" in _dw)
    check("data warning: names no tool and gives no advice",
          "keyword-archive-store" not in _dw and "should" not in _dw.lower())
    # The anti-loop contract: if it investigates, fixes nothing, and the same
    # paragraph returns every cycle, we have built a trap rather than a signal.
    check("data warning: an unchanged fault is NOT repeated next cycle",
          loop._build_data_warning() == "")
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write('{"url":"https://example.com/article1","title":"Test Article 1"}\n')
    check("data warning: fabricated reserved-domain content is counted",
          "RFC 2606" in loop._build_data_warning())
    # The 2026-08-17 variant, fixture verbatim from the live archive tail: with
    # the helper finally failing honestly, a CALLER converted the failure back
    # into an answer-shaped string and archived it tagged gap_filled. The
    # disease one level up the stack. Pre-registered trigger (report No. 3).
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write('{\n  "keyword": "given_the_following_content_and_goal",\n'
                 '  "content": "Answer not available (fallback).",\n'
                 '  "added_at": "2026-08-17T15:01:51Z","tags":["gap_filled"]}\n')
    _dw = loop._build_data_warning()
    check("data warning: a failure notice stored as an answer is counted",
          "failure notices" in _dw)
    check("data warning: the placeholder fact states the consequence, not a tool",
          "recalled" in _dw and "gap_filler" not in _dw)
    check("data warning: placeholder flip fires, stable count stays quiet",
          loop._data_state_worsened({"files": {}, "fabricated": 0, "placeholders": 1},
                                    {"files": {}, "fabricated": 0})
          and not loop._data_state_worsened(
              {"files": {}, "fabricated": 0, "placeholders": 5},
              {"files": {}, "fabricated": 0, "placeholders": 5})
          and loop._data_state_worsened(
              {"files": {}, "fabricated": 0, "placeholders": 10},
              {"files": {}, "fabricated": 0, "placeholders": 5}))
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write('{"keyword":"k","content":"a real note"}\n')
    check("data warning: silent about a store whose records all parse",
          "zz_probe.jsonl" not in loop._build_data_warning())
    # ...and a NEW fault after a clean period speaks up again, so going quiet
    # is not the same as going deaf.
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write('{\n  "keyword": "k",\n  "content": "broken again"\n}\n')
    check("data warning: a fault returning after a clean state fires again",
          "zz_probe.jsonl" in loop._build_data_warning())
    os.remove(_probe)

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

    # ---- wake cost: the instrument for the class, not the instance ----------
    # Fixing the 187,489-scan was fixing one function. This watches every
    # per-cycle builder, because they all live inside _build_context.
    _wc = os.path.join(TMP, "wake_cost.json")
    check("wake-cost tests write to TMP, never the real state file",
          _wc.startswith(TMP) and _wc != loop.WAKE_COST_STATE_PATH)

    # A healthy cost never shouts, however many cycles run.
    _crossings = 0
    for _ in range(30):
        _p50, _mx, _cr = loop._record_wake_cost(1090.0, path=_wc)
        _crossings += 1 if _cr else 0
    check("a healthy per-cycle cost never fires the budget",
          _crossings == 0 and abs(_p50 - 1090.0) < 1)

    # Drive it into the fault state: the observed 45,032 ms.
    _fired = 0
    for _ in range(30):
        _p50b, _mxb, _cr = loop._record_wake_cost(45032.0, path=_wc)
        _fired += 1 if _cr else 0
    check("the budget fires when the cost reaches the observed fault state",
          _fired == 1)
    check("it fires ONCE on the edge, not every cycle while it lasts",
          _fired == 1 and _p50b > loop.WAKE_COST_BUDGET_MS)

    # A fresh file must not shout on its first sample -- one cold cycle is not
    # a regression, and a brand-new install must not open with an alarm.
    _wc2 = os.path.join(TMP, "wake_cost2.json")
    _first = loop._record_wake_cost(45032.0, path=_wc2)[2]
    check("a single cold sample does not fire the budget",
          _first is False)

    # p50, not mean: one outlier must not move the verdict.
    check("the summary is a median, so one outlier cannot swing it",
          loop._wake_cost_summary([1000, 1000, 1000, 1000, 99999])[0] == 1000)

    # The recorder must never be able to kill a cycle.
    check("an unwritable path degrades quietly instead of raising",
          loop._record_wake_cost(1.0, path=os.path.join(TMP, "no", "such",
                                                        "dir", "x.json"))
          == (0.0, 0.0, False))

    # The checker must read the producer's budget, never restate it.
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(loop.__file__))), "scripts",
            "spine_health.py"), encoding="utf-8") as _shf:
        _shsrc = _shf.read()
    check("the health reader imports the budget rather than carrying a copy",
          "WAKE_COST_BUDGET_MS as budget" in _shsrc
          and str(loop.WAKE_COST_BUDGET_MS) not in
              _shsrc.split("def check_wake_cost")[1].split("def journal_integrity")[0])

    # ---- the builder's trigger, now that it can be computed ----------------
    # Redefined 2026-08-18. The parked wording ("demanded stubs >= 5 sustained
    # above zero for 7 consecutive days") could not be evaluated: demand_counts
    # is a cumulative all-time counter, and the stub organ zeroes the population
    # the sentence names. The trigger is now the DAILY DELTA of unmet demand.
    import importlib.util as _ilu
    _shp = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(loop.__file__))), "scripts", "spine_health.py")
    _spec = _ilu.spec_from_file_location("_spine_health_probe", _shp)
    _sh = _ilu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_sh)
        _sh_ok = True
    except Exception as _she:
        print(f"SKIP unmet-demand tests (spine_health did not import: {_she})")
        _sh_ok = False

    if _sh_ok:
        # NEVER let this touch the real snapshot. record/save helpers in this
        # codebase have flattened live state from a test before (quota_state,
        # 2026-08-10), so repoint the module constant and ASSERT the repoint.
        _sh.UNMET_STATE = os.path.join(TMP, "unmet.json")
        check("unmet-demand state is repointed away from the real file",
              _sh.UNMET_STATE.startswith(TMP))

        def _days(vals, start=1):
            return [{"day": "2026-07-%02d" % (start + i), "names": 1, "demand": v}
                    for i, v in enumerate(vals)]

        # Seven consecutive growing days is the condition; six is not.
        check("streak fires at 7 consecutive growing days",
              _sh.unmet_streak(_days([1, 2, 3, 4, 5, 6, 7, 8])) >= 7)
        check("streak does NOT fire at 6",
              _sh.unmet_streak(_days([1, 2, 3, 4, 5, 6, 7])) == 6)
        # A flat day is the organ keeping up -- it must break the streak.
        check("a flat day breaks the streak",
              _sh.unmet_streak(_days([1, 2, 3, 4, 4, 5, 6, 7])) == 3)
        # A missing calendar day is absence of evidence, not a zero.
        _gap = _days([1, 2, 3]) + [{"day": "2026-07-06", "names": 1, "demand": 4},
                                   {"day": "2026-07-07", "names": 1, "demand": 5}]
        check("a missing day breaks the streak rather than counting as growth",
              _sh.unmet_streak(_gap) == 1)
        # A counter rewrite shows as a big negative delta; never smoothed.
        check("a counter reset breaks the streak instead of being repaired",
              _sh.unmet_streak(_days([9, 10, 11, 2, 3])) == 1)

        # The normaliser both halves of the comparison use must strip tool
        # extensions, or every .py tool reads as absent.
        check("unmet key strips tool extensions on both sides",
              _sh._unmet_key("foo.py") == _sh._unmet_key("foo")
              == _sh._unmet_key("/mind/tools/own/foo.py"))

        # A demanded name with a real file behind it is NOT unmet.
        _tdir = os.path.join(TMP, "unmet_lib")
        os.makedirs(os.path.join(_tdir, "tools", "own"), exist_ok=True)
        os.makedirs(os.path.join(_tdir, "tools", "framework"), exist_ok=True)
        with open(os.path.join(_tdir, "tools", "own", "real_tool.py"), "w",
                  encoding="utf-8") as _f:
            _f.write(NL.join(("#!/usr/bin/env python3", "# tool: real_tool",
                              "print(1)", "")))
        _old_mind, _old_own = _sh.MIND, _sh.OWN
        try:
            _sh.MIND = _tdir
            _sh.OWN = os.path.join(_tdir, "tools", "own")
            _u = _sh.unmet_demand_now({"real_tool": 9, "never_built": 12})
            check("a demanded name WITH a file is not unmet",
                  "real_tool" not in _u)
            check("a demanded name with NO file is unmet",
                  _u.get("never_built") == 12)
            check("demand below the floor is not unmet",
                  "quiet" not in _sh.unmet_demand_now({"quiet": 1}))
        finally:
            _sh.MIND, _sh.OWN = _old_mind, _old_own

    # ---- tools that cannot start (2026-08-19) -------------------------------
    # Twelve files in the live library carry backslash-escaped triple quotes,
    # `prompt = f\\"""`, from the creature generating Python through a shell
    # layer whose escapes survived into the file. Two were live and invoked 30 and
    # 12 times in a week; one of them ran inside a multi-command block so the block
    # exited 0 and the breakage wore success.
    BS = chr(92)
    _bt_own = os.path.join(TMP, "brokenlib", "tools", "own")
    os.makedirs(os.path.join(TMP, "brokenlib", "state"), exist_ok=True)
    os.makedirs(_bt_own, exist_ok=True)

    def _put(name, body, executable=True):
        _p = os.path.join(_bt_own, name)
        with open(_p, "w", encoding="utf-8") as f:
            f.write(body)
        # The warning now uses the SAME predicate as the done-gate, which includes
        # the execute bit, so a fixture written with open() and left without +x
        # reads as unstartable on POSIX. A real tool has the bit; give it to them.
        if executable and os.name == "posix":
            import stat as _st
            os.chmod(_p, os.stat(_p).st_mode | _st.S_IXUSR)

    # REAL shape, copied from the live corpus, not authored to match the detector.
    _put("escaped_quotes", "#!/usr/bin/env python3" + NL
         + "prompt = f" + BS + '"' + BS + '"' + BS + '"hello' + NL)
    _put("healthy_py", "#!/usr/bin/env python3" + NL + "print(1)" + NL)
    # The false positive that would matter most: a shell tool must never be judged
    # by Python's grammar, or the whole bash half of the library reads as broken.
    _put("healthy_sh", "#!/bin/bash" + NL + "if [ -f x ]; then echo hi; fi" + NL)
    _put("empty_tool", "")

    _bt_prev_vm = loop.VOLUME_MOUNT
    _bt_prev_broken = loop.BROKEN_WARNING_STATE_PATH
    _bt_prev_cache = loop.BROKEN_CACHE_PATH
    loop.VOLUME_MOUNT = os.path.join(TMP, "brokenlib")
    loop.BROKEN_WARNING_STATE_PATH = os.path.join(TMP, "brokenlib", "state", "bw.json")
    loop.BROKEN_CACHE_PATH = os.path.join(TMP, "brokenlib", "state", "pc.json")
    check("broken-tool tests point at a library in TMP, not the real volume",
          loop.VOLUME_MOUNT.startswith(TMP)
          and loop.BROKEN_CACHE_PATH.startswith(TMP))
    try:
        _br = loop._library_broken_tools()
        check("the real escaped-quote corruption is detected",
              "escaped_quotes" in _br and "line 2" in _br["escaped_quotes"])
        check("a bash tool is NOT judged by Python's grammar",
              "healthy_sh" not in _br)
        check("valid python and an empty file are not reported as broken",
              "healthy_py" not in _br and "empty_tool" not in _br)

        # First sighting speaks; an unchanged set stays silent. A fact repeated
        # every cycle is a nag the creature learns to skip.
        _w1 = loop._build_broken_tool_warning()
        check("the warning names the count and the tool on first sighting",
              "escaped_quotes" in _w1 and "cannot start" in _w1)
        _w2 = loop._build_broken_tool_warning()
        check("an unchanged set of broken tools says nothing further",
              _w2 == "")

        # It must state the INVARIANT, not the mechanism. Told "stop escaping
        # quotes" it would obey the letter and reach the same fault another way.
        # Judge the GUIDANCE line, not the whole block: the tool names come from
        # the library and may legitimately contain anything.
        _guide = [l for l in _w1.splitlines() if "A tool must" in l]
        check("the warning states the invariant, not the mechanism to avoid",
              len(_guide) == 1 and "must be able to start" in _guide[0]
              and not any(w in _guide[0].lower()
                          for w in ("escap", "quote", "heredoc", "backslash")))

        # The parse cache is what keeps this off the quadratic-scan list: at 485
        # tools a full ast.parse every cycle is precisely the cost class that hid
        # the 187,489-scan. Prove unchanged files are not re-parsed.
        _calls = []
        _real_tse = _vtools_g.tool_syntax_error

        def _counting(name, text):
            _calls.append(name)
            return _real_tse(name, text)
        _vtools_g.tool_syntax_error = _counting
        try:
            loop._library_broken_tools()
            check("an unchanged library is not re-parsed (the cache holds)",
                  _calls == [])
            # touch one file: only that one is re-parsed
            _p = os.path.join(_bt_own, "healthy_py")
            with open(_p, "w", encoding="utf-8") as f:
                f.write("#!/usr/bin/env python3" + NL + "print(2)" + NL)
            os.utime(_p, (time.time() + 5, time.time() + 5))
            _calls.clear()
            loop._library_broken_tools()
            check("a changed file IS re-parsed, and only that one",
                  _calls == ["healthy_py"])
        finally:
            _vtools_g.tool_syntax_error = _real_tse

        # The warning and the gate must agree about what "cannot start" means.
        # They did not until 2026-08-22: the gate used tool_start_failure and the
        # warning used tool_syntax_error, so `proactiverearchpipeline` -- valid
        # Python, correct shebang, written with `cat > ...` and therefore with no
        # execute bit -- was invisible to BOTH. One predicate now.
        if os.name == "posix":
            _put("no_exec_bit", "#!/usr/bin/env python3" + NL + "print(1)" + NL,
                 executable=False)
            _nb = loop._library_broken_tools()
            check("a tool with no execute bit is reported as unable to start",
                  "no_exec_bit" in _nb)
            # THE cache trap: chmod +x changes neither mtime nor size, so a key of
            # (mtime, size) would keep reporting a tool the creature had just
            # fixed -- a stale nag rather than a signal.
            import stat as _st2
            _nep = os.path.join(_bt_own, "no_exec_bit")
            os.chmod(_nep, os.stat(_nep).st_mode | _st2.S_IXUSR)
            check("chmod +x invalidates the cache, so a fixed tool leaves the list",
                  "no_exec_bit" not in loop._library_broken_tools())
            os.remove(_nep)

        # A redirect into tools/own is authoring a tool, and the creature does it.
        check("a heredoc redirect into tools/own counts as touching that tool",
              loop._tools_touched(
                  [("cat << 'EOF' > /mind/tools/own/written_raw", 0)])
              == {"written_raw"})
        check("tee counts too, append or not",
              loop._tools_touched([("x | tee -a tools/own/t1", 0)]) == {"t1"})
        check("but merely READING a tool file is not authoring it",
              loop._tools_touched([("cat /mind/tools/own/somebody_elses", 0)])
              == set())

        # ---- reaching for a broken tool re-arms the warning (2026-08-23) ----
        # Found by gs-bug-daily on its first run: the set stabilised at 32 on
        # 08-22 09:16 and the warning then said NOTHING for 28 hours -- zero
        # mentions in the wake context -- while all 32 stayed broken. Told about 9
        # it had repaired two within a day; told about 32 once and never again, it
        # repaired none. Set-change alone is not enough to keep a fact present.
        _rj_use = [{"kind": "exec_start",
                    "content": "Block 1: escaped_quotes --topic x"}]
        _w4 = loop._build_broken_tool_warning()          # settle the set first
        _w5 = loop._build_broken_tool_warning()
        check("a stable set still says nothing on its own (no nagging)",
              _w5 == "")
        _w6 = loop._build_broken_tool_warning(_rj_use)
        check("reaching for a broken tool re-arms the warning",
              _w6 != "" and "escaped_quotes" in _w6)
        check("and it leads with what was reached for, not the whole list",
              "You reached for" in _w6)
        _w7 = loop._build_broken_tool_warning(_rj_use)
        check("reaching for the SAME tool again does not repeat the warning",
              _w7 == "")
        # A mention in its own reasoning is not an attempt to run it.
        _rj_think = [{"kind": "think_end",
                      "content": "later I might use hdr_no_hash for this"}]
        check("a think-record mention is not 'reaching for' a tool",
              loop._build_broken_tool_warning(_rj_think) == "")

        # A newly broken tool re-arms the warning.
        _put("second_break", "#!/usr/bin/env python3" + NL + "def f(:" + NL)
        _w3 = loop._build_broken_tool_warning()
        check("a NEWLY broken tool re-arms the warning",
              "second_break" in _w3 and "2 of your tools" in _w3)
    finally:
        loop.VOLUME_MOUNT = _bt_prev_vm
        loop.BROKEN_WARNING_STATE_PATH = _bt_prev_broken
        loop.BROKEN_CACHE_PATH = _bt_prev_cache

    # ---- throughput: the vital sign nothing was watching (2026-08-19) -------
    # On 08-19 one rung's unrecognised 402 hard-raised and killed 651 cycles;
    # thinks fell from 1,467/day to a 6/hour rate and every existing instrument
    # stayed quiet, because each was watching something else. This watches the
    # creature itself.
    if _sh_ok:
        _jt = os.path.join(TMP, "throughput_journal.jsonl")

        def _write_journal(recs):
            with open(_jt, "w", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r) + NL)

        _now = 1787000000.0
        _real_journal = _sh.JOURNAL
        _sh.JOURNAL = _jt
        check("throughput tests read a journal in TMP, not the real one",
              _sh.JOURNAL.startswith(TMP) and _sh.JOURNAL != _real_journal)
        try:
            # Healthy: 40 thinks spread across the last hour.
            _write_journal(
                [{"ts": _now - 3600 + i * 90, "kind": "served_by",
                  "content": "x finish=stop"} for i in range(40)]
                + [{"ts": _now - 3600 + i * 90, "kind": "exec_start",
                    "content": "b"} for i in range(35)])
            _t = _sh.check_throughput(now=_now)
            check("a healthy rate does not raise the throughput alarm",
                  "THROUGHPUT:!!" not in _t and "exec/think" in _t)

            # The 08-19 fault shape: 6 thinks/hour sustained.
            _write_journal([{"ts": _now - 3600 + i * 600, "kind": "served_by",
                             "content": "x finish=stop"} for i in range(6)])
            _t2 = _sh.check_throughput(now=_now)
            check("the 08-19 collapse rate DOES raise the alarm",
                  "THROUGHPUT:!!" in _t2)

            # Total silence must be reported as silence, never divided into a rate.
            _write_journal([{"ts": _now - 99999, "kind": "served_by",
                             "content": "old"}])
            check("no thinking at all is reported as NONE, not as a rate",
                  "NONE" in _sh.check_throughput(now=_now))

            # THE case that would make this lie: the box was off for most of the
            # window. Wall-clock rate would read as a collapse; the rate must be
            # taken over the span that actually produced records. Absence of
            # evidence is not a zero -- the rule the UNMET streak follows too.
            _write_journal([{"ts": _now - 1200 + i * 30, "kind": "served_by",
                             "content": "x finish=stop"} for i in range(40)])
            _t3 = _sh.check_throughput(now=_now)
            check("a box that was switched off for most of the window is not "
                  "reported as a throughput collapse",
                  "THROUGHPUT:!!" not in _t3)

            # The tail reader must not choke on a truncated first line.
            with open(_jt, "w", encoding="utf-8") as f:
                f.write('{"ts": 1, "kind": "ser' + NL)
                f.write(json.dumps({"ts": _now - 60, "kind": "served_by",
                                    "content": "x"}) + NL)
            _recs, _ = _sh._journal_tail_records(path=_jt)
            check("the tail reader skips a torn line instead of raising",
                  len(_recs) == 1)

            # And it must report when it could NOT see the file's start, rather
            # than presenting a partial history as complete.
            _big = os.path.join(TMP, "big.jsonl")
            with open(_big, "w", encoding="utf-8") as f:
                for i in range(400):
                    f.write(json.dumps({"ts": _now - i, "kind": "served_by",
                                        "content": "x" * 200}) + NL)
            _r2, _complete = _sh._journal_tail_records(path=_big, tail_bytes=4096)
            check("a truncated read says it did not reach the journal's start",
                  _complete is False and len(_r2) > 0)
        finally:
            _sh.JOURNAL = _real_journal

    # ---- the dependency scan, compared against its own predecessor ---------
    # The quadratic version (433 names re-searched in every file, 28.3s on the
    # live corpus) is kept HERE, as the oracle, not in loop.py -- one graph
    # builder ships, and this asserts the fast one still agrees with the slow one
    # it replaced. Measured 2026-08-18 on 433 real tools: 28,312ms -> 779ms,
    # 1011 edges both ways, dicts identical.
    def _naive_deps(names, sources):
        """The pre-2026-08-18 implementation, verbatim, as a test oracle."""
        matchable = [n for n in names if len(n) >= 4]
        g = {}
        for tool in names:
            deps = set()
            code = sources.get(tool, "")
            for other in matchable:
                if other == tool:
                    continue
                if _re_g.search(r"(^|[\s/`;|&(])" + _re_g.escape(other)
                                + r"(\s|$|['\"`;|&)])", code, _re_g.M):
                    deps.add(other)
            g[tool] = sorted(deps)
        return g

    import re as _re_g

    def _fast_deps(names, sources):
        pat = loop._dependency_pattern([n for n in names if len(n) >= 4])
        g = {}
        for tool in names:
            d = {m.group(1) for m in pat.finditer(sources.get(tool, ""))} if pat else set()
            d.discard(tool)
            g[tool] = sorted(d)
        return g

    # Cases the lookaround change exists for. finditer returns no overlapping
    # matches, so a boundary group that CONSUMED its delimiter would eat the start
    # of the next name and drop the edge -- silently, with a plausible smaller
    # graph. Authored deliberately: the real corpus is not guaranteed to contain
    # adjacency or prefix collisions, and the oracle means authoring cannot make
    # this pass falsely.
    _names = ["fetch_news", "fetch_news_v2", "store_item", "plan_step"]
    _srcs = {
        "fetch_news": "store_item plan_step",           # ADJACENT: both must count
        "fetch_news_v2": "fetch_news | store_item",     # pipe boundary
        "store_item": "prefix collision: fetch_news_v2",  # not fetch_news
        "plan_step": "no_fetch_news_here xstore_itemx",   # word-internal: neither
    }
    _ref, _got = _naive_deps(_names, _srcs), _fast_deps(_names, _srcs)
    check("dependency scan agrees with the quadratic version it replaced",
          _ref == _got)
    check("adjacent tool names both counted (no delimiter eaten)",
          _got["fetch_news"] == ["plan_step", "store_item"])
    check("a name inside a longer name is not an edge",
          _got["plan_step"] == [] and "fetch_news" not in _got["store_item"])

    # ---- the body's liveness contract (2026-08-18) -------------------------
    # On this day the container's PID namespace filled with 9,082 zombies
    # (`sleep infinity` as PID 1 never reaps). docker reported Running=true for
    # three and a half hours while `echo alive` came back exit 128 with the OCI
    # error ON STDOUT -- infrastructure breakage delivered to the creature shaped
    # exactly like the output of its own command. Both halves are asserted here:
    # the classification, and the stdout-stays-empty contract.
    from executive import sandbox as _sb

    # REAL captured text, not authored: measured from sandbox.run_command on the
    # live laptop at 07:41 on 2026-08-18. A test that writes its own fixture in
    # the words the detector hunts passes forever regardless (scar, CLAUDE.md
    # section 5), so this string is copied from the corpus.
    _oci = ("OCI runtime exec failed: exec failed: unable to start container "
            "process: procReady not received")
    check("exec_setup_failure: the real OCI text is infrastructure, not output",
          _sb.exec_setup_failure(_oci, "", 128) is True)
    check("exec_setup_failure: a command that RAN and failed is not infra",
          _sb.exec_setup_failure("", "grep: no such file", 2) is False
          and _sb.exec_setup_failure("", "", 127) is False)
    check("exec_setup_failure: exit 0 is never infra failure",
          _sb.exec_setup_failure(_oci, "", 0) is False)

    # The contract, reached the way run_command really reaches it: through
    # subprocess.run. Asserting the contract (stdout empty, reason preserved,
    # nonzero code) rather than the mechanism.
    _NL = chr(10)
    class _R:
        def __init__(self, o, e, c):
            self.stdout, self.stderr, self.returncode = o, e, c
    _real_run = _sb.subprocess.run
    try:
        _sb.subprocess.run = lambda *a, **k: _R(_oci + _NL, "", 128)
        _o, _e, _c = _sb.run_command("echo alive")
        check("run_command: infra failure leaves stdout EMPTY",
              _o == "" and _c == 128)
        check("run_command: the reason is kept, on stderr",
              "procReady" in _e)
        _sb.subprocess.run = lambda *a, **k: _R("alive" + _NL, "", 0)
        _o2, _e2, _c2 = _sb.run_command("echo alive")
        check("run_command: a real answer still passes through untouched",
              _o2 == "alive" + _NL and _c2 == 0)
    finally:
        _sb.subprocess.run = _real_run

    # ensure_body must not accept docker's status field as proof of life.
    from executive import runtime as _rtm
    with open(_rtm.__file__, encoding="utf-8") as _rf:
        _src = _rf.read()
    _eb = _src[_src.index("async def ensure_body"):_src.index("def sleep_duration_seconds")]
    check("ensure_body proves liveness by executing, not by asking is_running",
          "body_responds" in _eb)
    check("ensure_body verifies the RESPAWNED body too",
          _eb.count("body_responds") >= 2)

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
