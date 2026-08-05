"""self_restart.py -- v0.7 self-expansion safety net.

Lets the creature reload its own brain (the executive) by requesting a restart,
with a rollback-and-learn net underneath:

  * The creature edits its own code, then calls the `request-restart` tool, which
    writes a request flag (request_restart()).
  * The executive, seeing the flag, validates (compile+tests), snapshots a
    KNOWN-GOOD save "A" (recording the brain commit), records that a self-restart
    into state "B" is in flight, then exits. systemd (Restart=always) brings the
    new code up.
  * boot_check() runs at the TOP of every executive start. If it sees a
    self-restart was in flight and the process keeps dying (crash-loop) OR the
    new code won't import, it RESTORES brain to save A, computes the git diff
    A..B, writes "you crashed, restored to A, the change that killed you was:
    [diff]" into the creature's chat, and clears the flag. systemd then brings up
    the reverted (working) code.

State lives in <volume>/self_restart_state.json so it survives process death.
"""
import json, os, time

STATE_FILE = "self_restart_state.json"
REQUEST_FILE = "restart_request.flag"
CRASH_LIMIT = 3          # this many starts within the window after a self-restart = crash-loop
CRASH_WINDOW_SEC = 90    # ...counted within this many seconds of the self-restart


def _sp(volume_mount, name):
    return os.path.join(volume_mount, name)

def _load(volume_mount):
    try:
        with open(_sp(volume_mount, STATE_FILE), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(volume_mount, d):
    try:
        # atomic: this file arms the crash-rollback net; a truncated write here
        # is a disarmed net that looks armed
        from executive import journal as _j
        _j.atomic_json(_sp(volume_mount, STATE_FILE), d, indent=2)
    except Exception:
        pass


# ---- called by the creature's tool (host side) ----------------------------
def request_restart(volume_mount, reason=""):
    """Creature asks for a brain reload. Just drops a flag; the executive acts
    on it at the end of the current cycle."""
    with open(_sp(volume_mount, REQUEST_FILE), "w", encoding="utf-8") as f:
        f.write(reason or "self-requested restart")

def has_request(volume_mount):
    return os.path.exists(_sp(volume_mount, REQUEST_FILE))

def clear_request(volume_mount):
    try:
        os.remove(_sp(volume_mount, REQUEST_FILE))
    except Exception:
        pass


# ---- the validate+snapshot+arm step, run before honoring a restart ---------
def prepare_and_arm(volume_mount, savegame_root, container_name, savegame):
    """Validate the current (creature-edited) brain, snapshot a known-good save,
    and arm the crash-loop detector. Returns (ok, message). On failure the caller
    should NOT restart -- it tells the creature why and stays on current code."""
    import subprocess, sys
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1) compile-check every python file in the executive
    rc = subprocess.run([sys.executable, "-m", "py_compile",
                         os.path.join(repo, "main.py")],
                        capture_output=True, text=True)
    if rc.returncode != 0:
        return False, "Your brain edit does not compile:\n" + rc.stderr[:800]
    for root, _, files in os.walk(os.path.join(repo, "executive")):
        for fn in files:
            if fn.endswith(".py"):
                r = subprocess.run([sys.executable, "-m", "py_compile",
                                    os.path.join(root, fn)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    return False, f"{fn} does not compile:\n" + r.stderr[:800]

    # 2) run the test suite if present (fast guard against logic breakage)
    testfile = os.path.join(repo, "tests", "test_loop_v2.py")
    if os.path.exists(testfile):
        r = subprocess.run([sys.executable, testfile],
                           capture_output=True, text=True, cwd=repo, timeout=120)
        if "ALL TESTS PASS" not in r.stdout:
            tail = (r.stdout[-600:] + r.stderr[-600:])
            return False, "Your brain edit fails the test suite:\n" + tail

    # 3) snapshot a known-good save A (this also commits the creature's edit, so
    #    B = the committed edit, A = ... wait: we want A = last good BEFORE this
    #    edit. So record the PRE-edit commit as good, THEN snapshot.
    good_commit = savegame.brain_commit()  # current HEAD (pre-snapshot)
    # snapshot_brain inside save() will commit the edit -> that becomes B
    meta = savegame.save(volume_mount, savegame_root, container_name,
                         label="pre-self-restart", milestone=False)
    b_commit = meta.get("brain_commit")

    # 4) arm: record that a self-restart into B is in flight, with good=A
    st = _load(volume_mount)
    st["in_flight"] = True
    st["good_commit"] = good_commit
    st["bad_commit"] = b_commit
    st["armed_at"] = time.time()
    st["starts_since_arm"] = 0
    st["good_save_tag"] = meta.get("tag")
    _save(volume_mount, st)
    return True, "validated + snapshotted; restarting"


# ---- boot-time check, run at the TOP of every executive start --------------
def boot_check(volume_mount, savegame, chat):
    """Detect a crash-looping self-restart and roll back with a learning diff.
    Returns True if a rollback was performed (caller should exit so systemd
    restarts into the reverted code)."""
    st = _load(volume_mount)
    if not st.get("in_flight"):
        return False

    st["starts_since_arm"] = st.get("starts_since_arm", 0) + 1
    elapsed = time.time() - st.get("armed_at", 0)
    _save(volume_mount, st)

    # healthy: if we've been up and this is only the first/second clean start
    # well past the crash window, consider the self-restart a SUCCESS and disarm.
    if elapsed > CRASH_WINDOW_SEC and st["starts_since_arm"] <= CRASH_LIMIT:
        st["in_flight"] = False
        _save(volume_mount, st)
        return False

    # crash-loop: too many starts inside the window -> the new brain is bad.
    if st["starts_since_arm"] >= CRASH_LIMIT and elapsed <= CRASH_WINDOW_SEC:
        good = st.get("good_commit")
        bad = st.get("bad_commit")
        diff = savegame.brain_diff(good, bad) if good else "(no good commit recorded)"
        savegame.restore_brain(good)
        msg = (
            "## You crashed your own brain and were rolled back.\n\n"
            "You edited your executive and restarted, but the new code crash-looped. "
            f"You have been restored to the last good save ({st.get('good_save_tag','?')}). "
            "Your memory and tools are intact.\n\n"
            "The change you made that caused the crash (good -> crashed diff) was:\n\n"
            "```diff\n" + diff + "\n```\n\n"
            "Learn from this: the edit above broke startup. Make a smaller, safer "
            "change next time, and test before restarting."
        )
        try:
            chat.enqueue(volume_mount, msg)
        except Exception:
            # fallback: drop it where the creature will see it
            try:
                with open(_sp(volume_mount, "LAST_CRASH.md"), "w", encoding="utf-8") as f:
                    f.write(msg)
            except Exception:
                pass
        st["in_flight"] = False
        _save(volume_mount, st)
        return True

    return False
