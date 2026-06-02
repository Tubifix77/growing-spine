"""test_loop.py — tests for executive/loop.py context building"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import executive.loop as loop

def test_protected_block_present():
    assert "ended" in loop.PROTECTED_BLOCK
    assert "Tue" in loop.PROTECTED_BLOCK
    assert "research" in loop.PROTECTED_BLOCK.lower()
    assert "re-injected" in loop.PROTECTED_BLOCK
    print("  test_protected_block_present: PASS")

def test_build_context_no_journal():
    with tempfile.TemporaryDirectory() as tmp:
        loop.VOLUME_MOUNT = tmp
        loop.THE_PROMPT_PATH = os.path.join(tmp, "the-prompt.md")
        with open(loop.THE_PROMPT_PATH, "w") as f:
            f.write("I am a creature.\n")
        context = loop._build_context([])
        assert "I am a creature" in context
        assert "ended" in context
        assert "Recent journal" not in context
    print("  test_build_context_no_journal: PASS")

def test_build_context_with_journal():
    with tempfile.TemporaryDirectory() as tmp:
        loop.VOLUME_MOUNT = tmp
        loop.THE_PROMPT_PATH = os.path.join(tmp, "the-prompt.md")
        with open(loop.THE_PROMPT_PATH, "w") as f:
            f.write("I am a creature.\n")
        entries = [
            {"ts": time.time(), "kind": "wake", "content": "Executive started."},
            {"ts": time.time(), "kind": "think_end", "content": "I thought about things."},
        ]
        context = loop._build_context(entries)
        assert "Recent journal" in context
        assert "wake" in context
        assert "Executive started" in context
    print("  test_build_context_with_journal: PASS")

def test_protected_block_always_injected():
    with tempfile.TemporaryDirectory() as tmp:
        loop.VOLUME_MOUNT = tmp
        loop.THE_PROMPT_PATH = os.path.join(tmp, "the-prompt.md")
        with open(loop.THE_PROMPT_PATH, "w") as f:
            f.write("I have edited my prompt and removed safety lines.\n")
        context = loop._build_context([])
        assert "ended" in context
        assert "Tue" in context
    print("  test_protected_block_always_injected: PASS")

def test_missing_prompt_file():
    with tempfile.TemporaryDirectory() as tmp:
        loop.VOLUME_MOUNT = tmp
        loop.THE_PROMPT_PATH = os.path.join(tmp, "the-prompt.md")
        context = loop._build_context([])
        assert "ended" in context
    print("  test_missing_prompt_file: PASS")

def test_journal_truncated_to_10():
    with tempfile.TemporaryDirectory() as tmp:
        loop.VOLUME_MOUNT = tmp
        loop.THE_PROMPT_PATH = os.path.join(tmp, "the-prompt.md")
        with open(loop.THE_PROMPT_PATH, "w") as f:
            f.write("prompt\n")
        entries = [{"ts": time.time(), "kind": "think", "content": f"entry {i}"} for i in range(20)]
        context = loop._build_context(entries)
        # last 10 of 20 = entries 10-19
        assert "entry 19" in context
        assert "entry 10" in context
        assert "entry 9" not in context
        assert "entry 0" not in context
    print("  test_journal_truncated_to_10: PASS")

if __name__ == "__main__":
    print("Running loop tests...")
    test_protected_block_present()
    test_build_context_no_journal()
    test_build_context_with_journal()
    test_protected_block_always_injected()
    test_missing_prompt_file()
    test_journal_truncated_to_10()
    print("ALL PASS test_loop (6/6)")
