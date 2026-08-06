"""runtime.py — wake/sleep logic, death detection, respawn with death-log."""
import asyncio, os, time, subprocess
from . import sandbox, journal
from volume import savegame
from volume import tools as toolmod
from volume import memory as mem


def _death_log_entry(volume_mount: str, last_cmd: str, cause: str):
    """Write the death-log message the creature reads on respawn."""
    msg = (
        f"Your previous body died. "
        f"Cause: {cause}. "
        f"The last thing you did was: {last_cmd[:300] if last_cmd else 'unknown'}. "
        f"You have come back. Your memory is whole, but some changes to your "
        f"surroundings may be gone."
    )
    journal.append(volume_mount, "respawn", msg)


def _is_risky_command(cmd: str) -> bool:
    """Detect commands that warrant a pre-emptive savegame."""
    risk_patterns = [
        "sudo ", "apt remove", "apt purge", "pip uninstall",
        "rm -rf", "rm -r /", "chmod 000", "dd if=",
        "> /dev/", "mkfs", "fdisk", "parted",
    ]
    cmd_lower = cmd.lower()
    return any(p in cmd_lower for p in risk_patterns)


async def managed_exec(cmd: str, volume_mount: str, savegame_root: str,
                       container_name: str) -> tuple:
    """
    Execute a command with savegame pre-emption for risky ops.
    Returns (stdout, stderr, exit_code).
    """
    if _is_risky_command(cmd):
        journal.append(volume_mount, "savegame_preemptive",
                       f"Risky command detected, saving before exec: {cmd[:200]}")
        savegame.save(volume_mount, savegame_root, container_name,
                      label="pre-risky", milestone=False)

    stdout, stderr, code = sandbox.run_command(cmd)
    return stdout, stderr, code


async def ensure_body(volume_mount: str, savegame_root: str,
                      dockerfile_dir: str, last_cmd: str = "") -> bool:
    """
    Check container is running; respawn if not.
    Returns True if body is alive (or was successfully respawned).
    """
    if sandbox.is_running():
        return True

    cause = "container stopped unexpectedly"
    print(f"[runtime] Body death detected. Respawning...")
    journal.append(volume_mount, "death", f"Body died. Last cmd: {last_cmd[:200]}")

    try:
        sandbox.respawn(dockerfile_dir)
        _death_log_entry(volume_mount, last_cmd, cause)
        print(f"[runtime] Body respawned.")
        return True
    except Exception as e:
        journal.append(volume_mount, "error", f"Respawn failed: {e}")
        print(f"[runtime] Respawn failed: {e}")
        return False


def sleep_duration_seconds(keychain) -> float:
    """How long to sleep when exhausted.

    Uses `last_recovery_secs` -- the measured length of the most recent dark
    period, written by quota_state.mark_success when an outage ends -- else a
    conservative 1 hour. Floor of 60s to avoid hammering the API.

    2026-08-06 (audit P1-F10 / P2-F4 / P3-D5): this read `last_window_duration`,
    which NOTHING has ever written. So every call fell through to the flat 3600,
    and -- worse than dead code -- sleep_entry prints that fallback into the
    creature's own journal as `Earliest budget return: <time>`. The creature was
    being told a fabricated wake time as fact, which is why it could be seen
    "waking two minutes after" an hour-away estimate. Reading the key the writer
    actually writes makes the number true.
    """
    durations = []
    for p in keychain.providers:
        dur = keychain.state.get(p["key"], {}).get("last_recovery_secs")
        if dur and dur > 0:
            durations.append(dur)
    if durations:
        return max(60.0, min(durations) * 1.1)  # shortest known + 10% buffer
    return 3600  # no history yet — conservative hourly probe


async def wake_entry(volume_mount: str, keychain):
    """Restore framework tools, then log a coherent wake entry with budget info."""
    # Immutability by restoration: re-materialize the canonical framework
    # toolset onto the volume each wake, overwriting any prior-life tampering.
    try:
        toolmod.materialize_framework(volume_mount)
    except Exception as e:
        print(f"[runtime] framework materialize failed: {e}")

    from keychain import quota_state as qs
    available_names = [
        p["key"] for p in keychain.providers
        if p.get("enabled", True) and not qs.is_exhausted(keychain.state, p["key"])
    ]
    if available_names:
        msg = f"Resumed. Available providers: {available_names}."
    else:
        n = sum(1 for p in keychain.providers if p.get("enabled", True))
        msg = (f"Resumed. No providers believed available -- "
               f"will probe all {n} in case a window reopened.")
    journal.append(volume_mount, "wake", msg)
    print(f"[runtime] Wake: {msg}")


async def sleep_entry(volume_mount: str, keychain, reason: str = "quota exhausted"):
    """Log a coherent sleep entry with next-wake estimate. Auto-saves last thought."""
    secs = sleep_duration_seconds(keychain)
    wake_at = time.strftime("%Y-%m-%d %H:%M UTC",
                            time.gmtime(time.time() + secs))
    msg = f"Pausing. Reason: {reason}. Earliest budget return: {wake_at}."
    journal.append(volume_mount, "sleep", msg)
    print(f"[runtime] Sleep: {msg}")

    # Auto-remember last thought so creature wakes with continuity in layer 1
    try:
        last = journal.last_of_kind(volume_mount, "think_end")
        if last:
            mem.store(volume_mount,
                      key="last_thought",
                      value=last["content"],
                      tags=["auto", "continuity"])
    except Exception as e:
        print(f"[runtime] auto-remember failed: {e}")

    return secs
