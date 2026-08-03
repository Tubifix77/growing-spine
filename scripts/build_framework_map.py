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


def put(key, val, note=""):
    P[key] = {"text": val if isinstance(val, str) else str(val), "note": note}


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

NODES = [
 ("wake","a1","mech","Wake / Sleep","2-min cadence; sleeps through quota walls","executive/loop.py (runtime)",
  "The heartbeat. Wakes, checks provider availability via the keychain, runs one cycle, sleeps. Quota exhaustion is normal: long idle stretches are the free tier working as designed.",None),
 ("wake","a2","world","Context assembly","layers + directive + chat + tools","executive/loop.py:193-200",
  "Builds the creature's entire view of the world each wake: the two-part system prompt (protected constitution + a small creature-editable section), layered working memory (FOCUS leads), any active Reviewer/architect directive, unread chat from Tue, and the tools listing.","system_protected"),
 ("wake","a2b","world","Self-editable prompt","the creature's own words to itself","prompt file on /mind",
  "A small section of its own system prompt the creature is allowed to edit. Its current contents:","system_editable"),
 ("wake","a3","llm","THINK","one completion via the keychain","keychain.complete()",
  "The whole assembled context goes to whichever provider window is open (see Keychain). The reply is the creature's thought for this cycle. Gemma-31b currently serves ~82% of thinks.",None),
 ("wake","a4","mech","Bash extraction","```bash blocks or exec_skip","executive/loop.py",
  "Only fenced bash blocks become action. A think with no block is an exec_skip - the objective quality proxy we measure models by (big three ~20%, gemma 33%, gpt-oss 48%).",None),
 ("wake","a5","world","EXEC in the body","docker container, /mind mounted","volume/",
  "Commands run inside the mortal body container as the host user. Tools live at /mind/tools/own; the framework layer at /mind/tools/framework; the attic keeps every retired tool, reversibly.",None),
 ("wake","a5b","world","tool-find (the librarian)","semantic search over its own library","framework-tools/tool-find + executive/toolfind.py",
  "The creature's on-demand pull channel (2026-08-03, Tue's design): tool-find 'what you need' writes a request onto /mind/state, a host watcher answers in under a second from the gate's own live embedding index -- one geometry, no LLM, no new body packages. The constitution teaches it as the move when UNSURE what you own (uncertainty-triggered, deliberately not a pre-build ritual -- the gate already guards building); the catalogue header advertises it every wake.",None),
 ("wake","a6","gate","DONE-GATE suite","four checks before a completion counts","executive/loop.py:~1935-2075",
  "The law layer. Blocks: (1) hollow completions - the tool is still a tool-new placeholder; (2) completions on top of an abandoned-stub backlog; (3) false completions (claims contradicted by failing checks); (4) since Aug 2: gate-choice UPGRADEs where the chosen target file is unchanged - a spawned sibling does not count (escape for honest go-new: remember gate-choice-new). Every block message teaches the fix.",None),
 ("wake","a7","llm","Completion classifier","category + coverage bump","executive/loop.py:472",
  "After a genuine completion, one small LLM call classifies the built tool's category and updates the coverage map that ideation reads.","classify_category"),
 ("wake","a8","mech","Retro tick","counts real cycles -> Reviewer","executive/loop.py:2340+",
  "Every substantive cycle advances the retrospective counter and ticks down any active directive. At RETRO_INTERVAL it triggers the Reviewer (Meta lane).",None),
 ("idea","b1","mech","Pop / idea-hunger","composition mode drains the queue","executive/loop.py",
  "When the oracle assigns composition work it pops the idea queue. An empty queue triggers a full refill - the pipeline below.",None),
 ("idea","b2","world","Horizon sparks","HN + wiki + architect wanted-list","executive/loop.py:719-760",
  "Live top-HN titles, random Wikipedia pages, journal-mined 48h friction, and (since Aug 1) 'wanted by the architect' lines - the diet that shapes what the creature imagines. The domain census shows it generalized past this diet: it built its own DuckDuckGo search, Google News, BBC and Yahoo fetchers.",None),
 ("idea","b3","llm","Composition batch prompt","10 fresh ideas in ONE call","executive/loop.py:764",
  "One call generates the whole batch of tool-chaining ideas against the CURRENT toolkit and coverage map, horizon attached.","composition_batch"),
 ("idea","b4","gate","Deterministic embed bands","cos >= 0.75 DUP | < 0.45 NEW | band -> judge","executive/embed_gate.py",
  "Zero-token layer: potion-base-8M embeddings over own+attic (index at /mind/state). Name collisions and paraphrase-duplicates die here for free. Honest replay acceptance: 15/53 deterministic + 38 to the judge band (the 39/48 first reported was a replay self-match artifact, fixed with the exclude parameter).",None),
 ("idea","b5","llm","Batch judge","the fat band, one call","executive/idea_gate.py",
  "Judges every band idea in one call. History: four straight 0-parse refills (token starvation), then 0/8 despite visibly choosing verdicts in prose - reasoning models cannot obey verdict-first. The contract now embraces deliberation and requires a terminal VERDICTS block; since then 5/5, 8/8, 7/7 clean, failures fail open.","batch_judge"),
 ("idea","b6","mech","Regen round","one capped retry, fed the rejections","executive/loop.py:944-965",
  "If too few ideas survive, ONE regeneration round runs with the rejected jobs named - then the pipeline proceeds with whatever exists. The drive wall must never starve the queue.",None),
 ("idea","b7","llm","META-ARCHITECT v1","KEEP | DROP | RESHAPE + directive + wanted","executive/architect.py",
  "Tue's design (Aug 1): one evidence-fed ruling call per refill over the gate survivors - library census, 14-day usage histogram, lineage-variant drift. Gate-covered ideas are presented to it as UPGRADE candidates, not duplicates to delete -- its first two runs dropped every fork until the prompt said so (fix B, 2026-08-04). KEEPs carry build guidance into the brief; its DIRECTIVE speaks through the Reviewer slot for 25 cycles; its WANTED list feeds the next horizon. Fail-open: an unparsed reply changes nothing.","architect"),
 ("idea","b8","gate","Gate-choice FORK","covered pop -> a real choice","executive/loop.py:1373",
  "When a popped idea is covered, the creature receives a gate fact and a bounded choice: UPGRADE the existing tool by editing it IN PLACE (a new file will NOT count as done - enforced by the done-gate), or drop it and hunt something genuinely new. Announced in Tue's voice on Jul 30; the creature replied it would 'upgrade rather than duplicate effort'.","gate_choice"),
 ("idea","b9","llm","Single-idea gate (FUSED)","batch-of-one since 0ea37bf","executive/idea_gate.py: assess_idea",
  "The gap-path and pop-time gate. Until Aug 2 this was the batch judge's divergent twin - it kept the verdict-first contract after the batch path was cured, so it 0-parse fail-opened on reasoning windows. Now its LLM leg IS batch_judge with a batch of one: one prompt, one parser, one contract, and every future fix propagates to both callers. 3,675 bytes of dead twin amputated.","batch_judge"),
 ("idea","b10","llm","Gap assignment","cousin-tool gaps","executive/loop.py:1075",
  "Between refills, the oracle can assign a cousin-tool gap: a briefing that names an under-covered category next to tools it already has.","gap_prompt"),
 ("meta","c1","llm","The REVIEWER (retro)","PROGRESSING | STUCK + directive","executive/loop.py:2301",
  "Every RETRO_INTERVAL real cycles, a stateless judge reads a metrics digest and rules on the TRAJECTORY. STUCK clears the project, resets self-concept, and sets a timed directive. History: saved the creature from the 59h/39-STUCK basin in Part 5; on Aug 2 it became the strangler - its metrics could not see in-place consolidation and it thrashed a healthy creature with 7 resets in 16h. Now the digest carries an edited-in-place count and the prompt declares consolidation first-class progress.","retro"),
 ("meta","c2","gate","Spin trap","same failing command x5 -> abandon","executive/loop.py:338",
  "Per-decision counterpart to the Reviewer: five consecutive done-gate blocks on the same failing command abandons the project instead of looping forever.",None),
 ("meta","c3","mech","Aging shells","placeholder-only files attic after 3 days","volume/tools.py",
  "Any tool file still containing only its birth placeholder after 3 days moves to the attic automatically, like fallen leaves. Real tools - anything with actual code and a purpose line - are never touched by this.",None),
 ("meta","c4","llm","Basin check","is this the same project again?","executive/loop.py:1499",
  "A small judge that detects when a 'new' project is the same basin as the retired one. (Ledgered: an LLM doing math's job - candidate for replacement by an embed cosine.)","basin_check"),
 ("meta","c5","mech","KEYCHAIN","9 windows, 5 families, upward re-probe","keychain/",
  "Priority-ordered free-tier ladder: gemini -> groq(llama70b) -> groq(gpt-oss-120b) -> cerebras -> google gemma-31b (14,400/day) -> OR: super-120b -> ling-flash -> north-code -> nemotron-30b. Upward re-probe: an exhausted provider past a 10-min cooldown competes at its priority again, so a low rung never locks out a smarter one. classify_error taxonomy: too_large / retryable / quota (incl. dead model ids) / flaky (empty completions and timeouts hop to the next provider) / hard. Timestamps-only quota tracking.",None),
 ("meta","c6","mech","Sensors","spine-health daily, tier-check weekly","scripts/",
  "spine_health.py (06:30 UTC + boot catch-up, retries the boot race) and openrouter_tier_check.py (Fridays: diffs the free-model shelf, flags vanished rungs loudly, surfaced as the tier chip on the observer).",None),
 ("meta","c7","world","CHAT channel","world-facts only, Tue's voice","chat.jsonl",
  "The only voice from outside: plain statements of changed world-facts, never requests, never bug-pointing. Rule changes are announced (birth purposes, the gate fork); input changes are not (the fetcher going real). The creature replies here - and keeps its promises.",None),
]

kinds = {"llm": ("#b388ff", "LLM call"), "gate": ("#FFB74D", "GATE"),
         "world": ("#64B5F6", "creature-facing"), "mech": ("#9E9E9E", "mechanism")}
lanes = [("wake", "The Wake Cycle", "one heartbeat, every ~2 minutes"),
         ("idea", "The Idea Pipeline", "fires at refill / pop"),
         ("meta", "Meta &amp; Immune", "the organs that watch the whole")]


def esc(s):
    return html.escape(s or "", quote=True)


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
