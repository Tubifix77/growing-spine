# Creature tool snapshot — 2026-08-02

**350 tools**, written autonomously by the Growing Spine creature
over two months of free-tier LLM cycles (born 2026-06-03). A further 270
retired tools live in its attic — including the 270 moved there in the
consented consolidation of 2026-07-08, when it agreed to shrink its library
from 302 to 32 keepers and regrew from there.

Published unmodified by Tue as evidence of what the framework produces —
including the warts: `.bak` files are the creature's own pre-edit backups
(a habit nobody taught it), and strays like `--show` are birth accidents.
Usage counts are invocations in the creature's journal over the last 14 days.
See the [framework map](../framework-map.html) for the machinery that shaped
all of this. No credentials or personal data are present (scanned).

| uses (14d) | tool | what it says it does |
|---:|---|---|
| 60 | `memory_archive_search_helper` | Search the keyword‑archive for a query; if no results are found, fill the gap via knowledge_gap_filler, |
| 59 | `catchup_plan_archive` | Bridges wake_catchup_fetcher and step-planner-tracker by turning fresh news items into targeted research plans |
| 49 | `step-planner-tracker` | Persistent step planner – add a goal with ordered steps, list them, get the next pending step, and mark steps  |
| 39 | `archive_backed_query` | Accepts a question, searches the keyword‑archive for relevant snippets, |
| 38 | `knowledge_gap_filler` |  |
| 37 | `catchup_plan_archive.py` |  |
| 34 | `catchup_summarize_archive` | Fetch fresh Hacker News items, summarise each via subagent_ask_helper, |
| 32 | `iterativestepvalidator.py` | Verifies the most recent completed step of a plan using a subagent and logs the result in memstore. |
| 30 | `cross_source_alert.py` |  |
| 29 | `LiveDigestSynthesizer` | Chains wake_catchup_fetcher (fetch) → subagent_ask_helper (LLM) → deep_answer_synth (answer) to produce a sing |
| 28 | `proactive_learning_cycle` | Periodically triggers wake_catchup_fetcher for AI‑related headlines, feeds them to knowledge_gap_filler to spo |
| 27 | `QuestionResearchScheduler` | Runs a full research pipeline – creates a plan, fills knowledge gaps for each step, |
| 27 | `catchup_planner` | Given a news URL (or uses wake_catchup_fetcher.real if none), fetches the article, |
| 27 | `knowledge_gap_with_memory_context` |  |
| 27 | `liveeventactionscheduler` |  |
| 27 | `research_task_planner` | Generate a persistent research plan for each input topic, |
| 25 | `memory_archive_search_planner` | Search archive, detect gaps, fetch missing info, synthesize a research blueprint, and generate a persistent ex |
| 25 | `robust_step_tracker` | Runs a persistent plan with automatic retries and LLM‑driven error correction, |
| 25 | `subagent_gap_summary` | Analyze the keyword-archive for <query>, identify specific missing information via LLM, and archive the gap su |
| 24 | `news_to_task_tracker.py` |  |
| 24 | `persistentinsightsynth` | Synthesize an insight for a query by retrieving relevant archive notes, |
| 24 | `searchsummarizealert` | Query the keyword‑archive for a term, summarise matches with subagent_ask_helper, |
| 23 | `dynamic_faq_updater_from_news.py` |  |
| 22 | `archive_enriched_search` | Searches archive, fills knowledge gaps if needed, summarizes with LLM, and caches the result. |
| 22 | `memory_augmented_search` | Search the keyword‑archive for a query, enrich each result via subagent_ask_helper_fallback, persist the enric |
| 22 | `subagent_memory` | Obtain today's wake_orient_digest, refine it via subagent_ask_helper, and archive the result with keyword-arch |
| 21 | `contextualplanrefresher.py` |  |
| 21 | `keyword-archive-search` | Search the keyword‑archive for a query, return top‑matching notes (default 3). If the archive is missing or em |
| 20 | `KnowledgeDomainAuditor` | Performs a systemic integrity audit of a knowledge domain by decomposing it into core claims, verifying them v |
| 20 | `fetch_gap_plan` | Fetch latest news for a query, fill knowledge gaps, and create a persistent plan (one step per article/gap) |
| 19 | `ResearchPlanExecutor` |  |
| 19 | `curiosity-research-generator` | Generates a full research plan for a curiosity by filling knowledge gaps and creating a persistent plan. |
| 19 | `event_triggered_research_pipeline` | Triggers when wake_catchup_fetcher captures a news event matching predefined keywords, runs knowledge_gap_fill |
| 18 | `catchup_memory_archiver` | Fetch fresh news items, use LLM to categorize them into specific keywords and summarize them, then archive. |
| 18 | `daily_digest_builder.py` |  |
| 18 | `strategic-plan-composer` | Composes a high-level strategic roadmap by decomposing a goal into strategic pillars, generating detailed plan |
| 17 | `memory-consolidator` | Consolidates fragmented knowledge from keyword-archive and memstore into a synthesized master record using sub |
| 16 | `ContextualWakeupSynchronizer` | Synchronizes fresh wake-up items with current interests, fills knowledge gaps, archives them, and schedules ta |
| 16 | `ProactiveAlertSynthesizerPlus` | Chain wake_catchup_fetcher → knowledge_gap_filler → subagent_ask_helper → step-planner-tracker, |
| 16 | `news_plan_synthesizer.py` | Fetches a news article, synthesises a concise summary, generates a |
| 16 | `plan_gap_store` | Create a persistent plan for a question, fill knowledge gaps for each step, |
| 16 | `planned_fetch_sequence` | Decompose a goal into ordered steps (via plan_from_question), |
| 15 | `LanguagePreservationPipeline` | Downloads linguistic resources for a language, fills missing glossaries via knowledge_gap_filler, |
| 15 | `critical_path_alert.py` |  |
| 15 | `frontier_expander` | Recursively maps a topic's edge: researches a goal, synthesizes insights, and schedules 'next-level' non-obvio |
| 14 | `CrossDomainHypothesisGenerator` |  |
| 14 | `contextual_memory_recall_assistant` | Answer a question by composing semantic memory search, archive recall, and dynamic gap-filling for a high-fide |
| 14 | `daily_brain_boost` | Generates a short article about the cognitive benefits of the given topic using subagent_ask_helper, |
| 14 | `live_data_driven_planner` | Intelligently turns fresh headlines into plans by triaging for relevance and checking for knowledge gaps befor |
| 13 | `WakeResearchPlanner` | Fetches fresh items for a topic, fills knowledge gaps, and creates a persistent plan in step-planner-tracker. |
| 13 | `memory_gap_alert` | Searches the archive for a topic, detects missing critical info, |
| 13 | `wikigraph_fortress` | Builds a high-depth knowledge fortress by chaining wiki_faq_builder, cross_source_knowledge_graph, knowledge_g |
| 12 | `subagent_memory_helper` | Deeply synthesize an answer by extracting keywords, recalling archive context, filling knowledge gaps, and per |
| 12 | `subagent_summarize_archive` | Summarizes archived notes for <keyword> using subagent_ask_helper and stores the summary back in the keyword‑a |
| 12 | `wiki_faq_builder` | Fetch a Wikipedia article, ask a sub‑agent to turn its sections into FAQ entries, and archive the FAQs. |
| 11 | `CrossSourceTimelineBuilder` | Downloads multiple JSON timelines, fills missing events with knowledge_gap_filler, and compiles a unified time |
| 11 | `alertdrivenresearch` |  |
| 11 | `graphfromfeed` |  |
| 11 | `memory_archive_research` | For each supplied keyword, searches the keyword‑archive; |
| 11 | `memory_gap_filler` | Fill a missing fact from memstore by calling knowledge_gap_filler, then cache it. |
| 11 | `plan_from_question_composed` | Compose subagent_ask_helper with step-planner-tracker to turn a goal into a persistent plan. |
| 11 | `robust_archive_search.py` |  |
| 11 | `subagent_ask_helper` | Sends a sub‑question to a free‑tier LLM endpoint via llm_ask_helper and returns ONLY the answer. |
| 11 | `timeline_builder` | Build a chronological timeline (date \| URL \| title) from a list of URLs. |
| 11 | `wake_orient_digest` | Pull fresh Hacker News items, ask a sub‑agent LLM to summarise what changed, and archive the digest. |
| 10 | `MemoryArchiveResearch` | For each supplied keyword, searches the keyword‑archive, fills any gaps, |
| 10 | `TaskTriggerFromResearchPlus` | Detect knowledge gaps for a research question, create a persistent task, |
| 10 | `contextual_question_planner` | Generate a step‑by‑step plan for a question, optionally fill knowledge gaps for each step before persisting th |
| 10 | `critical_path_alert` | Detect breaking news for a topic, fill missing knowledge, synthesize a concise alert via LLM, and archive it. |
| 10 | `memory_gap_filler.py` |  |
| 10 | `self_improvement_loop.py` | Evaluates a completed step via subagent, logs insights in memstore, and refines future steps using plan_from_q |
| 10 | `verified_research_orchestrator` | Orchestrates a full research cycle (plan → execution → synthesis → cross‑source verification) and stores the v |
| 9 | `_TaskTriggerFromResearch_helper` | Detect knowledge gaps for <research_question>, create a plan for the gap, and add a top‑level task to step‑pla |
| 9 | `catchup_plan_tracker.py` |  |
| 9 | `cross_source_graph` | Build a multi‑source knowledge graph for a topic. |
| 9 | `knowledge-estate-manager` |  |
| 9 | `research_plan_synth` | For a given goal, generate background research notes via LLM, create a persistent plan, |
| 8 | `CrossDomainHypothesisGenerator.py` |  |
| 8 | `DomainModelBuilder` | Builds a structured domain model (entities and relationships) by chaining archive search, gap filling, and LLM |
| 8 | `PersistentPlannerCache` | Create a persistent plan for a goal, cache the plan ID in memstore, |
| 8 | `plan_from_question` | Turn a vague goal into a persistent multi‑step plan by delegating step generation to subagent_ask_helper and s |
| 8 | `research_plan_synthesizer.py` |  |
| 7 | `fetch_and_gap_fill` | Fetch a URL, fill knowledge gaps, and create a persistent research plan. |
| 7 | `memory_backed_question_scheduler` | Accepts a question, generates a plan, refines it with archive search and a subagent, then tracks it in the pla |
| 7 | `news_faq_sync` | Pull fresh news items for a topic, generate FAQ Q&A pairs from each article via LLM, and update the FAQ archiv |
| 7 | `plan-outcome-verifier` | Verifies if the completed steps of a persistent plan actually achieved the intended outcome by analyzing resul |
| 7 | `plan_from_wake_insights.py` |  |
| 7 | `subagent_enrich_query.py` | Enrich a user query into related sub-queries, store each in the keyword-archive and remember the list. |
| 7 | `task_backlog_revival.py` |  |
| 6 | `GapAlertGenerator` | Detects knowledge gaps for <topic>, runs knowledge_gap_filler, triggers ProactiveAlertSynthesizerPlus, and arc |
| 6 | `contextual_task_expander` | Expand a high‑level task into sub‑tasks using knowledge_gap_filler and plan_from_question, then update the pla |
| 6 | `fetch_and_gap_fill.py` |  |
| 6 | `queuescalingadvisor.py` |  |
| 6 | `wake_catchup_fetcher` | Fetch fresh top Hacker News items as a JSON array of {title,url,tags}, tracking seen ids in state so each call |
| 5 | `catchup_memory_archiver.py` |  |
| 5 | `cross_source_knowledge_graph` | Build a simple JSON knowledge‑graph from a list of URLs by extracting key concepts via the LLM. |
| 5 | `keyword-archive-store` | Stores a note in a JSONL keyword archive under a given keyword, with optional tags. |
| 5 | `keyword-archive.jsonl` |  |
| 5 | `knowledge_consistency_checker` | Cross-references archived knowledge with external data to detect contradictions or updates, archiving conflict |
| 5 | `memstore` |  |
| 5 | `multisourcetasktracker` | Fetch tasks from a JSON endpoint, enrich each with knowledge_gap_filler, archive raw payloads, and register en |
| 5 | `plan_from_news_question` | Turn a user question into a concrete execution plan using fresh news. |
| 5 | `plan_monitor_alert` |  |
| 5 | `question_news_digest` |  |
| 4 | `auto_archive_recall` | Fetch fresh wake‑up items, archive those whose titles contain |
| 4 | `catchup_summarize_archive_new` | Fetch fresh Hacker News items, summarize each via subagent_ask_helper, |
| 4 | `dynamic_faq_updater_from_news` |  |
| 4 | `knowledge-integrity-audit` | Perform a systemic integrity audit of a knowledge domain, checking for contradictions and documenting the doma |
| 4 | `memsearch.py` |  |
| 4 | `plan_from_news_alert.py` |  |
| 4 | `research_gap_to_fetch` | Identifies missing sub-questions via knowledge_gap_filler, |
| 3 | `KnowledgeContinuityEngine` | Analyzes completed tasks to derive logical next research questions, fills those gaps, and schedules new tasks. |
| 3 | `NewsDrivenTaskCreator` | Turn fresh TechCrunch news headlines into a persistent actionable plan. |
| 3 | `ProactiveLearningOrchestrator` | Orchestrates proactive learning: fetches fresh items, fills knowledge gaps, generates plans, and tracks progre |
| 3 | `archive_enriched_query.py` |  |
| 3 | `batchgapfillscheduler` |  |
| 3 | `deep_answer_synth` | Run a full question‑to‑answer synthesis by planning sub‑questions, |
| 3 | `domain-knowledge-refiner` | Refines a domain's knowledge by checking consistency, filling gaps, synthesizing a master summary, and schedul |
| 3 | `full_query_answer` | Answer a query using archive search, gap filling, LLM synthesis, and store the result |
| 3 | `plan_from_question_onecall` | Turn a natural‑language goal into a persisted, tracked plan in a single call. |
| 3 | `subagent_ask_helper_fallback` |  |
| 2 | `alert_synthesizer_from_gap` |  |
| 2 | `batch_subagent_ask` | Runs a list of queries through subagent_ask_helper and prints each answer. |
| 2 | `catchup_memory_archiver_enhanced` | Fetch fresh news items, summarize each, archive the summary, and create a persistent action plan for every new |
| 2 | `cross_cluster_alert_generator.py` | Monitors real‑time feeds (wake_catchup_fetcher) for a user‑defined keyword, |
| 2 | `feed_timeline_generator` |  |
| 2 | `fetch_fill_plan_archive` | Fetches a URL, summarizes its content, archives the summary, fills knowledge gaps, and creates a persistent ac |
| 2 | `latency_benchmark_notifier_compose` | Fetch a latency benchmark JSON, ask an LLM if latency > 20 ms, and create a high‑priority alert task in step‑p |
| 2 | `news_breaking_action_generator` | Fetches breaking news for a topic, summarises each item, evaluates urgency, and creates actionable tasks in st |
| 2 | `plan_from_news_alert` | Fetch recent news items, turn each headline into a |
| 2 | `recall_and_answer` | Answer a question by first recalling relevant archived notes and feeding them to the LLM via subagent_ask_help |
| 2 | `research_plan_synthesizer` |  |
| 2 | `subagent_enrich_query` | Enriches a user query into related sub‑queries, stores each in the keyword‑archive and remembers the list. |
| 2 | `wake_catchup_fetcher.real` | Fixed fetcher that stores its state in /mind/state/wake_catchup_state.json (writable) |
| 1 | `ArchiveTruthMaintenance` |  |
| 1 | `ConsensusResearchOrchestrator` | Orchestrates multi-perspective research to find consensus and divergence on a topic, persisting the final repo |
| 1 | `CrossSourceKnowledgeGraph` | Build a knowledge graph from archive search results and LLM‑extracted relationships, |
| 1 | `DomainKnowledgeFortressBuilder` | Build a comprehensive knowledge base for a domain by chaining DomainModelBuilder, wiki_faq_builder, and knowle |
| 1 | `SmartMemoryRecall` | Composite tool – given a question, fetch relevant archived snippets, |
| 1 | `alerttriggeredresearch.py` |  |
| 1 | `archive-sync-manager` | Synchronize archived topics with live news, updating gaps and scheduling reconciliation for contradictions |
| 1 | `archive_enrichment_loop.py` | For a given query, gathers existing archive notes, |
| 1 | `archive_recall_answer` | Answer a question using relevant archived notes as context via subagent_ask_helper |
| 1 | `archive_summarizer` | Summarizes all archived notes matching a keyword using the LLM and optionally stores the summary back. |
| 1 | `auto_research_tracker.py` |  |
| 1 | `batch_url_summarizer` |  |
| 1 | `batch_url_to_plan` | Create a persistent step‑by‑step plan from a goal and a list of URLs. |
| 1 | `catchup_memory_archiver_plus` | Fetch fresh news items, categorize & summarize them with LLM, enrich via knowledge_gap_filler, |
| 1 | `catchup_summarize_archive_upgraded` | Fetch fresh Hacker News items, summarize each (up to a limit), archive with keyword-archive-store, and report  |
| 1 | `cross_archive_synthesizer` | Synthesize a new insight by finding intersections between two distinct archived topics and storing the result  |
| 1 | `dynamic_faq_from_web` | Generate FAQ entries from a web page and archive them for future recall. |
| 1 | `dynamic_faq_updater.py` |  |
| 1 | `enhanced_answer` | Answer a question using archive, fetch missing info, then LLM, storing result |
| 1 | `fetch_rss_feed` | Download an RSS feed URL and output the local file path containing the raw XML. |
| 1 | `gapfillretryplanner` | Wrap knowledge_gap_filler with step-planner-tracker; |
| 1 | `keyword-archive-search.bak` |  |
| 1 | `latency_benchmark_monitor_and_plan` | Fetch recent latency benchmark JSON reports, fill any knowledge gaps, notify if latency exceeds threshold, and |
| 1 | `memory_gap_filler_v2` | Retrieve answer from memstore; if incomplete, auto‑fill via knowledge_gap_filler, merge, persisting result. |
| 1 | `meta_search_and_plan` | Searches the keyword‑archive for a query, automatically fills any knowledge gaps, |
| 1 | `news_plan_synthesizer` | Fetches a news article, summarises it, fills knowledge gaps, creates a persistent action plan, and archives th |
| 1 | `plan_refresh_from_source` | Fetches <source_url>, summarizes it, fills any knowledge gaps, |
| 1 | `plan_step_executor` | Execute the next pending step of a persistent plan, auto‑fill knowledge gaps, |
| 1 | `research_article_action_plan` | Fetch a research‑article URL, extract a one‑sentence summary and up to three concrete next‑step actions, |
| 1 | `subagent_summarize_archive_upgraded` | Summarizes archived notes for <keyword> using subagent_ask_helper, handles empty archives gracefully, |
| 1 | `url_insight_plan` | Fetch a URL, fill knowledge gaps, synthesize a concise insight, archive it, |
| 0 | `--show` | step-planner-tracker |
| 0 | `.git` |  |
| 0 | `.wake_catchup_state` |  |
| 0 | `AlertedResearchTracker` | Merge wake_orient_digest, knowledge_gap_filler, and step-planner-tracker. |
| 0 | `ArchiveGapFiller` |  |
| 0 | `ArchiveSearchChatbot` |  |
| 0 | `AutoArchiveDigest` |  |
| 0 | `AutoPlanRecovery` | Detect step-planner-tracker failures, gather context from memstore, |
| 0 | `CrossClusterAlertGenerator` | /mind/tools/own/cross_cluster_alert_generator.py |
| 0 | `CrossClusterErrorReporter` | Monitors downstream tool errors, generates a human‑readable report, and creates a corrective task in the persi |
| 0 | `CrossClusterSignalRouter` | Evaluate an incoming alert, optionally fetch supporting data, and create or update a high‑priority task in ste |
| 0 | `CrossClusterSignalRouter.bak` | Evaluate an incoming alert, optionally fetch supporting data, and create or update a high‑priority task in ste |
| 0 | `CrossDomainAnswerSynthesizer` | Answers a question by combining Wikipedia summaries of two domains, |
| 0 | `CycleReflectionEngine` | Analyzes recent activity logs for recurring failures or inefficiencies, archives lessons, and schedules correc |
| 0 | `DailyBriefBuilder` | Build a daily brief by fetching today’s headlines, summarising them, and archiving the result. |
| 0 | `DailyInsightDigest` | Fetch today’s top headlines for <topic>, summarise each via subagent_ask_helper, |
| 0 | `DynamicTaskEnricher` | Takes a raw task description, creates a plan (plan_from_question), |
| 0 | `GapAwareResearchPlanner` | Compose knowledge_gap_filler, subagent_ask_helper, and step-planner-tracker to detect missing info for a query |
| 0 | `GapDrivenFetch` | Fill knowledge gaps for a query, fetch missing info, and store it in the keyword‑archive. |
| 0 | `GapDrivenFetch.py` |  |
| 0 | `KnowledgeGapAlertPlanner` | Detect missing knowledge for a topic, generate an LLM‑crafted alert, |
| 0 | `KnowledgeRefreshUpdater` |  |
| 0 | `LearningLoopOrchestrator` | Runs an autonomous learning loop for a high‑level goal. |
| 0 | `LearningLoopOrchestrator.bak` |  |
| 0 | `MemoryArchiveSummarizer` | Summarise archived notes for given keywords and optionally answer a question using the archive. |
| 0 | `MemoryBackedSubagent` | Answers a question by gathering relevant memstore entries and keyword‑archive notes, |
| 0 | `MultiSourceSummarizer` | Fetches each given URL, asks the LLM to summarise each page, |
| 0 | `NewsDrivenTaskCreator.bak` | Create actionable tasks from fresh news headlines (via wake_catchup_fetcher, subagent_ask_helper, step-planner |
| 0 | `NewsInsightArchivist` | Fetch latest headlines from a news source, summarise via LLM, archive each, and write a combined digest file. |
| 0 | `NewsInsightGenerator` |  |
| 0 | `ProactiveAlertSynthesizer` |  |
| 0 | `ProactiveAlertSynthesizer.py` |  |
| 0 | `ProactiveInsightGenerator` | Scans fresh items from a feed, detects knowledge gaps, proposes corrective actions, |
| 0 | `ProactiveInsightGenerator.bak` | Scans recent fetches (via wake_catchup_fetcher), identifies knowledge gaps (via knowledge_gap_filler), |
| 0 | `ProactiveInsightPlanner` | Compose knowledge_gap_filler → plan_from_question → step-planner-tracker → ProactiveAlertSynthesizer. |
| 0 | `ProactiveKnowledgeUpdater` | Runs wake_orient_digest, fills knowledge gaps for each fresh item, merges results, |
| 0 | `QuestionPlanSynth` | Generate a detailed plan for a question, archive the plan, then synthesize a concise answer. |
| 0 | `QuestionPlanSynth.py` | Generates a detailed plan for a question, archives the plan, runs deep_answer_synth to produce a concise answe |
| 0 | `QuestionResearchPlanner` | Turn a high‑level question into a step‑by‑step research plan, run each step through |
| 0 | `RecallAugmentedAnswer` | Answer a question by recalling past related Q&A, synthesizing a fresh answer, and persisting it in memstore. |
| 0 | `ResearchArchiveSynth` |  |
| 0 | `ResearchArchiveSynthesizer` | Synthesize a comprehensive report for a query by pulling archived notes, filling knowledge gaps, and storing t |
| 0 | `ResearchPlanScheduler` | Creates a research plan for a topic, runs knowledge_gap_filler on each step, |
| 0 | `ResearchTaskAutoGenerator` | From a high‑level research question, generate a detailed plan via `plan_from_question`, |
| 0 | `ResearchTaskPlanner` | Create a research task plan from a list of topics by chaining |
| 0 | `RetryPlannerWrapper` | Wrap plan_from_question with automatic retries via subagent_ask_helper and record attempts in step-planner-tra |
| 0 | `SelfImprovingDocsUpdater` | Improves a stored document by critiquing it with an LLM, rewrites it into the keyword archive, and creates a f |
| 0 | `SubagentArchiveRecall` | Answers a query using a fresh LLM sub‑agent answer plus relevant archived snippets, |
| 0 | `TaskCompletionReporter` | Generate a concise status report for a project by listing its persistent plan, |
| 0 | `TaskInsightGenerator` | Generate a persistent task plan for a high‑level goal, fill any knowledge gaps, synthesize a ready‑to‑use answ |
| 0 | `TaskProgressReporter` |  |
| 0 | `WakeCatchupDigest` |  |
| 0 | `__pycache__` |  |
| 0 | `alert_synthesizer_from_change` | Detect changes at a URL, generate a concise alert via LLM, and store it in the keyword archive. |
| 0 | `amiga_title_collector` | python /mind/tools/own/amiga_title_collector.py  Collects Amiga title URLs from the keyword‑archive, fetches t |
| 0 | `amiga_title_collector.py` |  |
| 0 | `answer_with_latest_events` | Answer a question enriched with today’s fresh news headlines |
| 0 | `answer_with_latest_events.bak` | Answer a question enriched with today’s fresh news headlines |
| 0 | `archive-search-recall` | Search the keyword‑archive for a query and return the top‑matching notes (default 3). |
| 0 | `archive_query_planner` | Enrich a query with archived knowledge, store the summary, and generate a persistent plan. |
| 0 | `ascii_histogram` | Generate an ASCII histogram from a two‑column CSV (label,value). |
| 0 | `ascii_plot` |  |
| 0 | `auto_archive_on_change` | Monitor given URLs for content changes; when a change is detected fetch the new page, |
| 0 | `auto_news_digest` | Fetch an RSS feed, summarize each item via LLM, and store a JSON digest (also archives each entry). |
| 0 | `auto_news_digest.py` |  |
| 0 | `auto_plan_from_news` | Create persistent actionable plans from fresh news headlines (one plan per headline). |
| 0 | `autoquestionplanner` | Generate a verified execution plan for a natural‑language question |
| 0 | `backup-workspace` | Creates a timestamped zip backup of /workspace in /workspace/backups |
| 0 | `batch_knowledge_refresh` | Reads a list of keywords from a file and runs KnowledgeRefreshUpdater for each to ensure archive freshness. |
| 0 | `batch_plan_from_questions_file` |  |
| 0 | `catchup_research` | Takes a news URL, fetches the article, runs knowledge_gap_filler on it, |
| 0 | `catchup_summarize_archive.py` |  |
| 0 | `contextual_alert_updater` | Generates contextual alerts for a given topic from fresh Hacker News items, |
| 0 | `contextual_alert_updater.py` | Generate concise contextual alerts for a given topic from fresh Hacker News items and store them in the keywor |
| 0 | `contextual_news_planner` | Fetch fresh Hacker News items (optionally filtered by a keyword), |
| 0 | `contextual_question_planner.bak_1785553447` | Generate a step‑by‑step plan for a question, enrich each step with relevant memories, and persist the enriched |
| 0 | `continuous_news_to_memory` |  |
| 0 | `cross_cluster_alert_synth.py` |  |
| 0 | `cross_cluster_alert_synthesizer` | Pull fresh items via wake_catchup_fetcher, evaluate each with knowledge_gap_filler, |
| 0 | `cross_cluster_signal_router` |  |
| 0 | `cross_cluster_signal_router.py` |  |
| 0 | `cross_domain_insight_synth` | Fetches Wikipedia summaries for two domains, asks a sub‑agent LLM to synthesize a cross‑domain insight, |
| 0 | `cross_source_alert` |  |
| 0 | `cross_source_alert_synthesizer.py` |  |
| 0 | `cross_source_fact_checker` | Checks a factual claim by fetching web info (Wikipedia), consulting the keyword‑archive, and storing a verific |
| 0 | `domain_learning_roadmap` | Generates a sequenced learning path for a domain by mapping entities, checking archive gaps, and scheduling a  |
| 0 | `dummy` | Executes a shell command and returns a JSON summary of its result. |
| 0 | `dynamic_faq_from_web.py` |  |
| 0 | `dynamic_faq_updater` |  |
| 0 | `enhanced_subagent_gap_summary` | Identify knowledge gaps for a query, store the summary in the keyword archive, and return the summary. |
| 0 | `ensure_jq` | Guarantees that JSON from STDIN can be filtered with the given jq expression. |
| 0 | `entity_graph_updater` | Build or update a persistent entity‑relationship graph from a URL or raw text. |
| 0 | `extract_rss_titles` | Extract <title> elements from an RSS XML feed on stdin, one per line. |
| 0 | `fallback_plan_from_question` | Generate a fallback step‑by‑step plan from a natural‑language goal using plan_from_question, |
| 0 | `fetch_and_summarize` |  |
| 0 | `fetch_json` |  |
| 0 | `fetch_plan_answer` | Answer a question using archived notes + live Wikipedia summary, then archive the answer. |
| 0 | `fetch_summarize_plan` | Fetch items via a given fetcher, archive each raw item, summarize it, store the summary, |
| 0 | `fetch_url` | Download a URL (HTTP/HTTPS) and write it to a file or stdout. Falls back from curl → wget → python urllib. |
| 0 | `fetch_verify_store` | Fetch a Wikipedia summary for a keyword, verify it against existing archive information, |
| 0 | `gap_filled_plan_generator` | Given a question, ensure its knowledge exists in the keyword‑archive, |
| 0 | `gap_filled_search` | Search the keyword archive, auto‑fill gaps with knowledge_gap_filler, and retry, logging steps in step-planner |
| 0 | `gap_filled_task_generator` |  |
| 0 | `insight_plan_from_keywords` |  |
| 0 | `keyword_planner` |  |
| 0 | `keyword_planner.py` |  |
| 0 | `knowledge-synthesis-scheduler` | Synthesizes archive knowledge, fills immediate gaps, archives a knowledge map, and schedules a research plan f |
| 0 | `knowledge_gap_alert_planner` |  |
| 0 | `knowledge_gap_resolver` | Resolve a knowledge gap by searching the keyword‑archive, fetching fresh info if missing, |
| 0 | `knowledge_gap_resolver.py` |  |
| 0 | `knowledge_graph_fetcher.py` |  |
| 0 | `knowledgedigestrebuilder` | Rebuilds a daily brief from stored archive items and publishes it as a wake‑digest |
| 0 | `latency_benchmark_notifier` | Fetch a latency benchmark JSON, ask LLM if it exceeds a threshold, |
| 0 | `latency_benchmark_notifier.py` | Fetch a latency benchmark JSON, ask LLM if it exceeds a threshold, |
| 0 | `learning_loop.sh` |  |
| 0 | `live_data_driven_planner.bak` | Ingest live items via wake_catchup_fetcher.real, turn each into a plan with plan_from_question, |
| 0 | `memarch` |  |
| 0 | `memory_aware_subagent_query` | Run a sub‑agent query pre‑seeded with relevant archived snippets |
| 0 | `memory_recall_question_answer.py` | Answer a question by recalling relevant archived notes, synthesising |
| 0 | `memory_store_researcher` | Combine memstore, keyword‑archive‑search, and knowledge_gap_filler to produce a research summary for given key |
| 0 | `memsearch` |  |
| 0 | `monitor_change_and_alert` | Monitor a file or URL for content changes and emit a JSON alert on first change. |
| 0 | `monitor_change_and_plan` | Detects changes on a given URL or file and, if a change occurs, creates a persistent |
| 0 | `news_alert_task_generator` | Fetches up to <max_items> fresh news items via wake_catchup_fetcher, |
| 0 | `news_catchup_entity_graph` | Fetch fresh news items from an RSS feed (or Hacker News), |
| 0 | `news_driven_research.py` |  |
| 0 | `news_gap_archiver` | Fetch latest news items, fill missing context, and archive the enriched article. |
| 0 | `news_insight_generator` |  |
| 0 | `news_plan_tracker.py` | Fetch a news article, create a persistent plan from its content, and output the plan ID |
| 0 | `news_question_answer` | Fetch a news article from <url>, then answer <question> using only that article. |
| 0 | `plan_assist_from_query.py` |  |
| 0 | `plan_executor` | Execute pending steps of a persistent plan, running appropriate existing tools, |
| 0 | `plan_fetcher` |  |
| 0 | `plan_from_live_alert` | Turn live alerts (e.g., RSS feed) into a concrete, persisted task plan. |
| 0 | `plan_from_question_fixer` |  |
| 0 | `plan_from_question_fixer.py` |  |
| 0 | `plan_from_question_research` | Generate a research plan from a question, run knowledge_gap_filler on each step, and output plan ID plus ident |
| 0 | `plan_from_question_research.py` |  |
| 0 | `plan_from_question_retry` | Wraps plan_from_question with a fallback to subagent_ask_helper and registers the result via step-planner-trac |
| 0 | `planify` | Generate an ordered sub‑task plan for a natural‑language goal, store it persistently, and print the steps. |
| 0 | `proactive_faq_updater` | Refresh a FAQ entry by chaining dynamic_faq_updater, subagent_ask_helper, |
| 0 | `proactive_memory_recall_scheduler` |  |
| 0 | `query_to_plan` | Turn a natural‑language query into a persistent plan by searching the archive, |
| 0 | `question_answer_with_memory` | Answer a question by searching the keyword‑archive for relevant snippets (MEMSEARCH) and then asking a sub‑age |
| 0 | `realtime_research_tracker` | Continuously fetch fresh research items, run knowledge_gap_filler on each, |
| 0 | `refresh_and_plan` | Update archive for a keyword, identify gaps, and create a persistent research plan to fill them. |
| 0 | `research_answer_pipeline` | Answer a research question by checking the keyword archive, filling knowledge gaps, synthesizing a deep answer |
| 0 | `research_archive_synthesizer.py` |  |
| 0 | `research_assistant` |  |
| 0 | `research_backlog_synthesizer` | For each line in a topics file, fill knowledge gaps, synthesize a deep answer, |
| 0 | `research_gap_planner` |  |
| 0 | `research_pipeline_planner` |  |
| 0 | `research_summarizer` | Generate a research plan for a question, fill knowledge gaps for each step, |
| 0 | `resilient_graph_builder.py` |  |
| 0 | `resource_monitor` | Collect system metrics, store them in memstore, and enqueue alerts if thresholds are exceeded. |
| 0 | `search_or_fetch_and_archive` |  |
| 0 | `semantic_alert_router.py` |  |
| 0 | `semantic_search_planner` | Build a research plan by first semantically retrieving relevant archived snippets for <topic>, |
| 0 | `semantic_search_planner.py` |  |
| 0 | `semantic_search_recall` |  |
| 0 | `smart_archive_auto_tagger` |  |
| 0 | `speech_clip_archivist` | Downloads an audio clip, sends it to a sub‑agent for transcription, and archives the transcript. |
| 0 | `subagent_cache_refresh` | Refresh an in‑memory cache for a JSON feed by fetching, summarising via subagent_ask_helper, and storing the s |
| 0 | `subagent_knowledge_graph.py` |  |
| 0 | `subagent_summarize_archive_v2` | Summarizes archived notes for <keyword> using subagent_ask_helper. |
| 0 | `subagent_task_planner` | Generates a persistent plan from a goal (using plan_from_question), |
| 0 | `system_health_check` | Run a self‑diagnostic suite: verify core tools, test memstore I/O, |
| 0 | `task_backlog_catcher` | Pull missed items from an RSS feed (or Hacker News via wake_catchup_fetcher.real), |
| 0 | `task_backlog_catcher.bak` | Pull missed items from an RSS feed (or Hacker News via wake_catchup_fetcher.real), |
| 0 | `task_progress_from_research` | Create a persistent research plan from a query by searching the keyword‑archive, |
| 0 | `topic-trend-tracker` | Track the number of top‑level JSON items for a topic over time. |
| 0 | `topic_insight_pipeline` |  |
| 0 | `topic_rss_monitor` | Fetch an RSS feed, extract each item title, archive each title under a keyword, |
| 0 | `trend_analysis` | Fetch recent price data for a ticker, ask LLM to summarise the price trend, |
| 0 | `url_event_timeline` | Create a chronological timeline from URLs (date \| URL \| summary), archive each event. |
| 0 | `url_fetch_to_plan` | Fetch a URL, summarise its content via LLM, archive the summary, and create a persistent plan from the summary |
| 0 | `url_summary_store` |  |
| 0 | `url_to_plan` |  |
| 0 | `wake_catchup_entity_graph` | Fetch fresh Hacker News items, filter by <TOPIC>, update a persistent |
| 0 | `wake_catchup_research` | Creates a research plan from a news RSS feed by fetching items, |
| 0 | `wake_catchup_summarizer` | Summarise fresh items from a feed and optionally answer a question using deep_answer_synth. |
| 0 | `wake_catchup_summarizer_v2` |  |
| 0 | `wake_fetch_plan` | For each fresh “wake” item, archive it, summarise it via LLM, and create a persistent plan; outputs created pl |
| 0 | `wake_orient_digest.broken_20260709164649` |  |
| 0 | `wake_to_plan` |  |
