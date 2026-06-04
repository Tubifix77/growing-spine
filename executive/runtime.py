"""runtime.py — wake/sleep logic, death detection, respawn with death-log."""
import asyncio, os, time, subprocess
from . import sandbox, journal
from volume import savegame


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
    """
    Calculate seconds to sleep until the earliest provider quota resets.
    Returns at most 3600s (1 hour) to avoid sleeping past a reset.
    """
    min_reset = None
    now = time.time()
    for p in keychain.providers:
        state = keychain.state.get(p["key"], {})
        reset_at = state.get("reset_at", now + 3600)
        if min_reset is None or reset_at < min_reset:
            min_reset = reset_at
    if min_reset is None or min_reset <= now:
        return 60  # short nap, something's wrong
    return min(min_reset - now, 86400)  # cap at 24h, not 1h


async def wake_entry(volume_mount: str, keychain):
    """Log a coherent wake entry with budget info."""
    available = keychain.available_providers()
    provider_names = [p["key"] for p in available]
    budget_info = ", ".join(
        f"{p['key']}: {p['quota']['limit'] - keychain.state.get(p['key'], {}).get('used', 0)} remaining"
        for p in available
    ) or "none"
    msg = (
        f"Resumed. Available providers: {provider_names}. "
        f"Cognitive budget: {budget_info}."
    )
    journal.append(volume_mount, "wake", msg)
    print(f"[runtime] Wake: {msg}")


async def sleep_entry(volume_mount: str, keychain, reason: str = "quota exhausted"):
    """Log a coherent sleep entry with next-wake estimate."""
    secs = sleep_duration_seconds(keychain)
    wake_at = time.strftime("%Y-%m-%d %H:%M UTC",
                            time.gmtime(time.time() + secs))
    msg = f"Pausing. Reason: {reason}. Earliest budget return: {wake_at}."
    journal.append(volume_mount, "sleep", msg)
    print(f"[runtime] Sleep: {msg}")
    return secs
