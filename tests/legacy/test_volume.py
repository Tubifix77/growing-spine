"""test_volume.py — tests for volume/memory.py, volume/init.py"""
import sys, os, tempfile, time, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from volume import memory as mem
from volume.init import init_volume, volume_is_initialised

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')

# ── memory tests ────────────────────────────────────────────────────

def test_memory_store_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        mem.store(tmp, "test_key", "test_value", tags=["a", "b"])
        r = mem.retrieve(tmp, "test_key")
        assert r is not None
        assert r["value"] == "test_value"
        assert "a" in r["tags"]
    print("  test_memory_store_and_retrieve: PASS")

def test_memory_update():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        mem.store(tmp, "k", "v1")
        mem.store(tmp, "k", "v2")
        r = mem.retrieve(tmp, "k")
        assert r["value"] == "v2"
    print("  test_memory_update: PASS")

def test_memory_missing_key():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        assert mem.retrieve(tmp, "nonexistent") is None
    print("  test_memory_missing_key: PASS")

def test_memory_search_by_tag():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        mem.store(tmp, "a", "value_a", tags=["identity"])
        mem.store(tmp, "b", "value_b", tags=["task"])
        mem.store(tmp, "c", "value_c", tags=["identity", "task"])
        results = mem.search_by_tag(tmp, "identity")
        keys = [r["key"] for r in results]
        assert "a" in keys
        assert "c" in keys
        assert "b" not in keys
    print("  test_memory_search_by_tag: PASS")

def test_memory_recent():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        for i in range(5):
            mem.store(tmp, f"key_{i}", f"val_{i}")
            time.sleep(0.02)
        results = mem.recent(tmp, n=3)
        assert len(results) == 3
        assert results[0]["key"] == "key_4"
    print("  test_memory_recent: PASS")

def test_memory_delete():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        mem.store(tmp, "to_delete", "value")
        assert mem.delete(tmp, "to_delete") == True
        assert mem.retrieve(tmp, "to_delete") is None
        assert mem.delete(tmp, "nonexistent") == False
    print("  test_memory_delete: PASS")

def test_memory_count():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        assert mem.count(tmp) == 0
        mem.store(tmp, "a", "1")
        mem.store(tmp, "b", "2")
        assert mem.count(tmp) == 2
    print("  test_memory_count: PASS")

# ── init tests ───────────────────────────────────────────────────────

def test_init_volume_creates_structure():
    with tempfile.TemporaryDirectory() as tmp:
        vol = os.path.join(tmp, "mind")
        init_volume(vol, REPO_ROOT)
        assert os.path.exists(os.path.join(vol, "editable-prompt.md"))
        assert os.path.exists(os.path.join(vol, "memory.db"))
        assert os.path.exists(os.path.join(vol, "journal.jsonl"))
        assert os.path.exists(os.path.join(vol, "skills"))
    print("  test_init_volume_creates_structure: PASS")

def test_init_volume_seeds_birth_memory():
    with tempfile.TemporaryDirectory() as tmp:
        vol = os.path.join(tmp, "mind")
        init_volume(vol, REPO_ROOT)
        r = mem.retrieve(vol, "birth")
        assert r is not None
        assert "identity" in r["tags"]
    print("  test_init_volume_seeds_birth_memory: PASS")

def test_init_volume_seeds_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        vol = os.path.join(tmp, "mind")
        init_volume(vol, REPO_ROOT)
        prompt = open(os.path.join(vol, "editable-prompt.md")).read()
        assert "creature" in prompt.lower()
    print("  test_init_volume_seeds_prompt: PASS")

def test_volume_is_initialised():
    with tempfile.TemporaryDirectory() as tmp:
        vol = os.path.join(tmp, "mind")
        assert not volume_is_initialised(vol)
        init_volume(vol, REPO_ROOT)
        assert volume_is_initialised(vol)
    print("  test_volume_is_initialised: PASS")

def test_init_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        vol = os.path.join(tmp, "mind")
        init_volume(vol, REPO_ROOT)
        mem.store(vol, "test_persistence", "should survive reinit")
        init_volume(vol, REPO_ROOT)  # second call
        r = mem.retrieve(vol, "test_persistence")
        assert r is not None, "memory wiped by second init"
        assert r["value"] == "should survive reinit"
    print("  test_init_idempotent: PASS")


def test_memory_layers():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        # Write 7 entries
        for i in range(7):
            mem.store(tmp, f"key_{i}", f"value number {i} with some text")
            time.sleep(0.01)
        # Layer 1: last 5
        l1 = mem.layer1(tmp)
        assert len(l1) == 5
        assert l1[0]["key"] == "key_6"   # most recent first
        assert l1[4]["key"] == "key_2"
        # Layer 2: entries 6-50 (entries 0 and 1 here)
        l2 = mem.layer2_headlines(tmp)
        assert len(l2) == 2
        assert l2[0]["key"] == "key_1"
        assert len(l2[0]["headline"]) <= 120
        # Layer 3: empty (need 51+ entries)
        l3 = mem.layer3_themes(tmp)
        assert l3 == []
    print("  test_memory_layers: PASS")


def test_memory_recall():
    with tempfile.TemporaryDirectory() as tmp:
        mem.init_db(tmp)
        mem.store(tmp, "docker_limits", "docker command not found inside container", tags=["discovery"])
        mem.store(tmp, "growth_plan", "build memory manager first", tags=["plan"])
        mem.store(tmp, "python_version", "python3.11 available", tags=["discovery"])
        results = mem.recall(tmp, "docker")
        assert len(results) == 1
        assert results[0]["key"] == "docker_limits"
        results = mem.recall(tmp, "discovery")
        assert len(results) == 2
    print("  test_memory_recall: PASS")


if __name__ == "__main__":
    print("Running volume tests...")
    test_memory_store_and_retrieve()
    test_memory_update()
    test_memory_missing_key()
    test_memory_search_by_tag()
    test_memory_recent()
    test_memory_delete()
    test_memory_count()
    test_init_volume_creates_structure()
    test_init_volume_seeds_birth_memory()
    test_init_volume_seeds_prompt()
    test_volume_is_initialised()
    test_init_idempotent()
    test_memory_layers()
    test_memory_recall()
    print("ALL PASS test_volume (14/14)")
