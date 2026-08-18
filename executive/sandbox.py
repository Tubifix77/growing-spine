"""sandbox.py — manage the creature's Docker container (mortal body)."""
import subprocess, base64, time

CONTAINER_NAME = "growing-spine-body"
IMAGE_NAME = "growing-spine"


# Legacy env names the creature's OWN tools already reference by hand. Renaming
# these would silently break its world, so they are emitted as aliases forever.
LEGACY_KEY_ALIASES = {
    "groq":         "GROQ_API_KEY",
    "cerebras":     "CEREBRAS_API_KEY",
    "gemini_flash": "GEMINI_API_KEY",
}


def _complain(msg: str):
    """Say it on stdout AND in the creature's journal. A keyless body is a silent
    disability otherwise: every provider call from inside the container just fails."""
    print(f"[sandbox] {msg}")
    try:
        from executive import journal as _j
        _j.append(os.path.expanduser("~/growing-spine-mind"), "error",
                  f"sandbox: {msg}")
    except Exception:
        pass


def env_name_for(provider_key: str) -> str:
    """Canonical container env var name for a config provider key."""
    # str(): a bare off/on/yes/no key arrives from YAML as a bool ("Norway problem").
    safe = "".join(c if c.isalnum() else "_" for c in str(provider_key))
    return safe.upper() + "_API_KEY"


def container_api_env(cfg: dict) -> dict:
    """Env vars carrying provider keys into the body, so bash tools can call an
    API without Python or the keychain.

    Was a hardcoded three-entry map keyed on "groq"/"gemini"/"cerebras" while the
    config keys are gemini_flash/groq/groq_oss120/cerebras/google_gemma/
    openrouter_* -- so exactly TWO of thirteen providers ever reached the body,
    and gemini_flash missed by a suffix (2026-08-06). Now derived from the config,
    so a rung added tomorrow arrives the day it lands.

    DISABLED providers are deliberately excluded: a benched key has no business
    inside the container.
    """
    out = {}
    for prov in cfg.get("providers", []):
        key, api_key = str(prov.get("key", "")), prov.get("api_key", "")
        if not key or not api_key or not prov.get("enabled", True):
            continue
        out[env_name_for(key)] = api_key
        alias = LEGACY_KEY_ALIASES.get(key)
        if alias:
            out[alias] = api_key
    return out


def build_image(dockerfile_dir: str = "."):
    subprocess.run(["docker", "build", "-t", IMAGE_NAME, dockerfile_dir], check=True)


def is_running() -> bool:
    r = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
        capture_output=True, text=True
    )
    return r.stdout.strip() == "true"


def start(dockerfile_dir: str = "."):
    """Start the container if not already running."""
    if is_running():
        return
    # ensure image exists
    r = subprocess.run(["docker", "image", "inspect", IMAGE_NAME],
                       capture_output=True)
    if r.returncode != 0:
        build_image(dockerfile_dir)

    import os
    host_mind = os.path.expanduser("~/growing-spine-mind")
    host_ws = os.path.expanduser("~/growing-spine-workspace")
    os.makedirs(host_mind, exist_ok=True)
    os.makedirs(host_ws, exist_ok=True)
    # Read API keys from config so bash tools inside the container can use them
    # without needing Python or the keychain module.
    # Audit P1-F15: this hardcoded ~/growing-spine/config.yaml and swallowed every
    # failure with a bare `pass`, so a moved checkout or a YAML typo produced a body
    # with NO api keys, in total silence, and the creature's own tools would fail to
    # call any provider with no way to find out why. Derive the path from this file,
    # and say so loudly when the keys do not make it in.
    _api_env = []
    _cfg_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "config.yaml")
    try:
        import yaml as _yaml
        with open(_cfg_path, encoding="utf-8") as _cf:
            _cfg = _yaml.safe_load(_cf)
        _keys = container_api_env(_cfg)
        for _name, _val in _keys.items():
            _api_env += ["-e", f"{_name}={_val}"]
        if not _keys:
            _complain(f"config at {_cfg_path} yielded NO provider keys -- the body "
                      f"starts unable to call any API")
    except Exception as _ce:
        _complain(f"could not read {_cfg_path} ({type(_ce).__name__}: {_ce}) -- the "
                  f"body starts with NO api keys")

    subprocess.run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "--rm",  # auto-remove when stopped — safe now, all data is on host binds
        "--user", f"{os.getuid()}:{os.getgid()}",  # run as host user — files written to
                                                    # bind-mounts are host-user-owned from
                                                    # birth; eliminates root-owned tool files
        "-v", f"{host_mind}:/mind",            # curated durable mind (memory, prompts, tools)
        "-v", f"{host_ws}:/workspace",         # the creature's persistent build space
        "--network", "bridge",
        "--memory", "1g",          # hard cap — prevent OOM kills of host
        "--memory-swap", "1g",     # no swap either — fail fast inside container
        "--cpus", "1.5",           # leave headroom for host OS and observer
        # PID 1 must REAP. Without this the container's init is `sleep infinity`,
        # which never calls wait(), so every tool process orphaned inside the body
        # -- anything backgrounded, anything whose parent exits first -- becomes a
        # permanent zombie. Measured 2026-08-18: 9,082 zombies accumulated between
        # 08-16 20:20 and 08-18 04:11, at which point pids.current hit 9085 against
        # a pids.max of 9090 and the body could no longer fork AT ALL. `docker exec`
        # returned "procReady not received" for three and a half hours while
        # `docker inspect` still reported Running=true. --init puts tini at PID 1
        # (sleep infinity becomes its child) and tini reaps.
        "--init",
    ] + _api_env + [
        IMAGE_NAME,
        "sleep", "infinity"
    ], check=True)
    time.sleep(1)
    # Ensure python->python3 and the tool dirs exist, regardless of how old the
    # image is (the Dockerfile bakes these in for fresh builds; this covers the rest).
    subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "bash", "-c",
         "mkdir -p /mind/tools/framework /mind/tools/own; "
         "git config --global --replace-all safe.directory '*' 2>/dev/null || true"],
        check=False
    )


