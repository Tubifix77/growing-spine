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


def build_registry(tools_dir):
    reg = {}
    for name in sorted(os.listdir(tools_dir)):
        p = os.path.join(tools_dir, name)
        if os.path.isfile(p):
            d = extract_description(p)
            if d:
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


IDEA_GATE_PROMPT = """You are the idea gate for a self-building agent. Before it builds a new tool, decide whether an existing tool already covers the intent.

NEW IDEA (intent of the tool about to be built):
  {new_desc}

EXISTING TOOLS most related to it (name: what it does):
{candidates}

Judge by INTENT (the job done), not wording. Choose exactly one verdict:
- DUPLICATE:<tool>  an existing tool already does essentially this job.
- EXTEND:<tool>     an existing tool does MOST of this; the new idea is that tool plus a small delta. Prefer this over NEW whenever a close relative exists -- growing the existing tool beats spawning a near-twin.
- NEW               genuinely not covered by any listed tool.

Reply on TWO lines, exactly:
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


def _find_verdict(s):
    """DUPLICATE/EXTEND(+target) or NEW in a piece of text; None if absent."""
    m = _KIND_RE.search(s)
    if m:
        tgt = m.group(2)
        if tgt and tgt.lower() == "of":          # "EXTEND of tool_x" phrasing
            m2 = re.search(r"\bof\b\s+['\"`]?([A-Za-z0-9_\-.]{2,})", s[m.start():], re.IGNORECASE)
            tgt = m2.group(1) if m2 else None
        return m.group(1).upper(), tgt
    if re.search(r"\bNEW\b", s, re.IGNORECASE):
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
            got = _find_verdict(s)
            if got:
                verdict, target = got
                parsed = True
                if not reason:
                    reason = s[:160]
                break
    return {"verdict": verdict, "target": target, "reason": reason, "parsed": parsed}


async def assess_idea(new_desc, registry, complete, k=PREFILTER_K):
    """Route a newly-conceived idea. `complete`: async (prompt, max_tokens=) -> str."""
    new_desc = (new_desc or "").strip()[:DESC_CAP]
    cands = prefilter(new_desc, registry, k)
    if not cands:
        return {"verdict": "NEW", "target": None, "reason": "no related existing tool", "parsed": True, "candidates": []}
    prompt = IDEA_GATE_PROMPT.format(new_desc=new_desc, candidates=_format_candidates(cands))
    raw = (await complete(prompt, max_tokens=200)) or ""
    out = parse_verdict(raw)
    if not out.get("parsed"):
        out["reason"] = f"UNPARSED reply: {raw[:140]!r}"
    if out["target"] and out["target"] not in registry:
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
