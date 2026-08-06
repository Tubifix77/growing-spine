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
        from volume.tools import list_tools as _list_tools   # P2-F2
        names = _list_tools(own_dir)
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
            from volume.tools import tool_stem as _stem     # P2-F14
            stems.setdefault(_stem(n), []).append(n)
    for stem, group in stems.items():
        if len(group) > 1:
            lineage.extend(group)
    # The third copy of "what counts as use" used to live here: the same
    # `tools/own/` path-prefix regex as loop.py, over a 14-day journal window.
    # It could not see a bare invocation, and tools are on PATH -- so its
    # zero_use_count was inflated and its top_used disagreed with the catalogue
    # printed in the SAME prompt (audit P1-F5, P2-F3). Now the canonical merge.
    # Note the semantics changed with it: the counters are cumulative, so this is
    # "never used", not "unused in 14 days" -- the prompt says so.
    from volume import tools as toolmod
    _mind = os.path.dirname(os.path.dirname(own_dir))   # <mind>/tools/own -> <mind>
    # Normalise BOTH sides. demand_counts keys have the tool extension stripped
    # (tools are invoked bare off PATH), so matching them against raw filenames
    # silently drops every `foo.py` that has no extensionless twin -- which
    # inflated zero_use_count from 8 to 67 the day this census was unified.
    # Introduced 2026-08-06 by that unification and caught the same evening: a
    # normalisation mismatch between two halves of one comparison is the same
    # disease as two copies of a literal.
    from volume.tools import tool_stem as _stem
    own_stems = {_stem(n) for n in names}
    used = {k: v for k, v in toolmod.demand_counts(_mind).items()
            if k in own_stems}
    zero_names = [n for n in names if _stem(n) not in used]
    top = sorted(used.items(), key=lambda kv: -kv[1])[:10]
    zero = len(zero_names)
    return {"total": len(names), "born_24h": sorted(day_new)[:20],
            "lineage_variants": sorted(lineage)[:20],
            "lineage_count": len(lineage), "top_used": top,
            "zero_use_count": zero}


def build_prompt(items, ev):
    n = len(items)
    lines = []
    for i, it in enumerate(items, 1):
        g = it.get("gate")
        tag = (f" [gate: covered by {g[1]} -- an UPGRADE of {g[1]},"
               f" not a new file]" if g else " [gate: new]")
        lines.append(f"IDEA {i}: {it.get('title', '')} -- "
                     f"{str(it.get('brief', ''))[:160]}{tag}")
    top = ", ".join(f"{n}({c})" for n, c in ev.get("top_used", [])[:8])
    return f"""You are the meta-architect for an autonomous toolsmith agent. Its library has {ev['total']} tools; {ev['zero_use_count']} have never been used; {ev['lineage_count']} are lineage variants (files like X_upgraded or X_v2 spawned INSTEAD of editing X -- drift to stop). Most-used: {top or '-'}.
Born in the last 24h: {', '.join(ev['born_24h'][:12]) or '-'}.

Rule on each idea below.

Items tagged [gate: covered by X] have ALREADY been judged by the deduplication gate: the agent will receive them as a choice to UPGRADE X by editing that file in place -- never as a new sibling file. This is the library's depth work, so KEEP them unless X itself is not worth deepening (dead, unused, superseded by something better). A KEEP still needs its own line: the guidance on that line, naming what X should gain, is the whole value you add to a fork. Leaving a covered idea out of the block is NOT a keep -- it is a keep with no guidance at all, which wastes the ruling.

Items tagged [gate: new] are candidate NEW capabilities. KEEP the ones the library truly lacks -- guidance should prefer CHAINING existing tools over writing from scratch. DROP ones that duplicate capability the census shows it already has.

RESHAPE either kind only by rewriting the brief into something the library truly lacks.

{chr(10).join(lines)}

You may think first. Then END your reply with exactly this block: one decision line for EVERY idea, IDEA 1 through IDEA {n}, in order, nothing after the block. All {n} lines are required, covered and new alike.

ARCHITECT:
IDEA 1: KEEP | <one line of guidance>
IDEA 2: DROP | <reason>
IDEA 3: RESHAPE | <replacement one-line brief>
... one line per idea, continuing to IDEA {n}
DIRECTIVE: <one line steering the agent for the next 25 cycles>
WANTED: <capability 1>; <capability 2>; <capability 3>
"""


