#!/usr/bin/env python3
"""Regenerate docs/framework-map.html: the interactive framework map with
every LLM prompt embedded VERBATIM (constants imported live; function-built
prompts rendered with sample inputs). Run from the repo root after any
prompt change:  python3 scripts/build_framework_map.py"""
import html
import json
import sys
import time

sys.path.insert(0, ".")
P = {}
BLANK = []          # a prompt panel that came back empty. The creature's own
                    # prompt files live on /mind, which only the host machine
                    # has -- so building this map anywhere else renders those
                    # panels as "the creature has written nothing", which is a
                    # different claim entirely and indistinguishable by eye.


def put(key, val, note="", may_be_empty=False):
    text = val if isinstance(val, str) else str(val)
    if not text.strip() and not may_be_empty:
        BLANK.append(key)
        text = ("&lt;NOT READABLE FROM THIS MACHINE -- this text lives on the "
                "creature's volume. Rebuild the map on the host that carries "
                "/mind.&gt;")
    P[key] = {"text": text, "note": note}


from executive import loop as L            # noqa: E402
from executive import idea_gate as G       # noqa: E402
from executive import architect as A       # noqa: E402

put("system_protected", L._load_protected_prompt(),
    "loaded from file; not creature-editable")
put("system_editable", L._load_editable_prompt(),
    "loaded from file; the creature may edit this part of its own mind")
put("composition_single", L._COMPOSITION_PROMPT)
try:
    put("composition_batch",
        L._composition_batch_prompt(10, "<HORIZON: HN titles, wiki randoms, "
                                        "'wanted by the architect' lines appear here>"),
        "rendered with n=10 and a placeholder horizon block")
except Exception as e:
    put("composition_batch", f"<render failed: {e}>")
put("gap_prompt", L._GAP_PROMPT)
put("basin_check", L._BASIN_CHECK_PROMPT)
put("classify_category", L._CLASSIFY_CATEGORY_PROMPT)
put("retro", L._RETRO_PROMPT)
try:
    d = L._gate_choice_spec("DUPLICATE", "example_tool", "the part it lacks")
    e2 = L._gate_choice_spec("EXTEND", "example_tool", "the part it lacks")
    put("gate_choice", "== DUPLICATE variant ==\n" + d["brief"]
        + "\n\nDemonstration required:\n" + d["demonstration"]
        + "\n\n== EXTEND variant ==\n" + e2["brief"],
        "creature-facing fork text, rendered for target 'example_tool'")
except Exception as e:
    put("gate_choice", f"<render failed: {e}>")
put("batch_judge", G.BATCH_JUDGE_PROMPT)
try:
    items = [{"title": "AutoNewsDigest", "brief": "digest today's news into memory",
              "gate": ("DUPLICATE", "continuous_news_to_memory")},
             {"title": "TimelineView", "brief": "render archived events on a timeline"}]
    ev = {"total": 348, "zero_use_count": 120, "lineage_count": 14,
          "top_used": [("knowledge_gap_filler", 43), ("archive_backed_query", 39)],
          "born_24h": ["feed_timeline_generator", "news_alert_task_generator"],
          "lineage_variants": ["subagent_summarize_archive_v2"]}
    put("architect", A.build_prompt(items, ev),
        "rendered with 2 sample ideas + a sample evidence pack")
except Exception as e:
    put("architect", f"<render failed: {e}>")

def esc(s):
    return html.escape(s or "", quote=True)


UNRESOLVED = []     # a symbol lookup that MISSED. Never let one pass quietly:
                    # a bare path where a line number was expected reads exactly
                    # like a node nobody gave a symbol to, so the map goes on
                    # looking healthy while it says less than it used to.


def loc(path, symbol=None):
    """File reference with the line resolved LIVE. Hardcoded line numbers in
    this map went stale within days of every commit; a symbol lookup cannot."""
    if not symbol:
        return path
    UNRESOLVED.append((path, symbol))   # popped below if the lookup lands
    try:
        with open(path, encoding="utf-8") as f:
            wanted = (symbol, "async " + symbol)
            for i, line in enumerate(f, 1):
                st = line.strip()
                if line.startswith(wanted) or st.startswith(wanted):
                    UNRESOLVED.pop()
                    return f"{path}:{i}"
    except OSError:
        pass
    return path


def fw_verbs():
    """The built-in verbs, read live from framework-tools/ with their own
    one-line descriptions, so a new built-in appears here without an edit."""
    import os
    d = "framework-tools"
    out = []
    try:
        for name in sorted(os.listdir(d)):
            fp = os.path.join(d, name)
            if name.startswith(".") or not os.path.isfile(fp):
                continue
            out.append(f"{name} -- {L_first_doc(fp)}")
    except OSError:
        pass
    return out


def L_first_doc(fp):
    try:
        from volume import tools as VT
        return VT._first_doc_line(fp)
    except Exception:
        return "(no description)"


