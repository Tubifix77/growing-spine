"""One answer to "where is the mind?".

Audit P2-F13: five independent derivations existed -- loop.py, embed_gate.py
(the only env-aware one), observer.py, scripts/spine_health.py and
scripts/replay_gate.py each rebuilt the same `expanduser("~/growing-spine-mind")`
string. They agreed only because the literal was copied correctly five times, and
the test harness has to repoint loop's copy by walking the module namespace. One
mover breaks the others silently: exactly the shape that let the hollow-stub
markers drift for weeks.

VOLUME_MOUNT wins when set, so the test harness and the container agree with the
host without anyone special-casing either.
"""
import os

DEFAULT_MIND = "~/growing-spine-mind"


def mind_root() -> str:
    """Absolute path to the mind volume."""
    return os.environ.get("VOLUME_MOUNT") or os.path.expanduser(DEFAULT_MIND)
