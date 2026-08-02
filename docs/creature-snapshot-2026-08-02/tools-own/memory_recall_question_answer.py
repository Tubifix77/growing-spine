#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------------------------------------
# Tool: memory_recall_question_answer
# does: Answer a question by recalling relevant archived notes, synthesising
#       a concise answer via subagent_ask_helper, and persisting the Q&A
#       in memstore for future recall.
# ----------------------------------------------------------------------
#
# Usage:
#   memory_recall_question_answer "<question>" [max_results]
#
# Arguments:
#   <question>      The natural‑language question to answer.
#   [max_results]   Optional integer, how many archive hits to retrieve
#                   (default 3).
#
# Output:
#   JSON object with keys:
#     answer   - the LLM‑generated answer,
#     key      - the memstore key where the Q&A was stored,
#     sources  - array of archived snippets used.
# ----------------------------------------------------------------------

question="${1:-}"
max_results="${2:-3}"

if [[ -z "$question" ]]; then
  echo '{"error":"question argument missing"}' >&2
  exit 1
fi

# 1️⃣ Retrieve relevant archived notes
archive_json=$(keyword-archive-search "$question" "$max_results" | jq -s '.')

# Build a simple array of {title, content} for the prompt
sources=$(echo "$archive_json" | jq -c '[.[] | {title: .title, content: .content}]')

# 2️⃣ Build a prompt for the LLM
prompt=$(cat <<EOF
You are a knowledgeable assistant. Use only the information provided below to answer the question.

Question: $question

Relevant notes:
$(echo "$sources" | jq -r '.[] | "- Title: \(.title)\n  Content: \(.content)"')
