"""test_journal.py — tests for executive/journal.py"""
import sys, os, json, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from executive.journal import append, recent

def test_append_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        append(tmp, "wake", "test wake entry")
        entries = recent(tmp, n=10)
        assert len(entries) == 1
        assert entries[0]["kind"] == "wake"
        assert entries[0]["content"] == "test wake entry"
        assert "ts" in entries[0]
    print("  test_append_and_read: PASS")

def test_multiple_entries():
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(5):
            append(tmp, "think", f"entry {i}")
        entries = recent(tmp, n=10)
        assert len(entries) == 5
        assert entries[0]["content"] == "entry 0"
        assert entries[4]["content"] == "entry 4"
    print("  test_multiple_entries: PASS")

def test_recent_n_limit():
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(20):
            append(tmp, "exec", f"entry {i}")
        entries = recent(tmp, n=5)
        assert len(entries) == 5
        assert entries[-1]["content"] == "entry 19"
    print("  test_recent_n_limit: PASS")

def test_meta_fields():
    with tempfile.TemporaryDirectory() as tmp:
        append(tmp, "exec_end", "done", {"exit_code": 0})
        entries = recent(tmp, n=1)
        assert entries[0]["exit_code"] == 0
    print("  test_meta_fields: PASS")

def test_empty_volume():
    with tempfile.TemporaryDirectory() as tmp:
        entries = recent(tmp, n=10)
        assert entries == []
    print("  test_empty_volume: PASS")

def test_timestamps_increasing():
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(3):
            append(tmp, "think", f"entry {i}")
            time.sleep(0.01)
        entries = recent(tmp, n=10)
        ts = [e["ts"] for e in entries]
        assert ts == sorted(ts), f"timestamps not increasing: {ts}"
    print("  test_timestamps_increasing: PASS")

if __name__ == "__main__":
    print("Running journal tests...")
    test_append_and_read()
    test_multiple_entries()
    test_recent_n_limit()
    test_meta_fields()
    test_empty_volume()
    test_timestamps_increasing()
    print("ALL PASS test_journal (6/6)")
