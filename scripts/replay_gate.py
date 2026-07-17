#!/usr/bin/env python3
"""replay_gate.py -- behavioral regression for the idea gate.

Replays recently-born tools (their name + '# does:' line = the executed
conception) through the CURRENT gate and prints the verdict distribution.
This is the anti-contamination lesson made permanent: fixtures we author
reuse our own vocabulary; the creature's real output paraphrases. Judge
the gate against reality, not against ourselves.

Usage: python3 scripts/replay_gate.py [--days 3] [--llm]
  --llm also runs the one-call batch judge (costs quota; default off,
        deterministic stage only).
Approximation: each tool is judged against today's registry minus itself
and minus same-window births (conception-time registry is not recorded).
"""
import argparse, asyncio, os, re, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from executive import idea_gate as g

MIND = os.path.expanduser("~/growing-spine-mind")
OWN, ATTIC = os.path.join(MIND, "tools", "own"), os.path.join(MIND, "tools", "attic")

def desc(path):
    try:
        m = re.search(r"#\s*does:\s*(.+)", open(path, encoding="utf-8", errors="replace").read(3000))
        return m.group(1).strip() if m else ""
    except OSError:
        return ""

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=3)
    ap.add_argument("--llm", action="store_true")
    a = ap.parse_args()
    now = time.time()
    born = [n for n in os.listdir(OWN)
            if os.path.isfile(os.path.join(OWN, n)) and not n.startswith(".")
            and (now - os.path.getmtime(os.path.join(OWN, n))) / 86400 <= a.days]
    if not born:
        print(f"no tools born in the last {a.days} days"); return
    reg_full = g.build_registry(OWN)
    names_full = g.list_tool_names(OWN)
    areg, anames = g.build_registry(ATTIC), g.list_tool_names(ATTIC)
    bornset = set(born)
    caught, band = [], []
    for t in sorted(born):
        reg = {k: v for k, v in reg_full.items() if k != t and k not in bornset}
        names = [n for n in names_full if n != t and n not in bornset]
        text = f"{t}: {desc(os.path.join(OWN, t))}"
        v = g.deterministic_verdict(text, t, reg, names,
                                    attic_registry=areg, attic_names=anames,
                                    exclude_names=bornset)
        (caught if v else band).append((t, v))
    print(f"born last {a.days}d: {len(born)}   deterministic catches: {len(caught)}   to judgment band: {len(band)}")
    for t, v in caught:
        print(f"  CATCH {v['verdict']}:{v['target']}  <- {t}  [{v['method']}]")
    if a.llm and band:
        from keychain import Keychain
        kc = Keychain()
        if not kc.any_available():
            print("(--llm requested but all providers walled)")
            return
        reg = {k: v for k, v in reg_full.items() if k not in bornset}
        items = [{"title": t, "brief": desc(os.path.join(OWN, t))} for t, _ in band]
        verdicts = await g.batch_judge(items, reg, kc.complete, attic_registry=areg)
        for i, (t, _) in enumerate(band):
            if i in verdicts:
                print(f"  JUDGE {verdicts[i][0]}:{verdicts[i][1]}  <- {t}")
            else:
                print(f"  NEW/unparsed  <- {t}")

asyncio.run(main())
