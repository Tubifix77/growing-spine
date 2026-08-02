#!/usr/bin/env python3
"""
Manages ongoing research projects by periodically invoking knowledge_gap_filler for new data,
logging milestones with step-planner-tracker, and persisting updates in memstore.
"""
import subprocess
import json

def invoke_knowledge_gap_filler(topic):
    # Invoke knowledge_gap_filler for new data
    output = subprocess.check_output(["knowledge_gap_filler", topic])
    return output.decode("utf-8")

def log_milestones(topic, output):
    # Log milestones with step-planner-tracker
    subprocess.check_call(["step-planner-tracker", "add", topic, output])

def persist_updates(topic, output):
    # Persist updates in memstore
    subprocess.check_call(["memstore", "set", topic, output])

def main():
    topic = "microcontroller networking"
    output = invoke_knowledge_gap_filler(topic)
    log_milestones(topic, output)
    persist_updates(topic, output)

if __name__ == "__main__":
    main()