def stop():
    subprocess.run(["docker", "stop", CONTAINER_NAME],
                   capture_output=True)


def run_command(cmd: str) -> tuple:
    """
    Execute cmd inside the container via base64 (VibeOS pattern).
    Returns (stdout, stderr, exit_code).
    """
    enc = base64.b64encode(cmd.encode()).decode()
    pathline = 'export PATH="/mind/tools/framework:/mind/tools/own:$PATH"; '
    r = subprocess.run(
        ["docker", "exec", CONTAINER_NAME,
         "bash", "-c", pathline + f"echo {enc} | base64 -d | bash"],
        capture_output=True, text=True, errors="replace", timeout=300
    )
    out, err, code = r.stdout, r.stderr, r.returncode
    if exec_setup_failure(out, err, code):
        # The command never RAN. Docker's own diagnostic must not be delivered as
        # the command's answer: on 2026-08-18 `echo alive` returned exit 128 with
        # "OCI runtime exec failed: ... procReady not received" ON STDOUT, so the
        # creature received infrastructure breakage shaped exactly like output,
        # for three and a half hours. Same contract as framework-tools/ask:
        # stdout is the answer or it is EMPTY, and every failure names itself on
        # stderr. Keep the diagnostic -- discarding it is how a silent outage gets
        # built -- but move it to the channel that means failure.
        return "", (out + err).strip() or "container exec failed", code
    return out, err, code


# Docker CLI signatures for "the container could not start your process", as
# opposed to "your process ran and failed". Matched on the docker/OCI wording
# rather than on exit code alone, because 125-128 are also legitimate exit codes
# for a command that really did run (`bash -c 'exit 127'`).
_EXEC_SETUP_MARKERS = (
    "oci runtime exec failed",
    "error response from daemon",
    "procready not received",
    "cannot exec in a stopped",
    "is not running",
    "no such container",
    "resource temporarily unavailable",
)


def exec_setup_failure(stdout: str, stderr: str, code: int) -> bool:
    """True when the container refused to START the process at all.

    Canonical: both run_command (to keep it off stdout) and body_responds (to
    decide the body is dead) ask this one question, so the producer and the
    checker cannot drift apart -- the central lesson of this codebase.
    """
    if code == 0:
        return False
    blob = ((stdout or "") + " " + (stderr or "")).lower()
    return any(m in blob for m in _EXEC_SETUP_MARKERS)


def body_responds(timeout: int = 20) -> tuple:
    """Prove the body can execute, by executing. Returns (ok, detail).

    `docker inspect .State.Running` is NOT liveness. A container whose PID
    namespace is full is Running=true and cannot fork a single process; that is
    how the body stayed "alive" for three and a half hours on 2026-08-18 while
    every tool call the creature made came back as a docker error string. Ask the
    body to do something and see whether it does.
    """
    try:
        r = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "true"],
            capture_output=True, text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "exec probe timed out after %ds" % timeout
    except OSError as e:
        return False, "could not run docker: %s: %s" % (type(e).__name__, e)
    if r.returncode == 0:
        return True, ""
    detail = " ".join((r.stdout + " " + r.stderr).split())[:200]
    return False, "exec probe exit %d: %s" % (r.returncode, detail)


def respawn(dockerfile_dir: str = "."):
    """Kill and restart the container. Mind volume persists."""
    stop()
    time.sleep(2)
    # remove stopped container if --rm didn't catch it
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    start(dockerfile_dir)
