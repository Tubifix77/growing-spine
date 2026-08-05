"""test_runtime.py — tests for executive/runtime.py"""
import sys, os, tempfile, time, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from executive.runtime import (
    _is_risky_command, _death_log_entry, sleep_duration_seconds, wake_entry, sleep_entry
)
from executive import journal

# ── risky command detection ──────────────────────────────────────────

def test_risky_sudo():
    assert _is_risky_command("sudo apt install vim") == True
    print("  test_risky_sudo: PASS")

def test_risky_rm_rf():
    assert _is_risky_command("rm -rf /tmp/stuff") == True
    print("  test_risky_rm_rf: PASS")

def test_risky_apt_remove():
    assert _is_risky_command("apt remove python3") == True
    print("  test_risky_apt_remove: PASS")

def test_safe_commands():
    assert _is_risky_command("echo hello") == False
    assert _is_risky_command("python3 script.py") == False
    assert _is_risky_command("ls -la /mind") == False
    assert _is_risky_command("curl https://example.com") == False
    print("  test_safe_commands: PASS")

# ── death log ────────────────────────────────────────────────────────

def test_death_log_written():
    with tempfile.TemporaryDirectory() as tmp:
        _death_log_entry(tmp, "rm -rf /workspace", "container stopped")
        entries = journal.recent(tmp, n=5)
        assert len(entries) == 1
        assert entries[0]["kind"] == "respawn"
        assert "rm -rf" in entries[0]["content"]
        assert "memory is whole" in entries[0]["content"]
    print("  test_death_log_written: PASS")

def test_death_log_empty_last_cmd():
    with tempfile.TemporaryDirectory() as tmp:
        _death_log_entry(tmp, "", "container stopped")
        entries = journal.recent(tmp, n=5)
        assert "unknown" in entries[0]["content"]
    print("  test_death_log_empty_last_cmd: PASS")

# ── sleep duration ────────────────────────────────────────────────────

class FakeKeychain:
    def __init__(self, reset_offsets):
        """reset_offsets: list of seconds from now until reset."""
        now = time.time()
        self.providers = [{"key": f"p{i}"} for i in range(len(reset_offsets))]
        self.state = {
            f"p{i}": {"reset_at": now + offset}
            for i, offset in enumerate(reset_offsets)
        }

def test_sleep_duration_picks_minimum():
    kc = FakeKeychain([7200, 3600, 5400])
    secs = sleep_duration_seconds(kc)
    assert 3590 <= secs <= 3601, f"expected ~3600, got {secs}"
    print("  test_sleep_duration_picks_minimum: PASS")

def test_sleep_duration_capped_at_3600():
    kc = FakeKeychain([7200, 9000])
    secs = sleep_duration_seconds(kc)
    assert secs == 3600
    print("  test_sleep_duration_capped_at_3600: PASS")

def test_sleep_duration_past_reset():
    kc = FakeKeychain([-100])  # reset already passed
    secs = sleep_duration_seconds(kc)
    assert secs == 60  # short nap fallback
    print("  test_sleep_duration_past_reset: PASS")

# ── wake / sleep journal entries ─────────────────────────────────────

def test_wake_entry_written():
    with tempfile.TemporaryDirectory() as tmp:
        import executive.loop as loop
        loop.VOLUME_MOUNT = tmp

        class MinimalKeychain:
            providers = [{"key": "gemini", "quota": {"limit": 100}}]
            state = {"gemini": {"used": 30, "reset_at": time.time() + 3600}}
            def available_providers(self):
                return self.providers

        asyncio.run(wake_entry(tmp, MinimalKeychain()))
        entries = journal.recent(tmp, n=5)
        assert any(e["kind"] == "wake" for e in entries)
        wake = next(e for e in entries if e["kind"] == "wake")
        assert "gemini" in wake["content"]
    print("  test_wake_entry_written: PASS")

def test_sleep_entry_written():
    with tempfile.TemporaryDirectory() as tmp:
        import executive.loop as loop
        loop.VOLUME_MOUNT = tmp

        # Build keychain with named provider matching state key
        kc = FakeKeychain([1800])  # p0 resets in 1800s

        async def _run():
            return await sleep_entry(tmp, kc, reason="quota exhausted")

        secs = asyncio.run(_run())
        entries = journal.recent(tmp, n=5)
        assert any(e["kind"] == "sleep" for e in entries)
        slp = next(e for e in entries if e["kind"] == "sleep")
        assert "quota exhausted" in slp["content"]
        assert secs <= 3600  # capped at 3600 max
    print("  test_sleep_entry_written: PASS")

if __name__ == "__main__":
    print("Running runtime tests...")
    test_risky_sudo()
    test_risky_rm_rf()
    test_risky_apt_remove()
    test_safe_commands()
    test_death_log_written()
    test_death_log_empty_last_cmd()
    test_sleep_duration_picks_minimum()
    test_sleep_duration_capped_at_3600()
    test_sleep_duration_past_reset()
    test_wake_entry_written()
    test_sleep_entry_written()
    print("ALL PASS test_runtime (11/11)")
