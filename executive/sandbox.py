"""sandbox.py — manage the creature's Docker container (mortal body)."""
import subprocess, base64, time

CONTAINER_NAME = "growing-spine-body"
IMAGE_NAME = "growing-spine"
VOLUME_NAME = "growing-spine-mind"


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
    subprocess.run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "--rm",  # auto-remove when stopped — safe now, all data is on host binds
        "-v", f"{host_mind}:/mind",            # curated durable mind (memory, prompts, tools)
        "-v", f"{host_ws}:/workspace",         # the creature's persistent build space
        "--network", "bridge",
        IMAGE_NAME,
        "sleep", "infinity"
    ], check=True)
    time.sleep(1)
    # Ensure python->python3 and the tool dirs exist, regardless of how old the
    # image is (the Dockerfile bakes these in for fresh builds; this covers the rest).
    subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "bash", "-c",
         "ln -sf /usr/bin/python3 /usr/local/bin/python; "
         "mkdir -p /mind/tools/framework /mind/tools/own"],
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
        capture_output=True, text=True, timeout=300
    )
    return r.stdout, r.stderr, r.returncode


def respawn(dockerfile_dir: str = "."):
    """Kill and restart the container. Mind volume persists."""
    stop()
    time.sleep(2)
    # remove stopped container if --rm didn't catch it
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    start(dockerfile_dir)
