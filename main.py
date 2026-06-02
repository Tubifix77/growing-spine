"""main.py — entry point. Run on the Debian laptop host."""
import asyncio, os, sys

def check_config():
    cfg = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(cfg):
        print("ERROR: config.yaml not found. Copy config.yaml.example and fill in your API keys.")
        sys.exit(1)

def init_volume():
    from executive.loop import VOLUME_MOUNT, THE_PROMPT_PATH
    os.makedirs(VOLUME_MOUNT, exist_ok=True)
    if not os.path.exists(THE_PROMPT_PATH):
        starter = os.path.join(os.path.dirname(__file__), "starter-prompt.md")
        if os.path.exists(starter):
            import shutil
            shutil.copy(starter, THE_PROMPT_PATH)
            print(f"[init] Seeded the-prompt.md from starter-prompt.md")
        else:
            print("[init] WARNING: starter-prompt.md not found; the-prompt.md will be empty.")

if __name__ == "__main__":
    check_config()
    init_volume()
    from executive.loop import run_forever
    asyncio.run(run_forever(dockerfile_dir=os.path.dirname(__file__) or "."))
