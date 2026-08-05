"""test_keychain.py — tests for keychain quota state logic"""
import sys, os, json, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Patch STATE_FILE to a temp location before importing
import keychain.quota_state as qs

FAKE_PROVIDERS = [
    {
        "key": "provider_a",
        "enabled": True,
        "quota": {"type": "daily", "limit": 100, "resets": "00:00 UTC"},
    },
    {
        "key": "provider_b",
        "enabled": True,
        "quota": {"type": "daily", "limit": 50, "resets": "00:00 UTC"},
    },
    {
        "key": "provider_c",
        "enabled": False,
        "quota": {"type": "daily", "limit": 100, "resets": "00:00 UTC"},
    },
]

def test_load_state_fresh():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        assert "provider_a" in state
        assert "provider_b" in state
        assert state["provider_a"]["used"] == 0
    print("  test_load_state_fresh: PASS")

def test_is_available():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        assert qs.is_available(state, "provider_a", FAKE_PROVIDERS[0]) == True
        assert qs.is_available(state, "provider_c", FAKE_PROVIDERS[2]) == False
    print("  test_is_available: PASS")

def test_record_usage_exhausts():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        qs.record_usage(state, "provider_b", 50)
        assert qs.is_available(state, "provider_b", FAKE_PROVIDERS[1]) == False
    print("  test_record_usage_exhausts: PASS")

def test_state_persists():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        qs.record_usage(state, "provider_a", 42)
        # reload
        state2 = qs.load_state(FAKE_PROVIDERS)
        assert state2["provider_a"]["used"] == 42
    print("  test_state_persists: PASS")

def test_partial_usage_still_available():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        qs.record_usage(state, "provider_a", 99)
        assert qs.is_available(state, "provider_a", FAKE_PROVIDERS[0]) == True
        qs.record_usage(state, "provider_a", 1)
        assert qs.is_available(state, "provider_a", FAKE_PROVIDERS[0]) == False
    print("  test_partial_usage_still_available: PASS")

def test_reset_on_past_reset_time():
    with tempfile.TemporaryDirectory() as tmp:
        qs.STATE_FILE = os.path.join(tmp, "quota_state.json")
        state = qs.load_state(FAKE_PROVIDERS)
        # manually set reset_at to the past and used to limit
        state["provider_a"]["used"] = 100
        state["provider_a"]["reset_at"] = time.time() - 1
        qs.save_state(state)
        # reload should roll over
        state2 = qs.load_state(FAKE_PROVIDERS)
        assert state2["provider_a"]["used"] == 0
    print("  test_reset_on_past_reset_time: PASS")

if __name__ == "__main__":
    print("Running keychain quota tests...")
    test_load_state_fresh()
    test_is_available()
    test_record_usage_exhausts()
    test_state_persists()
    test_partial_usage_still_available()
    test_reset_on_past_reset_time()
    print("ALL PASS test_keychain (6/6)")
