"""init.py â initialise the mind volume on first run."""
import os, shutil, time

from . import memory
from executive import journal

SKILLS_DIR = "skills"
PROMPT_FILENAME = "editable-prompt.md"

def _starter_prompt_path(repo_root: str) -> str:
    return os.path.join(repo_root, "starter-prompt.md")

def init_volume(volume_mount: str, repo_root: str, force: bool = False):
    """
    Set up the mind volume for first run (or force re-init).
    Creates dirs, seeds editable-prompt, initialises memory DB, writes first journal entry.
    Safe to call on every startup â skips steps already done unless force=True.
    """
    os.makedirs(volume_mount, exist_ok=True)
    os.makedirs(os.path.join(volume_mount, SKILLS_DIR), exist_ok=True)

    # Seed editable-prompt from starter-prompt.md if not present
    prompt_path = os.path.join(volume_mount, PROMPT_FILENAME)
    if not os.path.exists(prompt_path) or force:
        src = _starter_prompt_path(repo_root)
        if os.path.exists(src):
            shutil.copy(src, prompt_path)
            print(f"[init] seeded editable-prompt.md from starter-prompt.md")
        else:
            # write a minimal stub so the loop doesn't crash
            with open(prompt_path, "w") as f:
                f.write("You are a creature in a box. You exist to grow.\n")
            print(f"[init] WARNING: starter-prompt.md not found â wrote minimal stub")

    # Initialise memory DB
    db_path = os.path.join(volume_mount, memory.DB_FILENAME)
    if not os.path.exists(db_path) or force:
        memory.init_db(volume_mount)
        print(f"[init] memory.db initialised")
        # Seed first memory â the creature's birth record
        memory.store(
            volume_mount,
            key="birth",
            value=f"I came into being at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}. "
                  f"My memory begins here.",
            tags=["identity", "birth"]
        )
        print(f"[init] birth memory seeded")
    else:
        # DB exists â ensure schema is current (idempotent)
        memory.init_db(volume_mount)

    # Write first journal entry if journal is empty
    journal_path = os.path.join(volume_mount, "journal.jsonl")
    if not os.path.exists(journal_path) or os.path.getsize(journal_path) == 0 or force:
        journal.append(volume_mount, "birth",
            "Volume initialised. Memory database created. Editable-prompt seeded. "
            "This is the first entry in this creature's journal.")
        print(f"[init] first journal entry written")

    print(f"[init] volume ready at {volume_mount}")
    return True

def volume_is_initialised(volume_mount: str) -> bool:
    """Quick check â does the volume look like it's been set up?"""
    return (
        os.path.exists(os.path.join(volume_mount, PROMPT_FILENAME)) and
        os.path.exists(os.path.join(volume_mount, memory.DB_FILENAME))
    )
