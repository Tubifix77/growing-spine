#!/usr/bin/env python3
"""idea_gate.py -- conception-stage duplicate/extend gate. STANDALONE (not wired into loop.py yet).

Before a conceived idea becomes a tool to build, compare its short intent-
description against existing tools' descriptions and route it:
    NEW            -> nothing covers this; build it
    DUPLICATE:<t>  -> tool <t> already does this job; reuse it, don't build
    EXTEND:<t>     -> tool <t> covers MOST of it; add the delta to <t>, don't build new

Why this shape:
- The compared unit is a SHORT description (DESC_CAP), never the whole tool. It
  stays cheap to compare against many, and the cap forces stating the essence,
  so two similar ideas produce similar descriptions and collide honestly.
- A cheap keyword pre-filter (PREFILTER_K) narrows to plausibly-related ideas
  before the costly LLM judgment, so per-idea cost doesn't scale with toolkit size.
- "Same vs different" is interpretive and cannot be fully formalised, so the
  judgment is delegated to the LLM; this module only frames it and routes.
- `complete` is injected (async callable) so the gate is testable without the
  keychain and drops into loop.py by passing keychain.complete.
"""
from __future__ import annotations
import os, re
from . import embed_gate
from pathlib import Path

# Compared-against-everything layer, so keep it short (Claude Code caps skill
# descriptions for the same reason). ~240 chars ~= two sentences: enough to
# separate "answer from local archive" from "answer from live web", short
# enough to compare many cheaply.
DESC_CAP = 240
# Only the top-K plausibly-related ideas reach the judge, bounding cost.
PREFILTER_K = 8

_DOES_RE = re.compile(r"does:\s*(.+)", re.IGNORECASE)
_PLACEHOLDER = ("(no description)", "- edit this line", "todo", "placeholder")
_STOP = set("a an the to of and or for in on with by from into this that your you it is are be as at".split())


def extract_description(path):
    """A tool's short intent description from its does: line / first real
    docstring line, or '' if only a placeholder. Capped to DESC_CAP."""
    try:
        head = Path(path).read_text(errors="replace").splitlines()[:25]
    except Exception:
        return ""
    text = ""
    for ln in head:
        m = _DOES_RE.search(ln)
        if m:
            text = m.group(1).strip(); break
    if not text:
        for ln in head:
            s = ln.strip().lstrip("#").strip().strip('"').strip("'").strip()
            if s and not s.startswith(("!", "import", "from", "set -", "if ", "usage", "call:", "tool:")) and len(s) > 15:
                text = s; break
    low = text.lower()
    if not text or any(p in low for p in _PLACEHOLDER):
        return ""
    return text[:DESC_CAP].strip()


_JUNK_SUFFIXES = (".bak", ".tmp", ".swp")


def _is_junk(name, desc=None):
    if name.startswith(".") or name.endswith(_JUNK_SUFFIXES) or ".broken" in name:
        return True
    if desc and desc.upper().startswith("DESCRIBE WHAT THIS TOOL DOES"):
        return True
    return False


def build_registry(tools_dir):
    reg = {}
    try:
        names = sorted(os.listdir(tools_dir))
    except OSError:
        return reg
    for name in names:
        p = os.path.join(tools_dir, name)
        if os.path.isfile(p):
            d = extract_description(p)
            if d and not _is_junk(name, d):
                reg[name] = d
    return reg


def _keywords(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP}


def prefilter(new_desc, registry, k=PREFILTER_K):
    nk = _keywords(new_desc)
    scored = []
    for name, desc in registry.items():
        ov = len(nk & _keywords(desc))
        if ov:
            scored.append((ov, name, desc))
    scored.sort(reverse=True)
    return [(n, d) for _, n, d in scored[:k]]


def list_tool_names(tools_dir):
    """Every tool filename (with or without a description) -- for name collision."""
    try:
        return [n for n in os.listdir(tools_dir)
                if os.path.isfile(os.path.join(tools_dir, n)) and not _is_junk(n)]
    except OSError:
        return []


def _norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# Deterministic thresholds, set empirically against the live registry 2026-07-08:
# exact-dups scored J=0.73-1.0, the hardest judgment-call near-sibling 0.43,
# genuinely-new ideas <=0.06. 0.55 sits in the empty band above every observed
# judgment call and below every observed duplicate.
JACCARD_DUP = 0.55
NAME_MIN = 6          # normalized-name collisions shorter than this are noise


def _best_jaccard(nk, registry):
    best, best_name = 0.0, None
    for name, desc in registry.items():
        dk = _keywords(f"{name} {desc}")
        if not dk:
            continue
        j = len(nk & dk) / len(nk | dk)
        if j > best:
            best, best_name = j, name
    return best, best_name


