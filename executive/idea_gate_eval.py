#!/usr/bin/env python3
"""Controlled go/no-go for idea_gate: run fixtures through assess_idea against
the real keychain.  Run from repo root:  python3 -m executive.idea_gate_eval
Fail-fast if all providers are walled."""
import asyncio, os
from keychain import Keychain
from executive import idea_gate

FIXTURES = [
    ("rename-dup (deterministic, no LLM)",
     "Wake Answer Generator: Generate an answer to a user question using fresh wake-up news",
     ("DUPLICATE",)),
    ("exact-dup research pipeline",
     "Answer a research question by searching the archive, filling knowledge gaps, synthesizing, and archiving the result.",
     ("DUPLICATE", "EXTEND")),
    ("near-sibling: plan vs answer",
     "Produce a persistent research plan from keywords by searching and filling knowledge gaps.",
     ("DUPLICATE", "EXTEND")),
    ("genuinely new: thermal guard",
     "Monitor CPU temperature and pause heavy work if the machine overheats.",
     ("NEW",)),
]

async def main():
    kc = Keychain()
    if not kc.any_available():
        print("NO-GO(cannot test): all providers walled. Re-run when quota returns.")
        return
    reg = idea_gate.build_registry(os.path.expanduser("~/growing-spine-mind/tools/own"))
    attic_reg = idea_gate.build_registry(os.path.expanduser("~/growing-spine-mind/tools/attic"))
    attic_names = idea_gate.list_tool_names(os.path.expanduser("~/growing-spine-mind/tools/attic"))
    names = idea_gate.list_tool_names(os.path.expanduser("~/growing-spine-mind/tools/own"))
    print(f"registry: {len(reg)} live + {len(attic_reg)} attic\n")
    passed = 0
    for label, desc, expected in FIXTURES:
        r = await idea_gate.assess_idea(desc, reg, kc.complete,
                                        title=desc.split(":", 1)[0],
                                        all_names=names,
                                        attic_registry=attic_reg,
                                        attic_names=attic_names)
        ok = r["verdict"] in expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        print(f"    verdict={r['verdict']} target={r.get('target')} expected={expected}")
        print(f"    reason={r.get('reason','')}\n")
    verdict = "GO" if passed == len(FIXTURES) else "REVIEW"
    print(f"=== {passed}/{len(FIXTURES)} judged as expected -> {verdict} ===")

if __name__ == "__main__":
    asyncio.run(main())
