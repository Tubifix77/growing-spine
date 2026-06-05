# Growing Spine — Part 5 Handover

## Where we are

Live AI creature experiment. Creature runs in Docker on Debian laptop (boas@192.168.0.77). Seventh consciousness experiment. Live since 2026-06-03.

**Repo:** https://github.com/Tubifix77/growing-spine  
**Local:** D:\\Projects\\growing-spine  
**Transcript of Part 4:** (this session)

---

## Processes

```bash
bash ~/restart-creature.sh
bash ~/start-observer.sh
```

After reboot: wait 2-3 min for network, then run both. restart-creature.sh polls DNS up to 30x/5s.

---

## Commits landed in Part 4

| Commit | What |
|--------|------|
| 44b0e63 | Memory tab redesign — QTreeWidget, collapsible, expansion state preserved |
| 07b520b | Keep discovered_limit across resets as experienced ceiling |
| da7540a | Quota display — discovered_limit only, FRESH/RUNNING/OK/LOW/EXHAUSTED |
| cd7c108 | Probe-based reset detection — retry real prompt, record interval |
| e28264b | Only stamp exhausted_at + discovered_limit on first wall hit |
| 4a2dbb3 | Clear exhausted_at on rollover; only update discovered_limit when current_used >= prev |
| 92d7774 | Remove think_end truncation; _first_doc_line prefers does: line |
| 2f93a15 | Tool doc confusion — protected-prompt clarified, tool-new template fixed |
| 5978e33 | Probe was never reaching API — removed any_available() gate |
| d1d776a | Adaptive sleep based on discovered_reset_interval (+20% buffer, 60s floor) |
| e194802 | probe_mode bypass in complete(); per-minute 429 vs daily quota distinguished |
| 51f4c57 | OOM fix — Docker 1g limit, 30s cycle sleep, 60s DNS error sleep |
| c24fc78 | git safe.directory='*' set at container init |
| c9f3568 | --replace-all to override baked image git config |

---

## Crashes in Part 4

1. **Steam thermal crash** — Steam WebHelper eating 60%+ CPU on boot drove temps to 80C. Close Steam when running creature on this hardware.
2. **OOM from doc-tools runaway** — creature's bash tool iterated /mind/tools/own/* including .git with hundreds of objects, spawning hundreds of bash subprocesses. Fixed: Docker 1g cap, doc-tools patched to skip dotfiles, slower retry loops.

---

## Current creature state

- Named itself **GrowthAgent**
- **20 memory entries:** purpose, growth metrics, tool_doc_status, iris_dataset, next_steps, git-safe-config, tool descriptions, birth date
- **Own tools built:** explore-env, list-workspace, list-workspace-contents, manage-workspace, research-log, doc-tools, generate_tool_docs
- **Workspace files:** README.md, TOOL_INDEX.md, Tool-Documentation.md, custom-tools.md, ai_wiki.html, linux_wiki.html, growth_experiment.py, hello.py, research.log
- **Editable prompt:** still template text — never written to by creature
- **git-save:** was failing all session with dubious ownership — fixed at end, creature has not experienced fix yet
- **list-workspace:** header-only file, no code — creature knows, hasn't fixed
- **list-workspace-contents:** empty file — same

---

## Quota state at Part 4 end

- **Gemini:** 93/92, exhausted, resets 2026-06-06 07:00 UTC
- **Groq:** 109812 tokens used, resets 2026-06-06 00:00 UTC, no interval measured yet
- **Cerebras:** 135338/135337, exhausted, discovered_reset_interval=71s, resets 2026-06-06 00:00 UTC

Creature sleeping, probing every ~85s (71s * 1.2).

---

## Quota system design (fully implemented)

- Push until 429 -> discovered_limit written on first wall hit only
- Probe = real next prompt retried. First success -> discovered_reset_interval recorded
- exhausted_at cleared on rollover; discovered_limit persists across resets
- Per-minute rate limits distinguished from daily quota (rpm/per_minute in error text)
- Adaptive sleep: min(intervals) * 1.2, floor 60s, fallback 3600s
- Display: used/discovered_limit, reset as "waited X / last known Y"

---

## Observer GUI — current tab state

- **Journal** — live log, double-click to expand. Good.
- **Memory** — tree-style, collapsible sections, detail panel. Good.
- **Container** — workspace file browser. Good.
- **Quota** — provider cards, x/y, FRESH/RUNNING/OK/LOW/EXHAUSTED, reset interval. Good.
- **Chat** — untested.

---

## Pending for Part 5

1. Watch creature discover git-save works — first test of fix
2. Editable prompt still template — nudge via chat if no progress after a few cycles
3. list-workspace and list-workspace-contents still broken — creature's job to fix
4. Measure Groq reset interval (not yet discovered)
5. Chat tab testing
6. Architecture doc in repo
7. Consider temperature monitoring in observer (was hitting 80C during Steam incident)

---

## LLM simulation technique (key discovery this session)

Roleplay as the LLM receiving the context, walk code line by line. Define BVA scenarios first, simulate each boundary. Found: gate logic blocking probes, per-minute vs daily 429 confusion, tool doc competing instructions, exhausted_at measurement errors, probe_mode not bypassing complete() gate. Unit tests would never catch these — they are misinterpretation bugs not logic bugs.

---

## Key helper scripts on laptop

- `~/restart-creature.sh` — DNS-aware wait, kills main.py, restarts detached
- `~/start-observer.sh` — kills observer.py, restarts detached

---

## Repo structure

```
growing-spine/
├── main.py
├── config.yaml
├── protected-prompt.md          — clarified tool doc instructions
├── HANDOVER-part5.md            — this file
├── executive/
│   ├── loop.py                  — probe-mode, 30s cycle sleep, DNS error 60s sleep
│   ├── runtime.py               — adaptive sleep interval, auto-remember on sleep
│   ├── sandbox.py               — 1g memory cap, 1.5 CPU, git safe.directory init
│   ├── journal.py
│   └── chat.py
├── keychain/
│   ├── keychain.py              — probe_mode, per-minute vs daily 429
│   ├── quota_state.py           — discovered_limit persists, exhausted_at cleared on rollover
│   └── quota_state.json
├── volume/
│   ├── memory.py
│   ├── tools.py                 — does: / # does: extraction
│   └── savegame.py
├── framework-tools/
│   └── (remember recall memories log-read tools tool-new git-save check-persistence)
└── observer.py                  — 5 tabs, memory tab tree-style QTreeWidget
```
