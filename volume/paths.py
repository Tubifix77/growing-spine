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


DEFAULT_WORKSPACE = "~/growing-spine-workspace"


def workspace_root() -> str:
    """Absolute host path to the creature's workshop (/workspace in the body)."""
    return os.environ.get("WORKSPACE_MOUNT") or os.path.expanduser(DEFAULT_WORKSPACE)


# Where executive/sandbox.py mounts each host root inside the body.
CONTAINER_MOUNTS = ("/mind", "/workspace")


def to_host(path: str, mind: str = None, workspace: str = None) -> str:
    """A CONTAINER path (`/mind/...`, `/workspace/...`) as the host sees it.
    Anything else is returned unchanged. Matches whole path segments only, so
    `/mindful` is not `/mind`."""
    roots = {"/mind": mind or mind_root(), "/workspace": workspace or workspace_root()}
    for mount in CONTAINER_MOUNTS:
        if path == mount or path.startswith(mount + "/"):
            return roots[mount] + path[len(mount):]
    return path


def host_path(path: str, mind: str = None, workspace: str = None, hops: int = 8) -> str:
    """The host file a tool path really is, following links the way the BODY would.

    2026-09-27: the creature replaced `tools/own/subagent_ask_helper` with a link
    to `/workspace/subagent_ask_helper_mock`. Inside the body that resolves; on the
    host `/workspace` does not exist, so the link DANGLED and every host-side
    reader skipped the tool as if it were gone. The dependency graph lost the
    helper and all 258 edges into it (edges/tool read 1.26 against a true 1.60),
    the retired-reach scan fell from 426 tools to 38, and nothing said why --
    a plausible wrong number, the house disease. Invariant: the host sees each
    tool as the container does. Relative links resolve against the link's
    directory; container-absolute ones map through `to_host`. Bounded, so a
    link loop ends rather than spins."""
    p = path
    for _ in range(hops):
        try:
            if not os.path.islink(p):
                return p
            t = os.readlink(p)
        except OSError:
            return p
        p = to_host(t, mind, workspace) if t.startswith("/") else \
            os.path.join(os.path.dirname(p), t)
    return p