def _refresh_embed_index():
    try:
        mind = os.environ.get("VOLUME_MOUNT", os.path.expanduser("~/growing-spine-mind"))
        embed_gate.refresh({"live": os.path.join(mind, "tools", "own"),
                            "attic": os.path.join(mind, "tools", "attic")})
    except Exception:
        pass


def _nearest_live(text, registry):
    """Embedding-nearest LIVE tool name (for attic->keeper remap)."""
    try:
        for full, _s in embed_gate.top_matches(text, k=12, labels={"live"}):
            n = full.split(":", 1)[1]
            if n in registry:
                return n
    except Exception:
        pass
    nk = _keywords(text)
    if nk:
        _j, name = _best_jaccard(nk, registry)
        return name
    return None


def deterministic_verdict(new_text, title, registry, all_names,
                          attic_registry=None, attic_names=None,
                          exclude_names=None):
    """Stage-0 gate: catch what needs no judgment, with zero LLM calls.
    The ATTIC (consolidated tools, out of the creature's view) serves as
    dedup memory: a hit there redirects to the covering live keeper, never
    to the unreachable attic tool. Returns a verdict dict or None."""
    nt = _norm_name(title)
    if len(nt) >= NAME_MIN:
        for name in all_names or ():
            if _norm_name(name) == nt:
                return {"verdict": "DUPLICATE", "target": name,
                        "reason": f"name collision: '{title}' normalizes to existing tool '{name}'",
                        "parsed": True, "method": "deterministic:name"}
    # --- semantic bands (v0.12): the layer lexical matching cannot be -------
    if embed_gate.available():
        _refresh_embed_index()
        top = embed_gate.top_matches(new_text, k=1, exclude=exclude_names)
        if top:
            full, sim = top[0]
            label, tname = full.split(":", 1)
            if sim >= embed_gate.SIM_DUP:
                if label == "attic" or tname not in registry:
                    keeper = _nearest_live(new_text, registry) or tname
                    return {"verdict": "DUPLICATE", "target": keeper,
                            "reason": (f"semantic duplicate of {'attic ' if label=='attic' else ''}"
                                       f"'{tname}' (cos={sim:.2f}); live coverage '{keeper}'"),
                            "parsed": True, "method": "deterministic:embed"}
                return {"verdict": "DUPLICATE", "target": tname,
                        "reason": f"semantic duplicate of '{tname}' (cos={sim:.2f})",
                        "parsed": True, "method": "deterministic:embed"}
            if sim < embed_gate.SIM_FLOOR:
                return {"verdict": "NEW", "target": None,
                        "reason": f"semantically unlike everything (best cos={sim:.2f} vs '{tname}')",
                        "parsed": True, "method": "deterministic:embed-floor"}
        # in the band: fall through to the LLM with embedding-ranked candidates
        return None
    nk = _keywords(new_text)
    if nk:
        best, best_name = _best_jaccard(nk, registry)
        if best >= JACCARD_DUP and best_name:
            return {"verdict": "DUPLICATE", "target": best_name,
                    "reason": f"deterministic overlap J={best:.2f} with '{best_name}'",
                    "parsed": True, "method": "deterministic:overlap"}
    # --- attic memory: was this job already consolidated away? -----------
    attic_hit = None
    if nt and len(nt) >= NAME_MIN:
        for name in attic_names or ():
            if _norm_name(name) == nt:
                attic_hit = ("name", name)
                break
    if attic_hit is None and nk and attic_registry:
        aj, aname = _best_jaccard(nk, attic_registry)
        if aj >= JACCARD_DUP and aname:
            attic_hit = (f"overlap J={aj:.2f}", aname)
    if attic_hit and registry:
        how, aname = attic_hit
        kj, keeper = _best_jaccard(nk or _keywords(title), registry)
        adesc = (attic_registry or {}).get(aname, "")
        akj, akeeper = _best_jaccard(_keywords(f"{aname} {adesc}"), registry)
        if akj > kj:
            kj, keeper = akj, akeeper
        if keeper:
            # A name-identical attic hit IS a duplicate -- the verdict states
            # the fact; only the redirect target depends on the mapping.
            v = "DUPLICATE" if (how == "name" or kj >= JACCARD_DUP) else "EXTEND"
            return {"verdict": v, "target": keeper,
                    "reason": (f"consolidated precedent: matches attic tool '{aname}' "
                               f"({how}); live coverage is '{keeper}' (J={kj:.2f})"),
                    "parsed": True, "method": "deterministic:attic"}
    return None


