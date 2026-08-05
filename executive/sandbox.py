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
    _api_env = []
    try:
        import yaml as _yaml
        _cfg = _yaml.safe_load(open(os.path.expanduser("~/growing-spine/config.yaml")))
        for _name, _val in container_api_env(_cfg).items():
            _api_env += ["-e", f"{_name}={_val}"]
    except Exception:
        pass  # best-effort — container still starts without keys

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
    return r.stdout, r.stderr, r.returncode


def respawn(dockerfile_dir: str = "."):
    """Kill and restart the container. Mind volume persists."""
    stop()
    time.sleep(2)
    # remove stopped container if --rm didn't catch it
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    start(dockerfile_dir)
