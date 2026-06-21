"""main.py — entry point. Run on the Debian laptop host."""
import asyncio, os, sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

def check_config():
    cfg = os.path.join(REPO_ROOT, "config.yaml")
    if not os.path.exists(cfg):
        print("ERROR: config.yaml not found. Copy config.yaml.example and fill in your API keys.")
        sys.exit(1)

def init_volume():
    from executive.loop import VOLUME_MOUNT
    from volume.init import init_volume as _init, volume_is_initialised
    if not volume_is_initialised(VOLUME_MOUNT):
        print("[main] First run — initialising mind volume...")
        _init(VOLUME_MOUNT, REPO_ROOT)
    else:
        # still call init to ensure schema is current
        from volume.memory import init_db
        init_db(VOLUME_MOUNT)
        print("[main] Volume already initialised — ready.")

if __name__ == "__main__":
    check_config()
    init_volume()
    # v0.7: boot-time self-restart safety net. If a creature-triggered brain
    # reload crash-looped, roll the brain back to the last good save and tell
    # the creature what change killed it -- then exit so systemd restarts into
    # the reverted (working) code.
    try:
        from executive.loop import VOLUME_MOUNT
        from volume import savegame as _sg
        from executive import chat as _chat, self_restart as _sr
        if _sr.boot_check(VOLUME_MOUNT, _sg, _chat):
            print("[main] self-restart rollback performed; exiting for systemd to relaunch reverted code.")
            sys.exit(0)
    except Exception as _e:
        print(f"[main] boot_check skipped: {_e}")
    from executive.loop import run_forever
    asyncio.run(run_forever(dockerfile_dir=REPO_ROOT))