IDEA_GATE_PROMPT = """You are the idea gate for a self-building agent. Before it builds a new tool, decide whether an existing tool already covers the intent.

NEW IDEA (intent of the tool about to be built):
  {new_desc}

EXISTING TOOLS most related to it (name: what it does):
{candidates}

Judge by INTENT (the job done), not wording. Choose exactly one verdict:
- DUPLICATE:<tool>  an existing tool already does essentially this job.
- EXTEND:<tool>     an existing tool does MOST of this; the new idea is that tool plus a small delta. Prefer this over NEW whenever a close relative exists -- growing the existing tool beats spawning a near-twin.
- NEW               genuinely not covered by any listed tool.

Candidates marked [consolidated] are prior tools whose job is already covered by the live library: matching one of them means DUPLICATE, not NEW.

CRITICAL OUTPUT RULE: the VERY FIRST characters of your reply must be "VERDICT:". No thinking out loud, no restating the idea, no preamble of any kind -- replies that do not start with VERDICT: are discarded unread. Reason comes AFTER, on the second line.

VERDICT: <NEW | DUPLICATE:tool-name | EXTEND:tool-name>
REASON: <one sentence>
"""


def _format_candidates(cands):
    return "\n".join(f"  {n}: {d}" for n, d in cands) if cands else "  (none related)"


_MD_PREFIX = re.compile(r"^[\s#*\->`\u2022]+")
_KIND_RE = re.compile(
    r"\b(DUPLICATE|EXTEND)\b\s*(?:[:\-]|\bof\b)?\s*['\"`]?([A-Za-z0-9_\-.]{2,})?",
    re.IGNORECASE)


def _clean_line(ln):
    return _MD_PREFIX.sub("", ln).strip().strip("*`").strip()


def _find_verdict(s, labeled=True):
    """DUPLICATE/EXTEND(+target) or NEW in a piece of text; None if absent.
    labeled=False (free-prose fallback) is stricter: NEW only counts in
    UPPERCASE (narration says 'the new idea...' constantly), and
    DUPLICATE/EXTEND only count WITH a target."""
    m = _KIND_RE.search(s)
    if m:
        tgt = m.group(2)
        if tgt and tgt.lower() == "of":          # "EXTEND of tool_x" phrasing
            m2 = re.search(r"\bof\b\s+['\"`]?([A-Za-z0-9_\-.]{2,})", s[m.start():], re.IGNORECASE)
            tgt = m2.group(1) if m2 else None
        if labeled or tgt:
            return m.group(1).upper(), tgt
    if labeled and re.search(r"\bNEW\b", s, re.IGNORECASE):
        return "NEW", None
    if not labeled and re.search(r"\bNEW\b", s):     # uppercase only in prose
        return "NEW", None
    return None


def parse_verdict(raw):
    """Tolerant parse of the judge's reply. Accepts the strict two-line format,
    markdown-wrapped labels (**VERDICT:** ...), or -- as a fallback -- the
    verdict token anywhere in a non-menu line. parsed=False means no verdict
    token was found at all (caller fails open to NEW, visibly)."""
    verdict, target, reason, parsed = "NEW", None, "", False
    lines = [_clean_line(ln) for ln in (raw or "").splitlines()]
    for s in lines:
        u = s.upper()
        if u.startswith("VERDICT"):
            got = _find_verdict(s)
            if got:
                verdict, target = got
                parsed = True
        elif u.startswith("REASON"):
            reason = (s.split(":", 1)[1] if ":" in s else s[6:]).strip().strip("* ")
    if not parsed:
        for s in lines:
            if not s or "<tool" in s.lower():     # skip echoed option menu
                continue
            got = _find_verdict(s, labeled=False)
            if got:
                verdict, target = got
                parsed = True
                if not reason:
                    reason = s[:160]
                break
    return {"verdict": verdict, "target": target, "reason": reason, "parsed": parsed}


def _rank_candidates(new_desc, pool, registry, attic_registry, k):
    """Top-k candidates for the LLM judge: embedding-ranked when available
    (the calibration showed top-1 embedding targets are exactly the right
    family siblings), keyword-overlap otherwise."""
    if embed_gate.available():
        try:
            _refresh_embed_index()
            out = []
            for full, _s in embed_gate.top_matches(new_desc, k=k):
                label, name = full.split(":", 1)
                if label == "attic" and name in (attic_registry or {}):
                    out.append((f"{name} [consolidated]", attic_registry[name]))
                elif name in registry:
                    out.append((name, registry[name]))
            if out:
                return out
        except Exception:
            pass
    return prefilter(new_desc, pool, k)


