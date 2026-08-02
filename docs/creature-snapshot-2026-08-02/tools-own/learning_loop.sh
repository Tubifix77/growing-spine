#!/usr/bin/env bash
# usage: learning_loop.sh "high level learning objective"
set -euo pipefail

OBJ="${1:-Python async programming}"

# Create a persistent plan (if not already existing) via plan_from_question
# The tool returns a plan ID; we ignore it because the planner stores state internally.
plan_from_question "$OBJ" >/dev/null

# Run the orchestrator loop until completion
LearningLoopOrchestrator