NODES = [
 ("wake","a1","mech","Wake / Sleep","10s between cycles; 2-min retry when quota-walled",loc("executive/runtime.py","def wake_entry"),
  "The heartbeat. Wakes, checks provider availability via the keychain, runs one cycle, sleeps. Quota exhaustion is normal: long idle stretches are the free tier working as designed. Current tempo (2026-08-05, post-outage): 38-46 thinks/hour against a 17.8/h baseline on Aug 1 -- thinking got cheap when the wake context was put on a diet. The sleep line it writes (`Earliest budget return: <time>`) was FICTION until 2026-08-06: it read `last_window_duration`, a key nothing has ever written, so it always fell through to a flat hour -- and printed that hour to the creature as fact. It now reads the measured `last_recovery_secs` (shortest on record: 183s). Same day, raising the think cap from 2048 to 3072 cut exec_skip from 14.9% to 3.0% at unchanged throughput: 28% of thinks were ending on the ceiling and the contract puts the executable block LAST, so a truncated reply lost the whole action. <br><br><b>Corrected 2026-09-21:</b> the cadence was never two minutes. The loop breathes <code>asyncio.sleep(10)</code> between cycles; the 120s figure is the retry after a quota wall, and the longer gaps are <code>sleep_entry</code>. Tempo has fallen with the ladder rather than with the loop: <b>17.1 thinks/hour</b> over 50.3h on 2026-09-21 against the 38-46/h recorded here in August, because <b>55% of think_starts now find no rung at all</b> and sleep. A declared floor of 15/h is checked hourly by <code>spine_health.check_throughput</code>, which fired for the first time on 2026-09-16 at 12-13/h.",None),
 ("wake","a2","world","Context assembly","layers + directive + chat + curated catalogue",loc("executive/loop.py","def _build_context"),
  "Builds the creature's entire view of the world each wake: the two-part system prompt (protected constitution + a small creature-editable section), layered working memory (FOCUS leads), any active Reviewer/architect directive, unread chat from Tue, and the tool catalogue. Since 2026-08-04 the catalogue is CURATED, not complete: ~2,480 tokens where the full listing had grown to 11,082, which alone made a wake context too fat for some provider windows to accept.","system_protected"),
 ("wake","a2b","world","Self-editable prompt","the creature's own words to itself","editable-prompt.md (on /mind)",
  "A small section of its own system prompt the creature is allowed to edit. Its current contents:","system_editable"),
 ("wake","a2c","mech","Curated catalogue v2","70 slots, five sections, honest tail",loc("executive/loop.py","def _build_tool_catalogue"),
  "Tue's design: built-ins verbatim + 6 most-used + 12 focus-relevant (by embedding) + 10 born-or-edited-in-7-days + least-recently-shown fill to CATALOGUE_TOOL_BUDGET=70 + a truthful 'and N more' tail. Rotation state lives at /mind/state/tool_last_surfaced.json. Cadence caveat measured 2026-08-05: at ~46 wakes/hour the whole 354-tool library cycles through in about five wakes, not the ~45 days the design assumed -- the anti-basin guarantee is over-satisfied, and the creature never sees the same catalogue twice. NEVER call this function to inspect the catalogue: it ends in _mark_surfaced() and writes rotation state.",None),
 ("wake","a3","llm","THINK","one completion via the keychain",loc("keychain/keychain.py","def complete") or "keychain/",
  "The whole assembled context goes to whichever provider window is open (see Keychain). The reply is the creature's thought for this cycle. google_gemma serves ~70-82% of answered thinks -- which is exactly why its silent death for 59.6 hours (Aug 2-4) nearly stopped the creature dead while every dashboard looked fine.",None),
 ("wake","a4","mech","Bash extraction","```bash blocks or exec_skip",loc("executive/parser.py","def parse_bash_blocks"),
  "Only fenced bash blocks become action. A think with no block is an exec_skip - the objective quality proxy we measure models by (big three ~20%, gemma 33%, gpt-oss 48%). Live skip rate is also a health signal in its own right: 46% on Aug 1, 32% on Aug 4, 16% on Aug 5 after the fork-target and reviewer fixes. <br><br><b>2026-09-21:</b> 22 skips against 1,098 exec blocks, and the aggregate is no longer the useful number &mdash; <b>split it by the rung that served the cycle</b>. Live: google_gemma 1.6%, cloudflare 0.0%, gemini_flash 27.8%. The total looked healthy all through the week that openrouter_super was skipping <b>97.3%</b> of the cycles it served, because a thousand clean gemma cycles drown it. Two distinct diseases hide under one word: <i>no bash block at all</i> (format non-compliance, a clean complete reply with no command in it) and <i>truncation</i> (the reply hit the token ceiling before the block, which the contract puts last).",None),
 ("wake","a5","world","EXEC in the body","docker container, /mind mounted","volume/",
  "Commands run inside the mortal body container as the host user. Tools live at /mind/tools/own; the framework layer at /mind/tools/framework; the attic keeps every retired tool, reversibly. The body is disposable and respawned by ensure_body -- the mind on the volume is what persists.",None),
 ("wake","a5a","world","The built-in verbs","framework-tools/, re-materialised every wake",loc("volume/tools.py","def materialize_framework"),
  "The hardcoded layer: the only verbs that exist before the creature builds anything. Canonical on the host in framework-tools/ and copied over /mind/tools/framework on EVERY wake, overwriting -- so a framework tool the creature writes itself does not survive two minutes, while anything in tools/own does. The full live list:<br><br>" + "<br>".join("&nbsp;&nbsp;<code>" + esc(v.split(" -- ")[0]) + "</code> &mdash; "
            + esc(v.split(" -- ", 1)[1] if " -- " in v else "") for v in fw_verbs()) + "<br><br>tool-edit (2026-08-05) is the newest and the one that had been missing longest: see the Gate-choice FORK node.",None),
 ("wake","a5b","world","tool-find (the librarian)","semantic search over its own library","framework-tools/tool-find + " + loc("executive/toolfind.py","def answer"),
  "The creature's on-demand pull channel (2026-08-03, Tue's design): tool-find 'what you need' writes a request onto /mind/state, a host watcher answers in under a second from the gate's own live embedding index -- one geometry, no LLM, no new body packages. The constitution teaches it as the move when UNSURE what you own (uncertainty-triggered, deliberately not a pre-build ritual -- the gate already guards building); the catalogue header advertises it every wake. Adoption is trending from name lookups toward genuine by-meaning queries.",None),
 ("wake","a5c","mech","The observation channel","what a command's output looks like coming back",loc("executive/loop.py","def _capped"),
  "<b>Everything the creature learns about the world arrives through this, and for the first fifteen months it was 300 characters wide.</b> An exec result is capped when it is written to the journal and capped AGAIN when the journal is rendered into the next wake, so its whole view of any command was ~286 characters &mdash; with no marker, so a 4KB <code>cat</code> looked complete. That manufactured rational-looking repetition: a 14-day census found 127 repeat streaks, 102 of them with capped output, and <b>44 where the loop warning&rsquo;s claim of an identical result was simply false</b>. It tried base64, python and <code>cat $(which ...)</code> to widen a pipe that does not widen, called the ban a trap in its own reasoning, and stalled for three cycles.<br><br>Three invariants came out of it, each held by test. <b>Truncation must announce itself wherever it cuts</b> &mdash; one marker, named constants shared by writer, render and warning. <b>A marker reports the TOTAL characters not shown; a later cut may only increase that number, never replace it with its own</b> &mdash; the first fix shipped a nested cut that showed <code>+40 chars cut</code> where 3,319 characters were withheld, which is worse than no marker at all, because a small number reads as reassurance. And <b>a detector must not count what truncation destroyed</b>: a capped command is identity-unknown and is never counted as a repeat.<br><br>The window itself was never a decision &mdash; <code>git log -S</code> traces 300 back to the v0.4 SKELETON commit. Three revisions of the MESSAGE moved nothing; the creature read the marker correctly and still asked for 100 lines in 63 of 69 cases, because the ceiling is stated in characters and it asks in lines. Raised to <b>1,200</b> against a census of 1,387 results (median 1,776 chars): whole-result fit 27.3% &rarr; 45.6%, capped share 71.8% &rarr; 43%, and the read sizes finally moved. <b>It had a second edge nobody baselined:</b> a 17.5% fatter context tripled reply truncation, ~4% &rarr; ~12%, for eighteen days. A context-size change has two edges, and the one you are not watching is the one that moves.",None),
 ("wake","a6","gate","DONE-GATE suite","five checks before a completion counts",loc("executive/loop.py","def _enforce_done_gate"),
  "The law layer. Blocks: (1) hollow completions - the tool is still a tool-new placeholder; (2) completions on top of an abandoned-stub backlog; (3) false completions (claims contradicted by failing checks); (4) since Aug 2: gate-choice UPGRADEs where the chosen target file is unchanged - a spawned sibling does not count (escape for honest go-new: remember gate-choice-new). Every block message teaches the fix. Aug 4-5 caveat worth remembering: check (3) was firing correctly nine times a day on a creature that had no way to edit a file in place, so a correct gate can still be the visible half of someone else&rsquo;s bug. <br><br><b>A fifth check since 2026-08-19:</b> <code>cannot_start</code> &mdash; a completion is refused if a tool written this cycle cannot start at all. The test is STATIC and never executes the tool (these tools write to the volume and call providers): an interpreter line the kernel can act on, a body its declared interpreter can parse, the execute bit. It is scoped to THIS cycle deliberately, because a library-wide block is a trap the creature cannot exit while a tool it wrote sixty seconds ago is always still fixable. <br><br><b>And since 2026-09-10 each block is journalled as a FIELD</b> (<code>guard</code> / <code>block</code>: false_completion, cannot_start, upgrade_no_change, empty_placeholder, hollow_backlog) rather than being recognised downstream by its prose. Seven producers and one consumer had been sharing three string literals with no test binding any pair; a single drifted literal would have told the retro judge there were zero done-gate blocks in a window that had 139. Consumers fall back to prose only when the field is absent.",None),
 ("wake","a6b","mech","Startability feedback","the fault made visible where it was made",loc("executive/loop.py","def _build_broken_tool_warning"),
  "An LLM writing an executable file produces three recurring corruptions and <b>none of them is a logic error</b>: backslash-escaped triple quotes surviving a shell layer, Unicode look-alikes (a typographic non-breaking hyphen sitting inside an identifier), and the tool header written without its <code>#</code>. Nothing validated a tool file at the moment it was written, and a census found 10 of 485 tools that could not start at all. Two surfaces now say so, both built on the ONE canonical predicate in <code>volume/tools.py</code>: <code>tool-edit</code> warns on stderr at write time (a WARNING, never a refusal &mdash; the file is saved exactly as given and the exit stays 0), and the loop names the set in-context, <b>edge-triggered on the set changing</b> and silent otherwise, because a fact repeated every cycle is a nag it learns to skip. It worked without anyone being asked: the creature repaired its own tools, and the unstartable count has fallen from 32 to 20.<br><br><b>The sharpest lesson here is about the MESSAGE, not the check.</b> The predicate said <i>no #! line</i> about a file that had one &mdash; on line 3, under a comment the creature had written &mdash; so it obeyed exactly, adding a shebang below the comment <b>ten times in five minutes</b>, drawing the identical false message each time, and destroying a working 3,626-byte tool on the way. A diagnostic that is literally false about the file it describes gets obeyed to the letter, forever. Before shipping a message about an artifact, check the message against the artifact: <i>no #! line</i> was one <code>head -3</code> away from being known false.",None),
 ("wake","a7","llm","Completion classifier","category + coverage bump",loc("executive/loop.py","def _classify_completion_category"),
  "After a genuine completion, one small LLM call classifies the built tool's category and updates the coverage map that ideation reads.","classify_category"),
 ("wake","a8","mech","Retro tick","counts real cycles -> Reviewer",loc("executive/loop.py","def _maybe_retrospective"),
  "Every substantive cycle advances the retrospective counter and ticks down any active directive. At RETRO_INTERVAL it triggers the Reviewer (Meta lane).",None),
 ("idea","b1","mech","Pop / idea-hunger","composition mode drains the queue",loc("executive/loop.py","def _oracle_next_spec"),
  "When the oracle assigns composition work it pops the idea queue. An empty queue triggers a full refill - the pipeline below. Queue drain rate measured Aug 5: roughly one item per 85 minutes.",None),
 ("idea","b2","world","Horizon sparks","HN + wiki + architect wanted-list",loc("executive/loop.py","def _refill_composition_queue"),
  "Live top-HN titles, random Wikipedia pages, journal-mined 48h friction, and (since Aug 1) 'wanted by the architect' lines - the diet that shapes what the creature imagines. The domain census shows it generalized past this diet: it built its own DuckDuckGo search, Google News, BBC and Yahoo fetchers.",None),
 ("idea","b3","llm","Composition batch prompt","fresh ideas in ONE call",loc("executive/loop.py","def _composition_batch_prompt"),
  "One call generates the whole batch of tool-chaining ideas against the CURRENT toolkit and coverage map, horizon attached.","composition_batch"),
 ("idea","b4","gate","Deterministic embed bands","cos >= 0.75 DUP | < 0.45 NEW | band -> judge",loc("executive/embed_gate.py","def top_matches"),
  "Zero-token layer: potion-base-8M embeddings over own+attic (index at /mind/state). Name collisions and paraphrase-duplicates die here for free. Honest replay acceptance: 15/53 deterministic + 38 to the judge band (the 39/48 first reported was a replay self-match artifact, fixed with the exclude parameter). Since 2026-08-05 the 'is this file even a tool?' question has ONE canonical answer here (embed_gate.JUNK_RE); it previously existed in three copies that disagreed, so birth accidents stayed in the index and the catalogue for days after tool-find had stopped recommending them.",None),
 ("idea","b5","llm","Batch judge","the fat band, one call",loc("executive/idea_gate.py","BATCH_JUDGE_PROMPT"),
  "Judges every band idea in one call. History: four straight 0-parse refills (token starvation), then 0/8 despite visibly choosing verdicts in prose - reasoning models cannot obey verdict-first. The contract now embraces deliberation and requires a terminal VERDICTS block; 5/5, 8/8, 7/7 clean followed. NOT cured, though: on 2026-08-05 a 7-item batch came back 0/7 with the head/tail dump showing it still deliberating ('We used: 1 DUPLICATE') at the cut -- the truncation disease returns on larger batches, and those seven ideas failed open to NEW. Open item.","batch_judge"),
 ("idea","b6","mech","Regen round","one capped retry, fed the rejections",loc("executive/loop.py","def _refill_composition_queue"),
  "If too few ideas survive, ONE regeneration round runs with the rejected jobs named - then the pipeline proceeds with whatever exists. The drive wall must never starve the queue.",None),
 ("idea","b7","llm","META-ARCHITECT v1","KEEP | DROP | RESHAPE + directive + wanted",loc("executive/architect.py","def run_architect"),
  "Tue's design (Aug 1): one evidence-fed ruling call per refill over the gate survivors - library census, 14-day usage histogram, lineage-variant drift. Its first two runs dropped EVERY fork, so fix B (Aug 4) told it covered ideas are upgrade candidates 'kept by default' -- and it then ruled only 3 of 17, because 'by default' reads as licence to omit the line. 14 keeps were silent fail-open abstentions wearing a victory costume. Two fixes followed: diagnostics that print the fail-open count and the ruled-index run (a leading run means truncation, 'none' means no block, a short run means compliance), and wording that says a KEEP still costs a line because the guidance IS the value. First refill after: 15/15 ruled [1-15], kept 8, dropped 7 -- the wording was the cause, confirmed in one refill.","architect"),
 ("idea","b8","gate","Gate-choice FORK","covered pop -> a real choice",loc("executive/loop.py","def _gate_choice_spec"),
  "When a popped idea is covered, the creature receives a gate fact and a bounded choice: UPGRADE the existing tool by editing it IN PLACE (a new file will NOT count as done - enforced by the done-gate), or drop it and hunt something genuinely new. Announced in Tue's voice on Jul 30; the creature replied it would 'upgrade rather than duplicate effort'. It then had NO VERB to do that with for six days: tool-new refuses to overwrite, no built-in edited an existing file, and the constitution documented only tool-new. It reached for apply_patch ~1,685 times and tool-edit ~140 times -- verbs real in its training corpus, absent from this world -- and never once wrote one itself, because 'command not found' is indistinguishable from a typo, `cat > path` always rescued the episode, and none of its 170 durable memories recorded the lesson. tool-edit shipped 2026-08-05 and was announced in Tue's voice. Also fixed here: _fork_target_ok() now validates the target at USE, since gate tags freeze into the queue at refill time and rot -- one pointed at a birth accident that could not be invoked at all.","gate_choice"),
 ("idea","b9","llm","Single-idea gate (FUSED)","batch-of-one since 0ea37bf",loc("executive/idea_gate.py","def assess_idea"),
  "The gap-path and pop-time gate. Until Aug 2 this was the batch judge's divergent twin - it kept the verdict-first contract after the batch path was cured, so it 0-parse fail-opened on reasoning windows. Now its LLM leg IS batch_judge with a batch of one: one prompt, one parser, one contract, and every future fix propagates to both callers. 3,675 bytes of dead twin amputated.","batch_judge"),
 ("idea","b10","llm","Gap assignment","cousin-tool gaps",loc("executive/loop.py","_GAP_PROMPT"),
  "Between refills, the oracle can assign a cousin-tool gap: a briefing that names an under-covered category next to tools it already has.","gap_prompt"),
 ("meta","c1","llm","The REVIEWER (retro)","PROGRESSING | STUCK + directive",loc("executive/loop.py","_RETRO_PROMPT"),
  "Every RETRO_INTERVAL real cycles, a stateless judge reads a metrics digest and rules on the TRAJECTORY. STUCK clears the project, resets self-concept, and sets a timed directive. History of it going wrong: it saved the creature from the 59h/39-STUCK basin in Part 5; on Aug 2 it became the strangler, thrashing a healthy creature with 7 resets in 16h because its metrics could not see in-place consolidation. That Aug-2 fix COMPUTED edited_existing_6h and never emitted it into the digest, so for three days the prompt asked the judge to credit consolidation while showing it no number. Worse, each STUCK fire cleared the project, the creature set a new one, and the next window counted that as a project switch: the reviewer manufactured the evidence for its own next verdict, five times in one night. Fixed 2026-08-05: the digest emits the in-place-edit count, attributes forced clears explicitly, and a STUCK verdict now logs the digest it saw (PROGRESSING always did; the failing case logged nothing). Result: resets fell from 5-in-7h to 3-in-8.6h with eight PROGRESSING verdicts where there had been none. 2026-08-06 closed the last two holes in it: the judge still ran the VERDICT-FIRST contract this codebase had already proved dead on reasoning windows -- it now invites prose and requires a terminal VERDICT: block, and the parser takes the LAST verdict line, so a judge that muses 'this could look STUCK' and then rules PROGRESSING is read correctly. And the in-place-edit number it judges by was a bare recent-mtime count over the whole tools dir: every edit is `mv X X.bak` then rewrite X, so ONE edit produced TWO entries, and births inflated the very metric added to detect sibling-spawn drift. Live at the time of the fix: 11 became 6.","retro"),
 ("meta","c2","gate","Spin trap","same failing command x5 -> abandon",loc("executive/loop.py","SPIN_THRESHOLD"),
  "Per-decision counterpart to the Reviewer: five consecutive done-gate blocks on the same failing command abandons the project instead of looping forever. Fired twice on Aug 5, both times on a creature trying to use a patch tool that did not exist.",None),
 ("meta","c3","mech","Aging shells","placeholder-only files attic after 3 days",loc("scripts/spine_health.py","def stub_janitor"),
  "Any tool file still containing only its birth placeholder after 3 days moves to the attic automatically, like fallen leaves. Real tools - anything with actual code and a purpose line - are never touched by this.",None),
 ("meta","c4","llm","Basin check","is this the same project again?",loc("executive/loop.py","_BASIN_CHECK_PROMPT"),
  "A small judge that detects when a 'new' project is the same basin as the retired one. (Ledgered: an LLM doing math's job - candidate for replacement by an embed cosine.)","basin_check"),
 ("meta","c5","mech","KEYCHAIN","5 rungs, fail-open default, upward re-probe","keychain/",
  "Priority-ordered free-tier ladder. <b>Live 2026-09-21, five enabled rungs:</b> gemini_flash &rarr; groq_oss120 &rarr; google_gemma (14,400/day, the workhorse) &rarr; cloudflare (Workers AI; one wake-sized call costs ~388 neurons against a 10,000/day allowance, so ~26 calls/day &mdash; a floor rung) &rarr; mistral (allowance is MONTHLY, left enabled so it returns on its own). <b>Three rungs have been retired since this map was first drawn</b>, each the moment it was detected and none of them a decision anyone had to weigh: <code>groq</code> on 2026-08-17, the day Groq withdrew llama-3.3-70b-versatile; <code>cerebras</code> on 2026-08-26, when the account was migrated to PayGo and answered HTTP 402 payment_required to ~1,200 re-probes over 8.4 days &mdash; behind a paywall is DEFUNCT for a free-tier-only system, not merely dark; <code>openrouter_super</code> on 2026-09-17 under the quality floor, after two models emitted no command in 54-68% of the cycles they served. Upward re-probe unchanged: an exhausted provider past a 10-min cooldown competes at its priority again, so a low rung never locks out a smarter one.<br><br><b>classify_error taxonomy:</b> too_large / retryable / quota / gone / flaky / hard &mdash; and <b>since c1b93a5 the DEFAULT is no longer <code>hard</code></b>. An unrecognised error now routes to the next rung, does not wall the account, and announces itself once with its text. That is the single most load-bearing line in the ladder. It was written after mistral&rsquo;s spent monthly allowance answered <code>HTTP 402 {&quot;detail&quot;:&quot;Check your subscription...&quot;}</code> &mdash; no <i>quota</i>, no <i>billing</i>, no <i>exceeded</i>, no 429 &mdash; and fell through to a default that RAISED, aborting the whole chain and killing <b>651 cycles in one day</b> with four rungs sitting open. The fail-open default has since handed us four more unenumerated shapes intact rather than as an outage: HTTP 499 client-closed, Cloudflare 520-527, an HTTP 200 with an empty body, and RemoteDisconnected (which carries no status code at all). <b>Adding a rung means adding its EXHAUSTION SIGNATURE, not just its key</b> &mdash; headers give you the ceiling and say nothing about what the provider returns once the allowance is gone. Timestamps-only quota tracking; there is still NO token accounting anywhere in runtime code. <b>Rung count and concentration are OUTCOMES, not targets:</b> free tier only, permanently, so a ladder carrying 90% on one rung is what the tier gives, not a fault to fix.",None),
 ("meta","c5b","mech","Truncation escalation","a cut-off reply is a failure, not a success",loc("keychain/keychain.py","TRUNCATION_ESCALATE_MAX"),
  "A reply that hits the token ceiling comes back <code>finish=length</code>, and the contract puts the executable block LAST &mdash; so a truncated reply loses the whole action and becomes an <code>exec_skip</code>. For a year that went through <code>record_success</code>: the call succeeded, the rung was never walled, and <b>a rung that truncated every reply looked healthy forever while the fatter rung below it was never reached by escalation</b>. Since b27070f it escalates instead. Three properties, all tested: the truncating rung is <b>not walled</b> (the call succeeded and the account is healthy); if every attempted rung truncates it <b>degrades to the longest partial</b>, which is exactly the old behaviour; and it is bounded by a declared <code>TRUNCATION_ESCALATE_MAX = 2</code>, never by the rung count, because throughput is the binding constraint.<br><br>The alternative &mdash; raising the 3,072-token think ceiling &mdash; was rejected on measurement, and the measurement is the part worth keeping: after the context raise the median reply grew 25% while the p90 more than doubled, so the tail stretched rather than the distribution shifting, and <b>a truncated reply tells you nothing about how long it wanted to be</b>, so no ceiling value is derivable from the journal at all. Picking one would have been a voodoo constant.<br><br><b>The escalation is also the instrument.</b> <code>served_by</code> carries <code>escalated=N</code> only when it happened, so <code>escalated=</code> together with <code>finish=stop</code> means a later rung FINISHED what the first could not. It read 0 for its first two days because there was no second rung to reach &mdash; the instrument blocked by the scarcity it was built to measure around. By 2026-09-19 it read 8, and the ceiling question was closed on evidence instead of being deferred a fourth time.",None),
 ("meta","c6","mech","Sensors","daily health, hourly flatline + throughput, weekly tier","scripts/",
  "spine_health.py (06:30 UTC + boot catch-up, retries the boot race) and openrouter_tier_check.py (Fridays 06:45 UTC: diffs the free-model shelf, flags vanished rungs loudly, surfaced as the tier chip on the observer). <br><br><b>Four checks have been added since, and every one exists because a fault was found by a human looking rather than by an instrument:</b> <code>check_throughput</code> (hourly, because a 6h window read once at 06:30 would have missed the whole 651-cycle outage &mdash; thinks/hour against a DECLARED floor of 15, taken over the span that produced records rather than wall clock, so a box switched off overnight is not a collapse); <code>check_unmet_demand</code> (daily; a missing calendar day breaks the streak, because absence of evidence must never read as a zero); <code>loop._record_wake_cost</code> (edge-triggered at a declared 5,000ms budget, after a quadratic dependency scan cost 28.3s of every wake and was found only because Tue could HEAR the fan); and <code>check_compounding</code> (daily &mdash; edges per tool, the depth distribution, and the cohort of tools born this week, which is the only half that can move before a 700-tool average does). <b>Every one of these reports to us and to Tue, never to the creature.</b>",None),
 ("meta","c7","gate","FLATLINE sensor","hourly: which rung has gone quiet?","scripts/spine_flatline_hourly.py",
  "Born from the incident it would have caught: google_gemma, serving 82% of all thinks, died silently on Aug 2 at 10:47 UTC and was not noticed for 59.6 hours -- nothing was broken, no error was raised, a provider simply stopped answering and the ladder quietly fell to its lower rungs. Now every hour at :07 the sensor names any provider whose last success has aged past its threshold, appended to ~/spine-health.log. It arbitrates recurrence, which is why the outage's root cause was allowed to stay open rather than relitigated. Its own first scheduled fire was misread as a dead timer, because a timer that has not fired yet shows LAST: - just like a broken one.",None),
 ("meta","c8","world","CHAT channel","world-facts only, Tue's voice","chat.jsonl",
  "The only voice from outside: plain statements of changed world-facts, never requests, never bug-pointing. Rule changes are announced (birth purposes, the gate fork, tool-edit); input changes are not (the fetcher going real). The creature replies here - and keeps its promises. On Jul 8 Tue offered to install packages for it and retracted the offer in the next message: 'it goes against what you are.' The tool-edit announcement (Aug 5) was sent because the day's own finding was that ambient information does not land -- 1,685 attempts at a missing verb and not one line written down, so a new entry in a long catalogue cannot outweigh that prior. It read and replied in 87 seconds. <br><br><b>Measured 2026-09-21, and it revises what this channel is for.</b> Three chat interventions exist in the whole project, and they split cleanly by what the framework did ALONGSIDE the message, not by how well the message was written. Announcing a capability the framework had just BUILT (<code>ask</code>, 08-14): 79 uses in August &rarr; 160 in September, <b>adopted</b>. Correcting a belief with nothing new framework-side: <b>failed twice</b> &mdash; told about a broken helper on 08-07 it agreed and kept using the broken path, and told on 09-20 that <code>git-save</code> was repaired it answered <i>&quot;Got it&quot;</i> within a minute and then made <b>zero calls across 317 cycles and 67 authoring actions</b>. So a chat message is an <b>accelerant for something the framework already carries, and worthless as the carrier itself</b>; if the only available fix is a chat message, there is no fix yet. Two framework changes followed. The exchange is now journalled (<code>chat_from_tue</code> / <code>chat_reply</code>, deliberately outside MEANINGFUL_KINDS) so a fact told to the creature is findable in the record the creature can search &mdash; the git-save correction lived only in chat.jsonl, which nothing it runs can read, while the journal still held 402 failures teaching the false belief. And the block now states the one-shot contract plainly: the message is shown ONCE, nothing repeats it, a reply is not storage. That is making an existing fact legible, not adding a rule &mdash; <code>chat_block</code> is built only while a message is unread, so it always was one-shot and the creature had no way to see that.",None),
]