async def assess_idea(new_desc, registry, complete, k=PREFILTER_K,
                      title=None, all_names=None,
                      attic_registry=None, attic_names=None):
    """Route a newly-conceived idea. `complete`: async (prompt, max_tokens=) -> str.
    Stage 0 is deterministic (name collision + high keyword overlap, no LLM);
    only the genuine judgment band reaches the LLM."""
    new_desc = (new_desc or "").strip()[:DESC_CAP]
    det = deterministic_verdict(new_desc, title or new_desc.split(":", 1)[0],
                                registry, all_names,
                                attic_registry=attic_registry,
                                attic_names=attic_names)
    if det is not None:
        det["candidates"] = []
        return det
    pool = dict(registry)
    attic_registry = attic_registry or {}
    for an, ad in attic_registry.items():
        pool.setdefault(f"{an} [consolidated]", ad)
    cands = _rank_candidates(new_desc, pool, registry, attic_registry, k)
    if not cands:
        return {"verdict": "NEW", "target": None, "reason": "no related existing tool", "parsed": True, "candidates": []}
    prompt = IDEA_GATE_PROMPT.format(new_desc=new_desc, candidates=_format_candidates(cands))
    raw = (await complete(prompt, max_tokens=300)) or ""
    out = parse_verdict(raw)
    if not out.get("parsed"):
        out["reason"] = f"UNPARSED reply: {raw[:140]!r}"
    if out["target"]:
        out["target"] = out["target"].replace("[consolidated]", "").strip()
    if out["target"] and out["target"] not in registry:
        if out["target"] in attic_registry:
            # precedent lives in the attic; redirect to the covering LIVE keeper
            keeper = _nearest_live(new_desc, registry)
            kj = 0.0
            if not keeper:
                nk = _keywords(new_desc)
                kj, keeper = _best_jaccard(nk, registry) if nk else (0.0, None)
            if keeper:
                out["reason"] = (f"matches consolidated tool '{out['target']}' (attic); "
                                 f"live coverage '{keeper}' (J={kj:.2f}) -- " + out.get("reason", ""))
                out["target"] = keeper
            else:
                out["verdict"] = "NEW"
                out["reason"] += " (attic precedent but no live keeper matched; treated as new)"
                out["target"] = None
        else:
            match = next((n for n in registry if out["target"] in n or n in out["target"]), None)
            out["target"] = match
            if not match:
                out["verdict"] = "NEW"; out["reason"] += " (named target not found; treated as new)"
    out["candidates"] = cands
    return out


if __name__ == "__main__":
    tools_dir = os.path.expanduser("~/growing-spine-mind/tools/own")
    reg = build_registry(tools_dir)
    print(f"registry: {len(reg)} tools with real descriptions\n")
    fixtures = [
        ("exact-dup of a research pipeline",
         "Answer a research question by searching the archive, filling knowledge gaps, synthesizing, and archiving the result.",
         "DUPLICATE/EXTEND of research_answer_pipeline*"),
        ("near-sibling: plan vs answer",
         "Produce a persistent research plan from keywords by searching and filling knowledge gaps.",
         "EXTEND/DUPLICATE of KeywordResearchPlanner"),
        ("genuinely new: thermal guard",
         "Monitor CPU temperature and pause heavy work if the machine overheats.",
         "NEW"),
    ]
    for label, desc, expected in fixtures:
        print(f"### {label}\n  new: {desc}\n  expect: {expected}\n  prefilter surfaced:")
        c = prefilter(desc, reg)
        if not c:
            print("    (nothing related -> would route NEW without an LLM call)")
        for n, d in c[:6]:
            print(f"    - {n}: {d[:64]}")
        print()


BATCH_JUDGE_PROMPT = """You are the idea gate for a self-building agent. For EACH numbered idea below, decide whether an existing tool already covers its intent. Judge by INTENT (the job done), not wording. Tools marked [consolidated] are prior art: matching one means DUPLICATE, not NEW.

{ideas_block}

You may think through the ideas first if you need to. Then you MUST end your reply with a final verdict block in EXACTLY this format -- one line per idea, every idea number exactly once, nothing after the block:

VERDICTS:
1: NEW
2: DUPLICATE:fetch_url
3: EXTEND:memstore

Allowed verdicts: NEW | DUPLICATE:tool-name | EXTEND:tool-name. A reply without the final VERDICTS block is invalid.
"""


