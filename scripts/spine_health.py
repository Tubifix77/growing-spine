#!/usr/bin/env python3
"""spine_health.py -- daily behavioral invariant probe + stub janitor.

Static sweeps find fictions; only running the invariants finds rot.
Checks (all side-effect-free except the janitor move):
  1. SENSOR: wake_catchup_fetcher returns real news (throwaway state file,
     so the creature's own seen-list is untouched). Mock output = the
     network is down OR the mock regressed back in.
  2. STALE FALLBACKS: any composition/breadth fallback title that exists
     as a built tool (own/ or attic/) -- the disease that bit twice.
  3. STUB JANITOR: placeholder stubs in own/ older than AGE_OUT_DAYS move
     to the attic (birth debris must not become permanent residents).
Appends one line per run to ~/spine-health.log.
"""
import json, os, re, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from volume.paths import mind_root as _mind_root   # P2-F13: one derivation
    MIND = _mind_root()
except Exception:
    MIND = os.path.expanduser("~/growing-spine-mind")
OWN, ATTIC = os.path.join(MIND, "tools", "own"), os.path.join(MIND, "tools", "attic")
LOG = os.path.expanduser("~/spine-health.log")
AGE_OUT_DAYS = 3
# Third copy of the stub markers used to live here as a single legacy string
# that tool-new stopped writing -- hence "aged-out 0" on all 28 janitor runs.
# Canonical list now lives in volume/tools.py; import it, never restate it.
sys.path.insert(0, REPO)
from volume.tools import (is_hollow_stub, demand_counts,  # noqa: E402
                          is_demanded, is_fabricated_feed, jsonl_parse_rate,
                          parse_feed_items, tool_stem)
from executive.embed_gate import _is_junk as is_junk_name  # noqa: E402
QUOTA_STATE = os.path.join(REPO, "keychain", "quota_state.json")
CONFIG = os.path.join(REPO, "config.yaml")
FLATLINE_HOURS = 12  # google_gemma sat dead 55h before anyone noticed, 2026-08-02

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def check_sensor():
    # At boot the Persistent timer fires while the network is still coming up
    # AND before the brain's first ensure_body has respawned the container --
    # both raced to SENSOR:fail(JSONDecodeError) on 2026-07-15/16. Four tries
    # 20s apart cover ~1 min of boot settling; a mid-day run passes on try 1.
    last = "SENSOR:fail(no-attempt)"
    for attempt in range(4):
        if attempt:
            time.sleep(20)
        last = _sensor_once()
        if last.startswith("SENSOR:ok") or last == "SENSOR:MOCK(!!)":
            return last  # ok, or a definitive non-transient verdict
    return last


def _sensor_once():
    try:
        out = subprocess.run(
            ["docker", "exec", "-e", "WAKE_CATCHUP_STATE=/tmp/health_probe_state.json",
             "growing-spine-body", "wake_catchup_fetcher"],
            capture_output=True, text=True, timeout=40).stdout.strip()
        # Both shapes: a JSON array, or one object per line. Canonical in
        # volume/tools.py -- never restate it here (2026-08-09: assuming the
        # array shape turned a live MOCK verdict into fail(JSONDecodeError)).
        items = parse_feed_items(out)
        if items is None:
            return "SENSOR:fail(unparseable)"
        if not isinstance(items, list) or not items:
            return "SENSOR:empty"
        # Was: a single literal title, "Mock News Item". On 2026-08-08 the
        # creature's fixture said "Test Article 1" and this returned
        # SENSOR:ok(2 fresh) over two example.com articles. Canonical test now
        # lives in volume/tools.py -- never restate it here.
        if is_fabricated_feed(items):
            return "SENSOR:MOCK(!!)"
        return f"SENSOR:ok({len(items)} fresh)"
    except Exception as e:
        return f"SENSOR:fail({type(e).__name__})"