def parse_architect(raw, n):
    """Tolerant scan: (parsed_count, {idx: (VERB, tail)}, directive, wanted).
    Same philosophy as the batch judge's terminal-block contract."""
    raw = THOUGHT_RE.sub("", raw or "")
    decisions, directive, wanted = {}, "", []
    for ln in raw.splitlines():
        s = ln.strip()
        m = re.match(r"[\s*#>\-]*(?:idea\s*)?(\d+)\s*[:.\)\-]\s*"
                     r"(KEEP|DROP|RESHAPE)\b[\s|:\-]*(.*)", s, re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < n:
                # LAST wins. The prompt licenses thinking BEFORE the terminal
                # block, so first-wins let a deliberation line ("IDEA 3: KEEP or
                # DROP? let me check") beat the real ruling -- and its tail was
                # then injected into the brief as guidance to the creature. The
                # sibling judge chose last-wins for exactly this reason, and
                # DIRECTIVE/WANTED below were already last-wins.
                decisions[idx] = (m.group(2).upper(), m.group(3).strip()[:220])
            continue
        m = re.match(r"[\s*#>\-]*DIRECTIVE\s*[:\-]\s*(.+)", s, re.I)
        if m:
            directive = m.group(1).strip()[:300]
            continue
        m = re.match(r"[\s*#>\-]*WANTED\s*[:\-]\s*(.+)", s, re.I)
        if m:
            wanted = [w.strip()[:90] for w in m.group(1).split(";")
                      if w.strip()][:5]
    return len(decisions), decisions, directive, wanted


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


def _fmt_ruled(dec):
    """1-based ruled indices, compressed to runs ('1-3,7'). A leading run
    that stops short is the signature of a reply truncated mid-block;
    'none' or a scattered set means the block was never written properly."""
    idx = sorted(i + 1 for i in dec)
    if not idx:
        return "none"
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i == prev + 1:
            prev = i
            continue
        runs.append((start, prev))
        start = prev = i
    runs.append((start, prev))
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


async def run_architect(items, evidence, complete):
    """One call, fail-open. Returns (items, dropped, directive, wanted)."""
    if not items:
        return items, 0, "", []
    budget = 200 * len(items) + 600
    try:
        raw = await complete(build_prompt(items, evidence),
                             max_tokens=budget) or ""
    except Exception as e:
        print(f"[architect] call failed ({type(e).__name__}) -- fail-open, "
              f"batch unchanged")
        return items, 0, "", []
    parsed, dec, directive, wanted = parse_architect(raw, len(items))
    kept, dropped = apply_architect(items, dec)
    fail_open = len(items) - parsed
    print(f"[architect] {parsed}/{len(items)} ruled [{_fmt_ruled(dec)}]: "
          f"kept {len(kept)}"
          + (f" ({fail_open} fail-open)" if fail_open else "")
          + f", dropped {dropped}"
          + ("; directive set" if directive else "")
          + (f"; wanted: {len(wanted)}" if wanted else ""))
    if fail_open and raw:
        # A PARTIAL parse used to wear a victory costume: unruled ideas are
        # silent fail-open KEEPs, and the old diagnostic only spoke at 0/N.
        # Speak whenever anything went unruled, and give the two numbers that
        # separate the causes: reply length against the token budget (a reply
        # near 4*budget chars was cut off mid-block) plus the ruled-index run
        # above (a leading run = truncation, 'none' = no block at all).
        flat = re.sub(r"\s+", " ", raw)
        print(f"[architect] {fail_open} unruled -- reply {len(flat)} chars "
              f"vs budget {budget} tok; head: '{flat[:110]}'")
        print(f"[architect] ... tail: '{flat[-160:]}'")
    return kept, dropped, directive, wanted