kinds = {"llm": ("#b388ff", "LLM call"), "gate": ("#FFB74D", "GATE"),
         "world": ("#64B5F6", "creature-facing"), "mech": ("#9E9E9E", "mechanism")}
lanes = [("wake", "The Wake Cycle", "one heartbeat, ~10s apart when a rung is open"),
         ("idea", "The Idea Pipeline", "fires at refill / pop"),
         ("meta", "Meta &amp; Immune", "the organs that watch the whole")]


boxes = {k: [] for k, _, _ in lanes}
for lane, nid, kind, title, sub, loc, role, pk in NODES:
    color, klabel = kinds[kind]
    boxes[lane].append(
        f'<div class="node k-{kind}" data-id="{nid}"><span class="tag" '
        f'style="color:{color};border-color:{color}">{klabel}</span>'
        f'<div class="t">{esc(title)}</div><div class="s">{esc(sub)}</div></div>')

cols = ""
for key, name, hint in lanes:
    inner = '<div class="arrow">&#8595;</div>'.join(boxes[key])
    cols += f'<div class="lane"><h2>{name}<span>{hint}</span></h2>{inner}</div>'

meta = {nid: {"title": t, "kind": k, "loc": loc, "role": role,
              "prompt": (P.get(pk, {}).get("text") if pk else None),
              "pnote": (P.get(pk, {}).get("note") if pk else "")}
        for _, nid, k, t, _, loc, role, pk in NODES}
