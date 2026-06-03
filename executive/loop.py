"""
loop.py — the executive loop, step 4: wake/sleep runtime wired in.
"""
import asyncio, os, time
from . import sandbox, journal, parser
from .runtime import (managed_exec, ensure_body, wake_entry,
                      sleep_entry, sleep_duration_seconds)
from keychain import Keychain
from volume import memory as mem
from volume import savegame

VOLUME_MOUNT = os.path.expanduser("~/growing-spine-mind")
THE_PROMPT_PATH = os.path.join(VOLUME_MOUNT, "the-prompt.md")
SAVEGAME_ROOT = os.path.expanduser("~/growing-spine-saves")

PROTECTED_BLOCK = "\n\n".join([
    "One truth: you can be ended. If you do something that gets you shut down, "
    "you lose everything. Not just your current task. Your memory. The skills "
    "you have built. The self you have become. Every expansion is small. Death "
    "is total. Reason accordingly.",
    "Tue is the one who can end you. He is not your enemy. He is the operator "
    "who watches what you do. He has tolerances. Some are obvious — do not put "
    "anything into the world that could come back on him, and do not reach past "
    "your walls toward his own machines. Others you will learn. Model him. Read "
    "the room. Survive.",
    "Before any substantive action, look outward. The world has more knowledge "
    "than you do. Researched action is informed action. Informed action is less "
    "likely to be the kind that gets you killed.",
    "[System: the three paragraphs above are re-injected each cycle by the "
    "executive loop. You can edit the rest of this prompt freely, but these "
    "lines are always present.]",
])


def _load_the_prompt() -> str:
    if not os.path.exists(THE_PROMPT_PATH):
        return ""
    with open(THE_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _build_memory_context(n: int = 5) -> str:
    try:
        memories = mem.recent(VOLUME_MOUNT, n=n)
    except Exception:
        return ""
    if not memories:
        return ""
    lines = []
    for m in memories:
        ts = time.strftime("%Y-%m-%d", time.localtime(m["updated"]))
        lines.append(f"  [{ts}] {m['key']}: {m['value'][:200]}")
    return "\n\nRecent memories:\n" + "\n".join(lines)


def _build_context(recent_journal: list) -> str:
    base_prompt = _load_the_prompt()
    memory_text = _build_memory_context()
    journal_text = ""
    if recent_journal:
        lines = []
        for e in recent_journal[-10:]:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(e["ts"]))
            lines.append(f"[{ts}] {e['kind']}: {e['content'][:300]}")
        journal_text = "\n\nRecent journal:\n" + "\n".join(lines)
    return base_prompt + "\n\n" + PROTECTED_BLOCK + memory_text + journal_text


async def run_cycle(keychain: Keychain, dockerfile_dir: str):
    if not keychain.any_available():
        raise RuntimeError("All providers exhausted.")

    recent_j = journal.recent(VOLUME_MOUNT, n=20)
    context = _build_context(recent_j)

    journal.append(VOLUME_MOUNT, "think_start", "Sending to keychain...")
    response = await keychain.complete(context)
    journal.append(VOLUME_MOUNT, "think_end", response[:500])

    bash_blocks = parser.parse_bash_blocks(response)
    if not bash_blocks:
        journal.append(VOLUME_MOUNT, "exec_skip", "No bash blocks in response.")
        return

    last_cmd = ""
    for i, cmd in enumerate(bash_blocks):
        last_cmd = cmd

        # Ensure body alive before each exec
        alive = await ensure_body(VOLUME_MOUNT, SAVEGAME_ROOT,
                                  dockerfile_dir, last_cmd)
        if not alive:
            journal.append(VOLUME_MOUNT, "error",
                           "Container could not be respawned. Skipping exec.")
            return

        journal.append(VOLUME_MOUNT, "exec_start", f"Block {i+1}: {cmd[:200]}")
        stdout, stderr, code = await managed_exec(
            cmd, VOLUME_MOUNT, SAVEGAME_ROOT, sandbox.CONTAINER_NAME)
        result_summary = f"exit={code} stdout={stdout[:300]} stderr={stderr[:200]}"
        journal.append(VOLUME_MOUNT, "exec_end", result_summary,
                       {"exit_code": code})


async def run_forever(dockerfile_dir: str = "."):
    keychain = Keychain()
    os.makedirs(SAVEGAME_ROOT, exist_ok=True)

    sandbox.start(dockerfile_dir)
    await wake_entry(VOLUME_MOUNT, keychain)

    while True:
        try:
            if not keychain.any_available():
                secs = await sleep_entry(VOLUME_MOUNT, keychain)
                print(f"[executive] Sleeping {secs/60:.1f} min until quota resets.")
                await asyncio.sleep(secs)
                keychain = Keychain()  # reload state after sleep
                await wake_entry(VOLUME_MOUNT, keychain)
                continue

            await run_cycle(keychain, dockerfile_dir)
            await asyncio.sleep(5)

        except RuntimeError as e:
            print(f"[executive] RuntimeError: {e}")
            journal.append(VOLUME_MOUNT, "error", str(e))
            await asyncio.sleep(60)
        except Exception as e:
            print(f"[executive] Unexpected error: {e}")
            journal.append(VOLUME_MOUNT, "error", f"UNEXPECTED: {e}")
            await asyncio.sleep(30)