def check_fallbacks():
    sys.path.insert(0, REPO)
    try:
        from executive.loop import _COMPOSITION_FALLBACKS, _FALLBACK_GAPS
    except Exception as e:
        return f"FALLBACKS:import-fail({type(e).__name__})"
    built = set()
    for d in (OWN, ATTIC):
        try:
            built |= {norm(n) for n in os.listdir(d)}
        except OSError:
            pass
    stale = []
    for fb in _COMPOSITION_FALLBACKS:
        if norm(fb.get("title", "")) in built:
            stale.append("comp:" + fb.get("title", ""))
    for cat, fb in _FALLBACK_GAPS.items():
        if norm(fb.get("title", "")) in built:
            stale.append("gap:" + fb.get("title", ""))
    return f"STALE-FALLBACKS:{len(stale)}[{'; '.join(stale)}]" if stale else "STALE-FALLBACKS:0"

def stub_janitor():
    moved, spared, now = [], [], time.time()
    try:
        names = os.listdir(OWN)
    except OSError:
        return "JANITOR:no-own-dir"
    counts = demand_counts(MIND)
    os.makedirs(ATTIC, exist_ok=True)
    for n in names:
        p = os.path.join(OWN, n)
        if not os.path.isfile(p):
            continue
        # The creature's own .bak_<ts> backups and .broken_* corpses are hollow by
        # definition but are NOT tools -- they are its safety net, and Tue's
        # standing decision on them is "delete nothing, tell it nothing".
        if is_junk_name(n):
            continue
        try:
            if not is_hollow_stub(open(p, encoding="utf-8", errors="replace").read(2000)):
                continue
            if (now - os.path.getmtime(p)) / 86400 < AGE_OUT_DAYS:
                continue
            if is_demanded(n, counts):
                spared.append(n)   # demand -> finish_stub organ, not the attic
                continue
            os.replace(p, os.path.join(ATTIC, n))
            moved.append(n)
        except OSError:
            continue
    out = f"JANITOR:aged-out {len(moved)}" + (f"[{'; '.join(moved)}]" if moved else "")
    if spared:
        out += f"  SPARED-DEMANDED:{len(spared)}[{'; '.join(spared)}]"
    return out

# ---------------------------------------------------------------------------
# UNMET DEMAND -- the builder's trigger, in a form that can actually be read.
#
# The builder graft (the-builder-idea.md) was parked 2026-08-10 behind this:
# "demanded stubs (demand_counts >= 5) sustained above zero for 7 consecutive
# days -- its own hands stopped keeping up." That sentence cannot be evaluated,
# and both of its defects were found on 2026-08-18:
#
#   1. demand_counts is a CUMULATIVE all-time invocation counter with no
#      timestamps (volume/tools.py merges two counters by MAX). Nothing in it
#      can express "sustained", or any present tense at all: health-summary-fixed
#      reads 378 today from invocations that stopped happening months ago, and
#      llm_ask_helper reads 104 for a tool that died in /tmp on 23 June.
#   2. "demanded stubs" names the one population the stub organ zeroes BY
#      CONSTRUCTION -- _finish_stub_spec opens with stubs = _library_hollow_tools()
#      -- so the easy reading of the trigger is guaranteed to read 0 forever
#      while the creature reaches for 336 names that have no file at all. A
#      guard whose count is always exactly zero is broken, not idle.
#
# So the trigger is redefined on the DAILY DELTA of unmet demand, which is the
# quantity the original sentence was reaching for: not "how much unbuilt work has
# ever been asked for" (a number that only ever grows) but "did it reach for
# something it has not built, again, today".
#
# WHO RECEIVES THIS: us, and Tue. It answers a framework question -- whether to
# graft a second actor -- which is not the creature's decision and not a fact
# about its world, so it does NOT go into the wake context. Nothing here changes
# what the creature sees. If the number ever shows a live symptom, THAT is the
# point at which surfacing it to the creature becomes worth designing; today the
# 336 are historical residue and there is no symptom to show it.
UNMET_STATE = os.path.expanduser("~/spine-health-unmet.json")
UNMET_STREAK_DAYS = 7    # from the parked decision's own wording, unchanged
UNMET_HISTORY_DAYS = 30  # enough to see the streak and a month of context


