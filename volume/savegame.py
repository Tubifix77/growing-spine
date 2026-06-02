"""savegame.py — body savegame (docker commit) + mind snapshot (volume copy)."""
import os, shutil, time, subprocess, json

SAVEGAME_DIR = None  # set by init; host-side dir outside volume

MAX_SAVEGAMES = 7  # keep last N plus milestone saves

def _savegame_dir(host_savegame_root: str) -> str:
    os.makedirs(host_savegame_root, exist_ok=True)
    return host_savegame_root

def _tag(label: str = "") -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{label}" if label else ts

def commit_body(container_name: str, tag: str) -> str | None:
    """docker commit the container. Returns image name or None on failure."""
    image = f"growing-spine-save:{tag}"
    r = subprocess.run(
        ["docker", "commit", container_name, image],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"[savegame] body commit failed: {r.stderr[:200]}")
        return None
    return image

def snapshot_mind(volume_mount: str, savegame_root: str, tag: str) -> str | None:
    """Copy volume contents to host-side snapshot dir. Returns path or None."""
    dst = os.path.join(savegame_root, f"mind-{tag}")
    try:
        shutil.copytree(volume_mount, dst)
        return dst
    except Exception as e:
        print(f"[savegame] mind snapshot failed: {e}")
        return None

def save(volume_mount: str, savegame_root: str, container_name: str,
         label: str = "", milestone: bool = False) -> dict:
    """Full savegame: body commit + mind snapshot. Returns metadata dict."""
    tag = _tag(label)
    body_image = commit_body(container_name, tag)
    mind_path = snapshot_mind(volume_mount, savegame_root, tag)
    meta = {
        "tag": tag,
        "ts": time.time(),
        "label": label,
        "milestone": milestone,
        "body_image": body_image,
        "mind_path": mind_path,
    }
    # write metadata
    meta_path = os.path.join(savegame_root, f"meta-{tag}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[savegame] saved: {tag} (body={body_image is not None}, mind={mind_path is not None})")
    _prune(savegame_root)
    return meta

def list_saves(savegame_root: str) -> list:
    """Return list of save metadata dicts, newest first."""
    saves = []
    if not os.path.exists(savegame_root):
        return saves
    for fname in os.listdir(savegame_root):
        if fname.startswith("meta-") and fname.endswith(".json"):
            try:
                with open(os.path.join(savegame_root, fname)) as f:
                    saves.append(json.load(f))
            except Exception:
                pass
    return sorted(saves, key=lambda s: s["ts"], reverse=True)

def _prune(savegame_root: str):
    """Keep last MAX_SAVEGAMES non-milestone saves; never prune milestones."""
    saves = list_saves(savegame_root)
    non_milestones = [s for s in saves if not s.get("milestone")]
    to_prune = non_milestones[MAX_SAVEGAMES:]
    for s in to_prune:
        _delete_save(savegame_root, s)

def _delete_save(savegame_root: str, meta: dict):
    tag = meta["tag"]
    # remove mind snapshot dir
    mind_path = meta.get("mind_path")
    if mind_path and os.path.exists(mind_path):
        shutil.rmtree(mind_path, ignore_errors=True)
    # remove docker image
    body_image = meta.get("body_image")
    if body_image:
        subprocess.run(["docker", "rmi", body_image], capture_output=True)
    # remove meta file
    meta_path = os.path.join(savegame_root, f"meta-{tag}.json")
    if os.path.exists(meta_path):
        os.remove(meta_path)
    print(f"[savegame] pruned: {tag}")

def restore_mind(savegame_root: str, volume_mount: str, tag: str = None) -> bool:
    """Restore mind from snapshot. Uses latest if tag not given."""
    saves = list_saves(savegame_root)
    if not saves:
        print("[savegame] no saves found")
        return False
    target = next((s for s in saves if s["tag"] == tag), saves[0]) if tag else saves[0]
    mind_path = target.get("mind_path")
    if not mind_path or not os.path.exists(mind_path):
        print(f"[savegame] mind snapshot not found: {mind_path}")
        return False
    # backup current mind first
    backup = volume_mount.rstrip("/") + f"_backup_{_tag()}"
    shutil.copytree(volume_mount, backup)
    # restore
    shutil.rmtree(volume_mount)
    shutil.copytree(mind_path, volume_mount)
    print(f"[savegame] mind restored from {target['tag']} (backup at {backup})")
    return True