def _resolve_batch_target(verdict, target, new_text, registry, attic_registry):
    """Same target discipline as assess_idea: strip tags, remap attic names to
    the covering live keeper, neutralise unknown targets to NEW."""
    if target:
        target = target.replace("[consolidated]", "").strip()
    if not target:
        return (verdict, None) if verdict == "NEW" else ("NEW", None)
    if target in registry:
        return verdict, target
    if attic_registry and target in attic_registry:
        keeper = _nearest_live(new_text, registry)
        if not keeper:
            nk = _keywords(new_text)
            kj, keeper = _best_jaccard(nk, registry)
            adesc = attic_registry.get(target, "")
            akj, akeeper = _best_jaccard(_keywords(f"{target} {adesc}"), registry)
            if akj > kj:
                keeper = akeeper
        if keeper:
            return verdict, keeper
        return "NEW", None
    match = next((n for n in registry if target in n or n in target), None)
    if match:
        return verdict, match
    return "NEW", None


def _scan_verdict_lines(raw, n_items):
    """Pure line-scan: (parsed_count, {idx: (VERDICT, raw_target)}).
    Tolerant of markdown junk, IDEA prefixes, and any amount of prose
    around the lines -- reasoning models put the block at the very end."""
    parsed, hits = 0, {}
    for ln in raw.splitlines():
        m = re.match(
            r"[\s*#>\-]*(?:idea\s*)?(\d+)[\s*]*[:.\)\-][\s*]*"
            r"(NEW|DUPLICATE|EXTEND)\s*(?:of\s+)?[:\-]?\s*['\"`]?"
            r"([A-Za-z0-9_\-.\[\] ]{2,})?",
            ln.strip(), re.IGNORECASE)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if not (0 <= idx < n_items):
            continue
        parsed += 1
        hits[idx] = (m.group(2).upper(), (m.group(3) or "").strip())
    return parsed, hits


async def batch_judge(items, registry, complete, attic_registry=None, per_idea_k=3):
    """ONE LLM call, verdicts for a whole ideation batch.
    items: list of dicts with title+brief. Returns {index: (verdict, target)}
    containing ONLY the ideas judged covered (DUPLICATE/EXTEND with a live
    target). Anything unparsed, unmatched, or judged NEW is simply absent --
    the caller treats absence as new (fail-open)."""
    if not items:
        return {}
    attic_registry = attic_registry or {}
    pool = dict(registry)
    for an, ad in attic_registry.items():
        pool.setdefault(f"{an} [consolidated]", ad)
    blocks = []
    for i, it in enumerate(items, 1):
        text = f"{it.get('title', '')}: {it.get('brief', '')}"[:DESC_CAP]
        cands = _rank_candidates(text, pool, registry, attic_registry, per_idea_k)
        rel = "; ".join(f"{n}: {d[:70]}" for n, d in cands) or "(none related)"
        blocks.append(f"IDEA {i}: {text}\n  RELATED: {rel}")
    prompt = BATCH_JUDGE_PROMPT.format(ideas_block="\n".join(blocks))
    # 30/idea starved chatty models: 4/4 live refills (Jul 15-16) burned the
    # whole budget on prose deliberation and truncated before verdict line 1.
    # A verdict line is ~12-18 tokens; 48/idea + 120 leaves ~3x slack so the
    # verdicts survive a stray preamble written despite the no-preamble rule.
    # Failure history: 30/idea starved chatty models (4/4 refills Jul 15-16).
    # 48/idea with a verdict-first, no-reasoning rule still parsed 0/8 live
    # (Jul 19): the reasoning model deliberated in prose and even CHOSE
    # verdicts, but never wrote IDEA-numbered lines -- verdict-first fights
    # how reasoning models generate. The contract now embraces deliberation
    # and requires a terminal VERDICTS block; 160/idea + 400 funds the musing.
    raw = (await complete(prompt, max_tokens=160 * len(items) + 400)) or ""
    # reasoning models wrap deliberation in <think> tags; strip before parsing
    # gemma-4 emits <thought>, others <think>/<thinking> -- strip all
    raw = re.sub(r"<(think|thinking|thought)>.*?</\1>", "", raw, flags=re.S | re.I)
    parsed_lines, hits = _scan_verdict_lines(raw, len(items))
    out = {}
    for idx, (v, raw_target) in hits.items():
        if v == "NEW":
            continue
        text = f"{items[idx].get('title', '')}: {items[idx].get('brief', '')}"
        v2, tgt = _resolve_batch_target(v, raw_target, text,
                                        registry, attic_registry)
        if v2 != "NEW" and tgt:
            out[idx] = (v2, tgt)
    print(f"[idea-gate] batch judge: {parsed_lines}/{len(items)} verdict lines parsed, "
          f"{len(out)} covered" + ("" if parsed_lines else
          f" -- UNPARSED reply head: {raw[:120]!r} tail: {raw[-120:]!r}"))
    return out