def _unmet_key(name):
    """The ONE normaliser both halves of this comparison use.

    Not spine_health's norm(): that strips punctuation but NOT extensions, so
    norm("foo.py") is "foopy" while the counter's key is "foo" -- every .py tool
    in the library would have read as absent and the unmet count would have come
    out large, plausible and wrong. There are 29 duplicate-stem twins in there.
    A normalisation mismatch between two halves of one comparison is a scar this
    project already owns (67 "unused tools" that were really 8), so both sides go
    through canonical tool_stem here and nothing else.
    """
    return tool_stem(os.path.basename(str(name)))


def unmet_demand_now(counts=None):
    """Names demanded at or above the floor that the creature cannot actually run.

    Unmet means invoked >= DEMAND_FLOOR times and either absent from own/ and
    framework/, or present as a placeholder shell. A hollow stub counts: it is a
    broken promise, not a tool. Junk names (.bak, .broken_*, --show) are excluded
    via the canonical _is_junk -- they are its safety net, never demand.
    """
    counts = demand_counts(MIND) if counts is None else counts
    present, hollow = set(), set()
    for d in (OWN, os.path.join(MIND, "tools", "framework")):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            pth = os.path.join(d, n)
            if not os.path.isfile(pth) or is_junk_name(n):
                continue
            present.add(_unmet_key(n))
            try:
                with open(pth, encoding="utf-8", errors="replace") as f:
                    if is_hollow_stub(f.read(2000)):
                        hollow.add(_unmet_key(n))
            except OSError:
                pass
    unmet = {}
    for name, c in counts.items():
        # is_demanded owns the floor. Restating DEMAND_FLOOR as a literal here is
        # how a producer and a checker drift apart (CLAUDE.md section 4).
        if is_junk_name(name) or not is_demanded(name, counts):
            continue
        k = _unmet_key(name)
        if k not in present or k in hollow:
            unmet[name] = c
    return unmet


def _unmet_load():
    try:
        with open(UNMET_STATE, encoding="utf-8") as f:
            st = json.load(f)
        if isinstance(st, dict) and isinstance(st.get("days"), list):
            return st, False
    except Exception:
        pass
    return {"days": []}, True


def unmet_streak(days):
    """Consecutive most-recent CALENDAR days whose unmet demand grew.

    A gap in dates breaks the streak: the box was off, so there is no evidence
    for that day and "7 consecutive days" must mean seven real ones. A delta of
    zero or less also breaks it -- that is the creature's own hands, or the stub
    organ, keeping up, which is exactly what the trigger is watching for.

    A counter rewrite shows up as a large negative delta and simply breaks the
    streak; it is never smoothed away, because a silently repaired number is how
    this project's worst measurements were made.
    """
    streak = 0
    for i in range(len(days) - 1, 0, -1):
        cur, prev = days[i], days[i - 1]
        try:
            d0 = time.strptime(prev["day"], "%Y-%m-%d")
            d1 = time.strptime(cur["day"], "%Y-%m-%d")
        except Exception:
            break
        if round((time.mktime(d1) - time.mktime(d0)) / 86400) != 1:
            break                       # missing day -- no evidence, not a zero
        if cur.get("demand", 0) - prev.get("demand", 0) <= 0:
            break
        streak += 1
    return streak


def check_unmet_demand(today=None):
    """One record per DAY; hourly runs on the same date just re-read it."""
    today = today or time.strftime("%Y-%m-%d")
    st, fresh = _unmet_load()
    unmet = unmet_demand_now()
    names, demand = len(unmet), sum(unmet.values())
    days = [d for d in st["days"] if d.get("day") != today]
    days.append({"day": today, "names": names, "demand": demand})
    days = days[-UNMET_HISTORY_DAYS:]
    st["days"] = days
    try:
        tmp = UNMET_STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, UNMET_STATE)
    except OSError:
        pass
    if fresh and len(days) == 1:
        return f"UNMET:first({names}n/{demand}d)"
    streak = unmet_streak(days)
    delta = demand - days[-2]["demand"] if len(days) > 1 else 0
    tag = f"UNMET:{names}n/{demand}d{delta:+d} streak {streak}/{UNMET_STREAK_DAYS}"
    if streak >= UNMET_STREAK_DAYS:
        # The parked builder decision's condition (1) is met. Says so; does
        # nothing else. The graft is a decision, not an automation.
        top = sorted(unmet.items(), key=lambda kv: -kv[1])[:3]
        tag += ("  BUILDER-TRIGGER:!!["
                + "; ".join(f"{n}x{c}" for n, c in top) + "]")
    return tag


