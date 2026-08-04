"""Meta-Architect v1 (2026-08-01, Tue's design): one LLM ruling per refill
over the gate-surviving batch, fed a machine-gathered evidence pack (library
census, usage histogram, lineage-variant drift). It advises and steers --
KEEP/DROP/RESHAPE per idea, a timed directive, a wanted-list for the next
ideation prompt. Enforcement stays with the gates; the architect makes them
quiet, not redundant. Fail-open everywhere: an unparsed reply changes
nothing and never blocks growth."""
import json
import os
import re
import time

LINEAGE_RE = re.compile(
    r"_(v\d+|upgraded|enhanced|plus|improved|better|final|new)(\.py)?$", re.I)
THOUGHT_RE = re.compile(r"<(think|thinking|thought)>.*?</\1>", re.S | re.I)


def gather_evidence(own_dir, journal_path, now=None, days=14):
    """Deterministic library census: totals, 24h births, lineage variants,
    usage top/zero. Never raises; empty evidence on any filesystem trouble."""
    now = now or time.time()
    try:
        names = [n for n in os.listdir(own_dir) if not n.startswith('.')]
    except OSError:
        names = []
    day_new, lineage = [], []
    stems = {}
    for n in names:
        try:
            if now - os.path.getmtime(os.path.join(own_dir, n)) < 86400:
                day_new.append(n)
        except OSError:
            pass
        if LINEAGE_RE.search(n):
            lineage.append(n)
        elif not re.search(r"(\.bak|\.broken|\.tmp|^\.)", n):
            # extension twins are lineage too: DigestPlanner.py born next to
            # DigestPlanner (2026-08-04) -- same capability, new file, and
            # invisible to the suffix regex above.
            stems.setdefault(re.sub(r"\.(py|sh|bash|txt)$", "", n), []).append(n)
    for stem, group in stems.items():
        if len(group) > 1:
            lineage.extend(group)
    used = {}
    cutoff = now - days * 86400
    try:
        with open(journal_path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get('ts', 0) >= cutoff and e.get('kind') == 'exec_start':
                    for m in re.finditer(r'tools/own/([A-Za-z0-9_.\-]+)',
                                         e.get('content', '')):
                        used[m.group(1)] = used.get(m.group(1), 0) + 1
    except OSError:
        pass
    top = sorted(used.items(), key=lambda kv: -kv[1])[:10]
    zero = len([n for n in names if n not in used])
    return {"total": len(names), "born_24h": sorted(day_new)[:20],
            "lineage_variants": sorted(lineage)[:20],
            "lineage_count": len(lineage), "top_used": top,
            "zero_use_count": zero}


def build_prompt(items, ev):
    lines = []
    for i, it in enumerate(items, 1):
        g = it.get("gate")
        tag = (f" [gate: covered by {g[1]} -- an UPGRADE of {g[1]},"
               f" not a new file]" if g else " [gate: new]")
        lines.append(f"IDEA {i}: {it.get('title', '')} -- "
                     f"{str(it.get('brief', ''))[:160]}{tag}")
    top = ", ".join(f"{n}({c})" for n, c in ev.get("top_used", [])[:8])
    return f"""You are the meta-architect for an autonomous toolsmith agent. Its library has {ev['total']} tools; {ev['zero_use_count']} were unused in 14 days; {ev['lineage_count']} are lineage variants (files like X_upgraded or X_v2 spawned INSTEAD of editing X -- drift to stop). Most-used: {top or '-'}.
Born in the last 24h: {', '.join(ev['born_24h'][:12]) or '-'}.

Rule on each idea below.

Items tagged [gate: covered by X] have ALREADY been judged by the deduplication gate: the agent will receive them as a choice to UPGRADE X by editing that file in place -- never as a new sibling file. This is the library's depth work, so KEEP them by default and use your guidance line to say what X should gain. DROP a covered item only if X itself is not worth deepening (dead, unused, superseded by something better).

Items tagged [gate: new] are candidate NEW capabilities. KEEP the ones the library truly lacks -- guidance should prefer CHAINING existing tools over writing from scratch. DROP ones that duplicate capability the census shows it already has.

RESHAPE either kind only by rewriting the brief into something the library truly lacks.

{chr(10).join(lines)}

You may think first. Then END your reply with exactly this block, one decision line per idea, nothing after the block:

ARCHITECT:
IDEA 1: KEEP | <one line of guidance>
IDEA 2: DROP | <reason>
IDEA 3: RESHAPE | <replacement one-line brief>
DIRECTIVE: <one line steering the agent for the next 25 cycles>
WANTED: <capability 1>; <capability 2>; <capability 3>
"""


def parse_architect(raw, n):
    """Tolerant scan: (parsed_count, {idx: (VERB, tail)}, directive, wanted).
    Same philosophy as the batch judge's terminal-block contract."""
    raw = THOUGHT_RE.sub("", raw or "")
    decisions, directive, wanted, parsed = {}, "", [], 0
    for ln in raw.splitlines():
        s = ln.strip()
        m = re.match(r"[\s*#>\-]*(?:idea\s*)?(\d+)\s*[:.\)\-]\s*"
                     r"(KEEP|DROP|RESHAPE)\b[\s|:\-]*(.*)", s, re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < n and idx not in decisions:
                decisions[idx] = (m.group(2).upper(), m.group(3).strip()[:220])
                parsed += 1
            continue
        m = re.match(r"[\s*#>\-]*DIRECTIVE\s*[:\-]\s*(.+)", s, re.I)
        if m:
            directive = m.group(1).strip()[:300]
            continue
        m = re.match(r"[\s*#>\-]*WANTED\s*[:\-]\s*(.+)", s, re.I)
        if m:
            wanted = [w.strip()[:90] for w in m.group(1).split(";")
                      if w.strip()][:5]
    return parsed, decisions, directive, wanted


def apply_architect(items, decisions):
    """(kept_items, dropped_count). Fail-open: no decision -> KEEP unchanged.
    v1 known gap: a RESHAPEd brief sheds its gate tag ungated -- the
    architect just ruled it library-lacking; the done-gate still guards."""
    out, dropped = [], 0
    for i, it in enumerate(items):
        v, tail = decisions.get(i, ("KEEP", ""))
        if v == "DROP":
            dropped += 1
            continue
        if v == "RESHAPE" and tail:
            it = dict(it)
            it["brief"] = tail
            it.pop("gate", None)
        elif v == "KEEP" and tail:
            it = dict(it)
            it["brief"] = f"{it.get('brief', '')}\n[architect] {tail}"
        out.append(it)
    return out, dropped


async def run_architect(items, evidence, complete):
    """One call, fail-open. Returns (items, dropped, directive, wanted)."""
    if not items:
        return items, 0, "", []
    try:
        raw = await complete(build_prompt(items, evidence),
                             max_tokens=200 * len(items) + 600) or ""
    except Exception as e:
        print(f"[architect] call failed ({type(e).__name__}) -- fail-open, "
              f"batch unchanged")
        return items, 0, "", []
    parsed, dec, directive, wanted = parse_architect(raw, len(items))
    kept, dropped = apply_architect(items, dec)
    print(f"[architect] {parsed}/{len(items)} ruled: kept {len(kept)}, "
          f"dropped {dropped}"
          + ("; directive set" if directive else "")
          + (f"; wanted: {len(wanted)}" if wanted else ""))
    if parsed == 0 and raw:
        h = re.sub(r"\s+", " ", raw)[:110]
        print(f"[architect] UNPARSED head: '{h}'")
    return kept, dropped, directive, wanted