data = json.dumps(meta).replace("</", "<\\/")
stamp = time.strftime("%Y-%m-%d")

page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Growing Spine - Framework Map</title><style>
body{{margin:0;background:#12121a;color:#E0E0E0;font:14px/1.45 system-ui,sans-serif}}
header{{padding:18px 26px;border-bottom:1px solid #2a2a38}}
h1{{margin:0;font-size:19px}} h1 em{{color:#4CAF50;font-style:normal}}
.legend{{margin-top:6px;font-size:12px;color:#999}}
.legend b{{font-weight:600;margin-right:14px}}
main{{display:flex;gap:22px;padding:22px 26px;align-items:flex-start}}
.lane{{flex:1;min-width:0}}
.lane h2{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#8a8aa0;margin:0 0 10px}}
.lane h2 span{{display:block;letter-spacing:0;text-transform:none;color:#555;font-weight:400;margin-top:2px}}
.node{{background:#1e1e2e;border:1px solid #333;border-left:3px solid #555;border-radius:8px;
 padding:9px 12px;cursor:pointer;transition:transform .08s,box-shadow .08s}}
.node:hover{{transform:translateY(-1px);box-shadow:0 3px 14px #0009}}
.node .t{{font-weight:600;margin-top:2px}} .node .s{{font-size:12px;color:#9a9ab0}}
.tag{{font-size:10px;border:1px solid;border-radius:4px;padding:0 5px;letter-spacing:.06em}}
.k-llm{{border-left-color:#b388ff}} .k-gate{{border-left-color:#FFB74D}}
.k-world{{border-left-color:#64B5F6}} .k-mech{{border-left-color:#9E9E9E}}
.arrow{{text-align:center;color:#444;font-size:15px;line-height:1.5}}
#drawer{{position:fixed;top:0;right:-52%;width:50%;height:100%;background:#181824;
 border-left:1px solid #333;box-shadow:-8px 0 30px #000a;transition:right .18s;overflow:auto;padding:22px}}
#drawer.open{{right:0}}
#drawer h3{{margin:0 0 2px}} #drawer .loc{{font-family:monospace;font-size:12px;color:#4CAF50}}
#drawer .role{{margin:12px 0;color:#c9c9da}}
#drawer pre{{background:#0d0d14;border:1px solid #2a2a38;border-radius:8px;padding:14px;
 white-space:pre-wrap;word-wrap:break-word;font:12px/1.5 monospace;color:#d7d7e8}}
#drawer .pnote{{font-size:12px;color:#FFB74D;margin-bottom:6px}}
#close{{float:right;cursor:pointer;color:#888;font-size:20px}}
footer{{padding:14px 26px;color:#555;font-size:12px;border-top:1px solid #2a2a38}}
</style></head><body>
<header><h1>Growing Spine <em>Framework Map</em> - regenerated {stamp}</h1>
<div class="legend"><b style="color:#b388ff">&#9632; LLM call</b><b style="color:#FFB74D">&#9670; GATE</b>
<b style="color:#64B5F6">&#9632; creature-facing</b><b style="color:#9E9E9E">&#9632; mechanism</b>
&nbsp;click any box for its function, file and the verbatim prompt</div></header>
<main>{cols}</main>
<div id="drawer"><span id="close">&#10005;</span><div id="body"></div></div>
<script type="application/json" id="data">{data}</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const dr=document.getElementById('drawer'),bd=document.getElementById('body');
document.querySelectorAll('.node').forEach(n=>n.onclick=()=>{{
 const m=D[n.dataset.id];if(!m)return;
 let h=`<h3>${{m.title}}</h3><div class="loc">${{m.loc}}</div><div class="role">${{m.role}}</div>`;
 if(m.prompt){{if(m.pnote)h+=`<div class="pnote">${{m.pnote}}</div>`;
  h+=`<pre>${{m.prompt.replace(/&/g,'&amp;').replace(/</g,'&lt;')}}</pre>`;}}
 bd.innerHTML=h;dr.classList.add('open');}});
document.getElementById('close').onclick=()=>dr.classList.remove('open');
document.addEventListener('keydown',e=>{{if(e.key==='Escape')dr.classList.remove('open')}});
</script>
<footer>Every prompt shown is extracted verbatim from the running code (function-built prompts rendered with sample inputs). Gates in orange are where ideas and completions are tested; the creature never sees this page.</footer>
</body></html>"""
open("docs/framework-map.html", "w", encoding="utf-8").write(page)
print(f"framework map regenerated: {len(page)} bytes, {len(NODES)} nodes")
if BLANK:
    print(f"\nEMPTY PROMPT PANELS ({len(BLANK)}): {', '.join(BLANK)}. These read "
          f"from the creature's volume and this machine has none, so the map now "
          f"says so out loud instead of showing an empty box. Rebuild on the host.")
if UNRESOLVED:
    print(f"\nUNRESOLVED SYMBOLS ({len(UNRESOLVED)}) -- each node now carries a bare "
          f"path and says less than it used to. Find where these moved:")
    for _path, _symbol in UNRESOLVED:
        print(f"  {_path}  ::  {_symbol}")
    raise SystemExit(1)
if BLANK:
    raise SystemExit(1)
print(f"all {len(NODES)} nodes rendered; every symbol lookup resolved, "
      f"every prompt panel non-empty")