WAKE_COST_STATE = os.path.expanduser("~/spine-wake-cost.json")


def check_wake_cost():
    """Report the per-cycle context-build cost the brain recorded.

    The NUMBER goes in the line every day, not only when it breaches: the fault
    this watches for grows slowly with the creature's own success, so a visible
    trend is worth more than a threshold being exactly right. Written by
    loop._record_wake_cost; budget and derivation live there, and this reader
    imports the budget rather than restating it -- a producer and a checker that
    each carry their own copy of a number always drift.
    """
    try:
        with open(WAKE_COST_STATE, encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        return "WAKE:no-data"
    if not isinstance(st, dict) or not st.get("n"):
        return "WAKE:no-data"
    try:
        from executive.loop import WAKE_COST_BUDGET_MS as budget
    except Exception:
        return ("WAKE:p50 %.0fms max %.0fms n%s"
                % (st.get("p50") or 0, st.get("max") or 0, st.get("n")))
    age_h = (time.time() - (st.get("updated") or 0)) / 3600.0
    tag = ("WAKE:p50 %.0fms max %.0fms n%s"
           % (st.get("p50") or 0, st.get("max") or 0, st.get("n")))
    if age_h > 3:
        # The brain has not recorded a cycle in hours. That is not a wake-cost
        # fault, and this check must not report a stale number as a live one.
        return tag + "(STALE %.0fh)" % age_h
    if st.get("over"):
        tag += ("  WAKE-BUDGET:!![%.0fms > %dms -- a per-cycle cost is growing]"
                % (st.get("p50") or 0, budget))
    return tag


def journal_integrity():
    """Detect + auto-repair torn/interleaved journal lines (abrupt-shutdown
    damage). Recovers the last complete {...} object from a torn line; drops
    only the unrecoverable fragment. Backs up before any rewrite."""
    jpath = os.path.join(MIND, "journal.jsonl")
    try:
        # Audit P1-F20: read -> repair -> rewrite with no lock, while the
        # executive appends continuously. Every append landing inside that window
        # was overwritten by the rewrite. The hot append path is deliberately
        # NOT given a lock (it runs many times a cycle), so instead: remember how
        # many bytes we read, and re-read the tail just before writing.
        _size_at_read = os.path.getsize(jpath)
        lines = open(jpath, encoding="utf-8", errors="replace").readlines()
    except OSError:
        return "JOURNAL:no-file"
    bad = []
    for i, l in enumerate(lines):
        if not l.strip():
            continue
        try:
            json.loads(l)
        except Exception:
            bad.append(i)
    if not bad:
        return "JOURNAL:clean"
    # repair
    import shutil, time as _t
    shutil.copy(jpath, jpath + ".bak-" + _t.strftime("%Y%m%d-%H%M%S"))
    fixed, recovered, dropped = [], 0, 0
    for l in lines:
        s = l.strip()
        if not s:
            continue
        try:
            json.loads(s)
            fixed.append(l if l.endswith("\n") else l + "\n")
            continue
        except Exception:
            pass
        ok = False
        for start in [i for i, c in enumerate(s) if c == "{"]:
            try:
                obj = json.loads(s[start:])
                fixed.append(json.dumps(obj) + "\n")
                recovered += 1
                ok = True
                break
            except Exception:
                continue
        if not ok:
            dropped += 1
    # Anything appended while we were repairing: carry it over verbatim.
    _tail = ""
    try:
        if os.path.getsize(jpath) > _size_at_read:
            with open(jpath, encoding="utf-8", errors="replace") as _tf:
                _tf.seek(_size_at_read)
                _tail = _tf.read()
    except OSError:
        pass
    # Atomic: a crash mid-rewrite must not truncate the journal to nothing.
    _tmp = jpath + ".repair.tmp"
    with open(_tmp, "w", encoding="utf-8") as _wf:
        _wf.writelines(fixed)
        if _tail:
            if not _tail.startswith("\n") and fixed and not fixed[-1].endswith("\n"):
                _wf.write("\n")
            _wf.write(_tail)
    os.replace(_tmp, jpath)
    return f"JOURNAL:REPAIRED {len(bad)} torn (recovered {recovered}, dropped {dropped})"


# Which flatlines are a FAULT, and which are just a low rung nobody reached.
#
# 2026-08-06: the probe never exited non-zero, so systemd could not tell a
# healthy run from "the 82%-of-thinks workhorse has been dead for 55 hours".
# But a blanket "any !! fails" would cry wolf permanently: four OpenRouter rungs
# sit quiet for days BY DESIGN, because they are the floor of the ladder and the
# rungs above them keep serving. So severity follows ladder position: the rungs
# listed BEFORE the first openrouter entry are the ones that actually carry
# traffic, and their silence is the outage shape. Derived from config order, so
# it needs no maintenance when the ladder changes.
DEAD_KEYS = set()    # primary rung keys, filled by check_flatline
SILENT_KEYS = set()  # every flatlined key, filled by check_flatline


def primary_rungs(cfg) -> set:
    """Enabled providers ahead of the first openrouter rung: the traffic carriers."""
    out = set()
    for prov in cfg.get("providers", []):
        # str(): YAML parses a bare off/on/yes/no key as a BOOLEAN (the "Norway
        # problem"), so a config key is not guaranteed to be a string.
        key = str(prov.get("key", ""))
        if key.startswith("openrouter"):
            break
        if prov.get("enabled", True):
            out.add(key)
    return out


def exit_code(silent: set, primaries: set) -> int:
    """1 if a traffic-carrying rung has gone silent, else 0."""
    return 1 if (silent & primaries) else 0


def check_tool_wiring():
    """Do the creature's own tools agree with each other about WHERE data lives?

    2026-08-06. `keyword-archive-store` has written 1,670 times to
    /workspace/keyword_archive.jsonl; `keyword-archive-search` has read 934 times
    from /mind/memarch/keyword-archive.jsonl, which is 0 bytes. Neither tool ever
    errored: the reader's contract is "if the archive is missing or empty, return
    no results without error". The same conceptual archive exists at FIVE paths.

    The cause is in OUR half, not its tools. protected-prompt.md tells it durable
    data "must store it under /mind or /workspace" -- durability, not IDENTITY.
    Two acceptable answers, no naming convention, so two obedient tools written on
    different days cannot find each other. (We had the identical bug: five
    derivations of the mind root, collapsed into volume/paths.py the same day.)

    This is a SENSOR, not a repair. Its tools are its world; we do not edit them
    and we do not tell it about its own bugs. It reports to the humans only.
    """
    own = os.path.join(MIND, "tools", "own")
    pathre = re.compile(r"[\"']((?:/mind|/workspace)/[A-Za-z0-9_./\-]+)[\"']")
    def canon(pth):
        return re.sub(r"[^a-z0-9]", "", os.path.basename(pth).lower())
    def host(pth):
        return (pth.replace("/mind", MIND)
                   .replace("/workspace", os.path.expanduser("~/growing-spine-workspace")))
    groups, readers = {}, {}
    try:
        names = os.listdir(own)
    except OSError:
        return "WIRING:no-own-dir"
    for n in names:
        fp = os.path.join(own, n)
        if not os.path.isfile(fp) or is_junk_name(n):
            continue
        try:
            body = open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in pathre.finditer(body):
            pth = m.group(1)
            if "." not in os.path.basename(pth):
                continue
            groups.setdefault(canon(pth), set()).add(pth)
            readers.setdefault(pth, set()).add(n)
    split = {k: v for k, v in groups.items() if len(v) > 1}
    if not split:
        return "WIRING:ok"
    out = []
    for k, paths in sorted(split.items()):
        sizes = []
        for pth in sorted(paths):
            try:
                sz = os.path.getsize(host(pth))
            except OSError:
                sz = -1
            sizes.append(f"{pth}={sz}b/{len(readers.get(pth, ()))}t")
        # the damning signature: someone reads an EMPTY copy while another is fat
        empty = [x for x in sizes if "=0b" in x]
        fat = [x for x in sizes if "=0b" not in x and "=-1b" not in x]
        flag = " ORPHANED-READER" if empty and fat else ""
        out.append(f"{k}({len(paths)} paths){flag}: " + "; ".join(sizes))
    return f"WIRING:!!{len(split)}[" + " | ".join(out) + "]"

def check_jsonl():
    """Can the creature read back what it just wrote? (2026-08-08)

    /mind/data is where the contract says shared data lives, and .jsonl means one
    record per LINE. Nothing verified that, and the breach has happened twice --
    `jq -n` on 7 Aug, a multi-line heredoc on 8 Aug after the first fix was
    rewritten away. Both times: write succeeds, read returns empty, nobody errors.

    Reports the parse rate rather than a pass/fail, because the number is the
    alarm: "4/104" says what "broken" cannot. Deliberately does NOT touch the exit
    code -- that means "a provider went silent" and overloading it would make
    `systemctl --user --failed` ambiguous. This is for the daily line and for Tue.
    """
    d = os.path.join(MIND, "data")
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith(".jsonl"))
    except OSError:
        return "JSONL:no-data-dir"
    bad, checked = [], 0
    for n in names:
        ok, total = jsonl_parse_rate(os.path.join(d, n))
        if not total:
            continue  # empty or unreadable: nothing to judge
        checked += 1
        if ok < total:
            bad.append(f"{n}({ok}/{total} parse)")
    if not checked:
        return "JSONL:none"
    return f"JSONL:!!{len(bad)}[" + "; ".join(bad) + "]" if bad else f"JSONL:ok({checked})"


