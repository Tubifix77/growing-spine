"""
loop.py Ã¢ÂÂ the executive loop, step 4: wake/sleep runtime wired in.
"""
import asyncio, os, time
from . import sandbox, journal, parser
from .runtime import (managed_exec, ensure_body, wake_entry,
                      sleep_entry, sleep_duration_seconds)
from keychain import Keychain
from volume import memory as mem
from volume import savegame
from volume import tools as toolmod
from executive import chat as chatmod

VOLUME_MOUNT = os.path.expanduser("~/growing-spine-mind")
EDITABLE_PROMPT_PATH = os.path.join(VOLUME_MOUNT, "editable-prompt.md")
PROTECTED_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "protected-prompt.md")
SAVEGAME_ROOT = os.path.expanduser("~/growing-spine-saves")



def _load_protected_prompt() -> str:
    if not os.path.exists(PROTECTED_PROMPT_PATH):
        return ""
    with open(PROTECTED_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_editable_prompt() -> str:
    if not os.path.exists(EDITABLE_PROMPT_PATH):
        return ""
    with open(EDITABLE_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _build_memory_context() -> str:
    try:
        l1 = mem.layer1(VOLUME_MOUNT)
        l2 = mem.layer2_headlines(VOLUME_MOUNT)
        l3 = mem.layer3_themes(VOLUME_MOUNT)
    except Exception:
        return ""

    parts = []

    if l1:
        lines = [f"  [{m['key']}] {m['value'][:200]}" for m in l1]
        parts.append("Working memory (most recent):\n" + "\n".join(lines))

    if l2:
        headlines = [f"  {m['key']}: {m['headline']}" for m in l2]
        parts.append("Older memories:\n" + "\n".join(headlines))

    if l3:
        parts.append("Archived themes: " + ", ".join(l3))

    return ("\n\n" + "\n\n".join(parts)) if parts else ""


# Journal kinds worth showing the creature — its thoughts and results,
# not executive plumbing (think_start, wake, sleep, exec_start, exec_skip).
MEANINGFUL_KINDS = {"think_end", "exec_end", "error", "exec_timeout",
                    "respawn", "death", "birth"}


def _build_tool_catalogue() -> str:
    try:
        return toolmod.build_catalogue(VOLUME_MOUNT)
    except Exception:
        return ""


def _build_context(recent_journal: list, tue_message: str = None) -> str:
    protected = _load_protected_prompt()
    editable = _load_editable_prompt()
    catalogue = _build_tool_catalogue()
    memory_text = _build_memory_context()

    journal_text = ""
    if recent_journal:
        meaningful = [e for e in recent_journal if e["kind"] in MEANINGFUL_KINDS]
        lines = []
        for e in meaningful[-8:]:
            ts = time.strftime("%H:%M", time.localtime(e["ts"]))
            lines.append(f"[{ts}] {e['kind']}: {e['content'][:300]}")
        if lines:
            journal_text = "\n\nRecent activity (your thoughts and their results):\n" + "\n".join(lines)

    catalogue_block = ("\n\n" + catalogue) if catalogue else ""
    chat_block = ""
    if tue_message:
        chat_block = f"\n\nMessage from Tue: {tue_message}\nReply to this in plain text before your bash blocks."
    return protected + "\n\n" + editable + catalogue_block + memory_text + journal_text + chat_block


async def run_cycle(keychain: Keychain, dockerfile_dir: str):
    if not keychain.any_available():
        raise RuntimeError("All providers exhausted.")

    recent_j = journal.recent(VOLUME_MOUNT, n=20)
    tue_message = chatmod.pop_unread(VOLUME_MOUNT)
    context = _build_context(recent_j, tue_message)

    journal.append(VOLUME_MOUNT, "think_start", "Sending to keychain...")
    response = await keychain.complete(context)
    journal.append(VOLUME_MOUNT, "think_end", response[:500])

    if tue_message:
        reply = chatmod.extract_text_reply(response)
        if reply:
            chatmod.record_reply(VOLUME_MOUNT, reply)

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
            msg = str(e)
            if "exhausted" in msg.lower() or "sleeping" in msg.lower():
                # quota exhausted mid-cycle - sleep gracefully
                secs = await sleep_entry(VOLUME_MOUNT, keychain)
                print(f"[executive] Quota exhausted - sleeping {secs/60:.1f} min.")
                await asyncio.sleep(secs)
                keychain = Keychain()
                await wake_entry(VOLUME_MOUNT, keychain)
            elif "temporarily unavailable" in msg.lower():
                print(f"[executive] Providers temporarily unavailable - retrying in 60s.")
                await asyncio.sleep(60)
            else:
                print(f"[executive] RuntimeError: {msg}")
                journal.append(VOLUME_MOUNT, "error", msg)
                await asyncio.sleep(60)
        except Exception as e:
            import subprocess
            if isinstance(e, subprocess.TimeoutExpired):
                journal.append(VOLUME_MOUNT, "exec_timeout",
                               f"Command timed out after {e.timeout}s - continuing.")
                print(f"[executive] Exec timeout - continuing.")
            else:
                print(f"[executive] Unexpected error: {e}")
                journal.append(VOLUME_MOUNT, "error", f"UNEXPECTED: {e}")
            await asyncio.sleep(5)
