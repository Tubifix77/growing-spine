"""sandbox.py — manage the creature's Docker container (mortal body)."""
import subprocess, base64, re, time

CONTAINER_NAME = "growing-spine-body"
IMAGE_NAME = "growing-spine"


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
    from volume.paths import workspace_root
    host_ws = workspace_root()
    os.makedirs(host_mind, exist_ok=True)
    os.makedirs(host_ws, exist_ok=True)
    # NO PROVIDER KEY ENTERS THE BODY (2026-09-26, Tue's decision). Until then
    # every enabled rung's key was injected as an env var so the creature's bash
    # tools could call an API without the keychain. The one thing in the body
    # still using them was the framework's own `ask`, which put a second model of the
    # same class as its own -- with none of its context -- behind 400 of its
    # tools; 53% of those calls returned no answer in September. `ask` is now a
    # tombstone (framework-tools/ask). Withholding the keys is the other half:
    # with `ask` gone and a key in reach, the illusion is one curl away, and a
    # direct call to google_gemma spends the 16,000 tokens/minute the creature
    # THINKS with. Verified before shipping: no tool of its own reads any of the
    # five keys that were present (GEMINI_API_KEY, GEMINI_FLASH_API_KEY,
    # GOOGLE_GEMMA_API_KEY, CLOUDFLARE_API_KEY, GROQ_OSS120_API_KEY).
    # Keys stay on the host, in config.yaml, read only by the keychain.
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


def exec_wrapper(cmd: str) -> str:
    """The `bash -c` string that runs one exec block inside the body.

    The block is decoded into a FILE and run from there with stdin EMPTY.
    It used to be `echo ENC | base64 -d | bash`, which hands bash the script
    ON STDIN -- so any command in the block that reads stdin swallowed the
    rest of the block. On 2026-09-29 09:55-10:06 the cloudflare rung wrote
    `tool-edit X` with no heredoc six times; each time tool-edit read the
    remaining lines of the block as the new file, comment first and shebang
    on line 3, `remember current-phase "done"` included -- six tools that
    cannot start, in thirteen minutes. Invariant: a command's stdin is never
    the script it is part of. With stdin empty, tool-edit's own guard
    ("Refusing to write empty content") answers the same mistake honestly.
    """
    enc = base64.b64encode(cmd.encode()).decode()
    return ('export PATH="/mind/tools/framework:/mind/tools/own:$PATH"; '
            'f=$(mktemp /tmp/.exec-block.XXXXXX) || exit 125; '
            'g=$(mktemp /tmp/.exec-failed.XXXXXX) || exit 125; '
            f'echo {enc} | base64 -d > "$f"; '
            f'echo {_FAILED_TRAP_B64} | base64 -d > "$g.env"; '
            'GS_FAILED="$g" BASH_ENV="$g.env" bash "$f" </dev/null; rc=$?; '
            f'printf \'\\036GS-FAILED %s\' "$(head -c {EXEC_FAILED_MAX_BYTES} "$g" '
            '| base64 -w0)" >&2; '
            'rm -f "$f" "$g" "$g.env"; exit $rc')


# WHICH command in a block failed (2026-10-02). A block is many commands and
# returns ONE exit code, its last one's -- so the done-gate could not see a
# failure inside the block that carries the done-mark (42 completions in 14
# days were accepted that way, 15 with an error in that block's output), and
# it quoted the first failing BLOCK, often a probe, instead of the run that
# mattered. bash sources BASH_ENV before the script, so the trap is installed
# without changing one line of the creature's file: exit codes, `$?`, `set -e`
# and bash's own `line N` messages are untouched, child scripts do not inherit
# it, and conditionals (`if`, `||`, `&&`) record nothing, by bash's own rule.
# The record travels back on stderr behind a marker and is stripped there, so
# the creature sees exactly what its commands printed.
_FAILED_TRAP = (
    "__gs_f=$GS_FAILED; unset GS_FAILED BASH_ENV\n"
    "set -o errtrace\n"
    "trap '__gs_rc=$?; printf \"%s\\t%s\\n\" \"$__gs_rc\" "
    "\"${BASH_COMMAND//[$'\"'\"'\\t\\n'\"'\"']/ }\" >> \"$__gs_f\"; "
    "(exit $__gs_rc)' ERR\n")