def check_flatline():
    """FLATLINE: an ENABLED provider with no success in FLATLINE_HOURS.
    Silence is the failure mode that already bit once -- google_gemma
    (82%% of all thinks) sat with zero successes for 55h, Aug 2->4, 2026,
    masked because smaller thinks kept succeeding elsewhere and nothing
    ever printed "gemma is down". A wall alone is normal (quota exhaustion
    is the free tier working); FLATLINE fires only when last_success is
    older than the threshold, regardless of exhausted_at -- catches a
    provider that keeps failing on every re-probe just as well as one that
    stopped being tried at all."""
    try:
        import yaml
        cfg = yaml.safe_load(open(CONFIG))
        enabled = {p["key"] for p in cfg.get("providers", []) if p.get("enabled", True)}
    except Exception as e:
        return f"FLATLINE:fail(config:{type(e).__name__})"
    try:
        state = json.load(open(QUOTA_STATE))
    except Exception as e:
        return f"FLATLINE:fail(state:{type(e).__name__})"
    now = time.time()
    DEAD_KEYS.clear()
    DEAD_KEYS.update(primary_rungs(cfg))
    dead = []
    for key in sorted(enabled):
        last = state.get(key, {}).get("last_success_at")
        age_h = (now - last) / 3600 if last else None
        if age_h is None or age_h >= FLATLINE_HOURS:
            dead.append(f"{key}({'never' if age_h is None else str(int(age_h)) + 'h'})")
            SILENT_KEYS.add(key)
    return "FLATLINE:!!" + ",".join(dead) if dead else "FLATLINE:ok"


if __name__ == "__main__":
    line = (time.strftime("%Y-%m-%d %H:%M") + "  "
            + "  ".join([check_sensor(), check_fallbacks(), stub_janitor(),
                         journal_integrity(), check_tool_wiring(),
                         check_jsonl(), check_flatline(),
                         check_unmet_demand(), check_wake_cost()]))
    _rc = exit_code(SILENT_KEYS, DEAD_KEYS)
    if _rc:
        line += f"  SERIOUS:{','.join(sorted(SILENT_KEYS & DEAD_KEYS))}"
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line)
    sys.exit(_rc)