_FAILED_TRAP_B64 = base64.b64encode(_FAILED_TRAP.encode()).decode()
EXEC_FAILED_SENTINEL = "\x1eGS-FAILED "
EXEC_FAILED_MAX_BYTES = 65536
_last_failed = None


def split_failed(err: str):
    """(stderr as the commands wrote it, [(exit_code, command), ...] or None).
    None means the block's failures are UNKNOWN -- no record came back -- which
    is not the same as none failing, and callers must fall back to the exit code."""
    i = (err or "").rfind(EXEC_FAILED_SENTINEL)
    if i < 0:
        return err, None
    payload = err[i + len(EXEC_FAILED_SENTINEL):].strip()
    try:
        raw = base64.b64decode(payload).decode("utf-8", "replace") if payload else ""
    except Exception:
        return err[:i], None
    recs = []
    for line in raw.splitlines():
        rc, _, c = line.partition("\t")
        if rc.strip().isdigit():
            recs.append((int(rc.strip()), c.strip()))
    return err[:i], recs


def take_failed():
    """The failed commands of the last run_command, once. None = unknown."""
    global _last_failed
    out, _last_failed = _last_failed, None
    return out


def run_command(cmd: str) -> tuple:
    """
    Execute cmd inside the container via base64 (VibeOS pattern).
    Returns (stdout, stderr, exit_code).
    """
    global _last_failed
    _last_failed = None
    r = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "bash", "-c", exec_wrapper(cmd)],
        capture_output=True, text=True, errors="replace", timeout=300
    )
    out, code = r.stdout, r.returncode
    err, _last_failed = split_failed(r.stderr)
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


# A name that looks like it holds a credential. Names only are ever reported.
KEY_NAME_RE = re.compile(r"(?:^|_)(?:API_?KEY|KEY|TOKEN|SECRET|PASSWORD|PASSWD)(?:$|_)",
                         re.I)
SELFCHECK_MIN_SECRET = 12
_selfcheck_secrets = []


def set_selfcheck_secrets(secrets):
    """The brain's own provider keys, held in memory so selfcheck can prove
    none of them reached the body. Never written, printed or journalled."""
    global _selfcheck_secrets
    _selfcheck_secrets = [s for s in (secrets or [])
                          if isinstance(s, str) and len(s) >= SELFCHECK_MIN_SECRET]


def selfcheck(secrets=None) -> dict:
    """Prove the body's bounds by their EFFECT, at every start (2026-10-02,
    taken from Growing Cousin's start-up selfcheck). Since 2026-09-26 no
    provider key enters the body and `ask` is a tombstone, and the only proof
    of either was a session typing `env` into the body during a daily check --
    "keys withheld: UNVERIFIED today" stood in CLAUDE.md section 8 four times.
    A setting that is present, parsed and live can still do nothing; ask the
    body. Three states per check: True, False, None (could not tell). It never
    vetoes: a body that fails it still runs, and the record says so.
    Reports names and counts only, never a value.
    """
    secrets = _selfcheck_secrets if secrets is None else [
        s for s in secrets if isinstance(s, str) and len(s) >= SELFCHECK_MIN_SECRET]
    res = {"keys_absent": None, "ask_retired": None, "key_shaped_names": [],
           "config_keys_checked": len(secrets), "config_keys_found": None}
    try:
        out, _err, code = run_command("env")
        take_failed()
        if code == 0 and "=" in out:
            names = [l.split("=", 1)[0] for l in out.splitlines() if "=" in l]
            res["key_shaped_names"] = sorted(n for n in names if KEY_NAME_RE.search(n))
            res["config_keys_found"] = sum(1 for s in secrets if s in out)
            res["keys_absent"] = (not res["key_shaped_names"]
                                  and res["config_keys_found"] == 0)
    except Exception:
        pass
    try:
        out, err, code = run_command("ask selfcheck")
        take_failed()
        if not exec_setup_failure(out, err, code):
            res["ask_retired"] = (code != 0 and not out.strip()
                                  and "retired" in (err or ""))
    except Exception:
        pass
    return res


def respawn(dockerfile_dir: str = "."):
    """Kill and restart the container. Mind volume persists."""
    stop()
    time.sleep(2)
    # remove stopped container if --rm didn't catch it
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    start(dockerfile_dir)
