"""savegame.py — body savegame (docker commit) + mind snapshot (volume copy)."""
import os, shutil, time, subprocess, json

MAX_SAVEGAMES = 1  # keep only the latest save; rollback only ever uses saves[0]

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

def _normalise_ownership(path: str) -> int:
    """Walk *path* and chown any root-owned files/dirs to the current process
    uid:gid.  This fixes tools the container wrote as root before snapshot_mind
    tries to copy them.  Best-effort: errors are swallowed so a permissions
    hiccup never aborts the save.  Returns count of items re-owned."""
    uid, gid = os.getuid(), os.getgid()
    if uid == 0:
        return 0  # already root — nothing to do
    count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for name in dirnames + filenames:
                full = os.path.join(dirpath, name)
                try:
                    st = os.lstat(full)
                    if st.st_uid == 0:
                        os.chown(full, uid, gid)
                        count += 1
                except OSError:
                    pass
    except Exception:
        pass
    return count

def snapshot_mind(volume_mount: str, savegame_root: str, tag: str) -> str | None:
    """Copy volume contents to host-side snapshot dir. Returns path or None."""
    dst = os.path.join(savegame_root, f"mind-{tag}")
    # Normalise any root-owned files the container wrote before we try to copy.
    # This is self-healing: the container runs as root and periodically writes
    # tool scripts that the host user can't copy until ownership is fixed.
    fixed = _normalise_ownership(volume_mount)
    if fixed:
        print(f"[savegame] normalised ownership on {fixed} item(s) before snapshot")
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
    _brain = snapshot_brain(label)
    meta = {
        "tag": tag,
        "ts": time.time(),
        "label": label,
        "milestone": milestone,
        "body_image": body_image,
        "mind_path": mind_path,
        "brain_commit": _brain.get("commit"),
    }
    # write metadata
    meta_path = os.path.join(savegame_root, f"meta-{tag}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[savegame] saved: {tag} (body={body_image is not None}, mind={mind_path is not None})")
    _prune(savegame_root)
    rep = prune_save_images(savegame_root)
    if rep["orphans_removed"]:
        print(f"[savegame] reaped {len(rep['orphans_removed'])} orphan image(s): {rep['orphans_removed']}")
    return meta

SAVE_IMAGE_KEEP = 0  # orphan images (no matching meta) are garbage — remove all of them


def _container_image_refs() -> set:
    """Image names/IDs in use by any container (running or stopped) -- never reap these."""
    r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Image}}"],
                       capture_output=True, text=True)
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()} if r.returncode == 0 else set()


def prune_save_images(savegame_root: str = None, keep: int = SAVE_IMAGE_KEEP) -> dict:
    """Reap docker litter the meta-based _prune() can miss.

    _prune() only deletes images it still has a meta-*.json for, so if the meta
    files are lost (e.g. a mind reset/restore) the docker images become ORPHANS
    and accumulate forever (this filled the disk on 2026-06-17). This grounds
    cleanup in docker's ACTUAL state instead: delete `growing-spine-save:*`
    images that are (a) NOT referenced by any current meta file and (b) NOT used
    by a container (keep=0 by default — orphans are garbage). Then prune
    dangling images, build cache, and unused Docker volumes (volumes with no
    container attachment are safe to remove; the mind volume and active container
    volumes are never touched by docker volume prune). Best-effort: never raises,
    logs only. Runs docker WITHOUT sudo -- same as commit_body."""
    summary = {"orphans_removed": [], "errors": [], "skipped_reason": ""}
    CORRUPT_METAS.clear()
    try:
        tracked = set()
        if savegame_root and os.path.exists(savegame_root):
            for sv in list_saves(savegame_root):
                if sv.get("body_image"):
                    tracked.add(sv["body_image"])
        in_use = _container_image_refs()
        r = subprocess.run(
            ["docker", "images", "growing-spine-save",
             "--format", "{{.Repository}}:{{.Tag}}|{{.ID}}"],
            capture_output=True, text=True)
        rows = []  # docker lists newest first
        for ln in r.stdout.splitlines():
            p = ln.split("|")
            if len(p) >= 2 and p[0] and not p[0].endswith(":<none>"):
                rows.append({"ref": p[0], "id": p[1]})
        candidates = [im for im in rows
                      if im["ref"] not in tracked and not CORRUPT_METAS
                      and im["id"] not in in_use and im["ref"] not in in_use]
        for im in candidates[keep:]:  # keep newest `keep`, reap the rest
            rm = subprocess.run(["docker", "rmi", im["ref"]], capture_output=True, text=True)
            if rm.returncode == 0:
                summary["orphans_removed"].append(im["ref"])
            else:
                summary["errors"].append(f"rmi {im['ref']}: {rm.stderr.strip()[:80]}")
        subprocess.run(["docker", "image", "prune", "-f"], capture_output=True)
        subprocess.run(["docker", "builder", "prune", "-f"], capture_output=True)
        # Prune Docker volumes not attached to any container.  Safe: docker only
        # removes volumes with no live container reference, so the mind volume
        # and any active container volumes are never touched.
        subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)
    except Exception as e:
        summary["errors"].append(f"{type(e).__name__}: {e}")
    return summary


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
            except Exception as e:
                # Audit P1-F19: swallowed with a bare `pass`. A meta that cannot
                # be read means its body_image is absent from `tracked`, and the
                # orphan reaper deletes every untracked image (SAVE_IMAGE_KEEP=0)
                # -- so ONE corrupt json file authorised the destruction of the
                # save image it was describing. Corruption must be loud, and it
                # must make the reaper stand down.
                CORRUPT_METAS.append(fname)
                _complain(f"unreadable save meta {fname} ({type(e).__name__}) -- "
                          f"its body image cannot be matched, so image reaping "
                          f"will be SKIPPED this run to avoid deleting it")
    return sorted(saves, key=lambda s: s.get("ts", 0), reverse=True)

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


# ---------------------------------------------------------------------------
# v0.7 -- BRAIN snapshots (the executive source code), via git.
# The body (container) and mind (volume) are snapshotted above. The BRAIN --
# loop.py and the rest of the executive on the host -- is tracked by git, so a
# "save" also records the repo's current commit SHA. Restoring the brain is a
# git reset to that SHA; the diff the creature is shown after a bad self-restart
# is `git diff <good> <crashed>`. Git is the right tool: it already tracks
# exactly the files that matter and produces diffs for free.
# ---------------------------------------------------------------------------
import subprocess as _sp

def _repo_root() -> str:
    # savegame.py lives in <repo>/volume/, so repo root is one up.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _git(args: list, check: bool = False) -> tuple:
    """Run git in the repo. Returns (rc, stdout, stderr)."""
    try:
        r = _sp.run(["git", "-C", _repo_root()] + args,
                    capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def brain_commit() -> str | None:
    """Current executive commit SHA, or None if not a git repo."""
    rc, out, _ = _git(["rev-parse", "HEAD"])
    return out if rc == 0 and out else None

CORRUPT_METAS = []   # filled by list_saves; a non-empty list disarms reaping


def _complain(msg: str):
    """Loud on stdout, and in the creature's journal. These failures are about
    its restore points; silence is the one thing they must not be."""
    print(f"[savegame] {msg}")
    try:
        from executive import journal as _j
        _j.append(os.path.expanduser("~/growing-spine-mind"), "error",
                  f"savegame: {msg}")
    except Exception:
        pass


def snapshot_brain(label: str = "") -> dict:
    """Capture the brain state. If the working tree has uncommitted changes
    (e.g. the creature just edited loop.py), commit them first so the SHA is a
    faithful, restorable snapshot. Returns {commit, dirty_committed}."""
    rc, status, _ = _git(["status", "--porcelain"])
    dirty = bool(status)
    committed = False
    err = ""
    if dirty:
        _git(["add", "-A"])
        msg = "savegame brain snapshot" + (f" ({label})" if label else "")
        rc, _, err = _git(["commit", "-m", msg, "--no-verify"])
        committed = (rc == 0)
        if not committed:
            # Audit P1-F18: `err` was bound and dropped. The consequence is not
            # cosmetic: the recorded SHA then predates the creature's edit, so the
            # crash-rollback net restores a state that never crashed and the
            # "the change that killed you was:" diff comes out EMPTY -- the one
            # message whose entire job is teaching the creature what broke.
            _complain(f"brain snapshot commit FAILED ({err.strip()[:200]}) -- "
                      f"the recorded SHA predates the working tree, so a "
                      f"crash-rollback diff from it would be empty or wrong")
    return {"commit": brain_commit(), "dirty_committed": committed,
            "commit_error": err.strip()[:300] if not committed and dirty else ""}

def restore_brain(commit: str) -> bool:
    """Hard-reset the executive source to a known-good commit. The caller
    (boot-time rollback) restarts the process afterward so the reverted code
    actually loads."""
    if not commit:
        return False
    # stash anything uncommitted so reset can't be blocked, then hard reset
    _git(["add", "-A"])
    _git(["stash", "push", "-m", "pre-restore-brain", "--include-untracked"])
    rc, _, err = _git(["reset", "--hard", commit])
    if rc != 0:
        print(f"[savegame] restore_brain failed: {err}")
        return False
    print(f"[savegame] brain restored to {commit[:10]}")
    return True

def brain_diff(good_commit: str, bad_commit: str = "HEAD") -> str:
    """The diff between a known-good brain and the (crashing) one -- this is what
    the creature is shown so it can learn what its self-edit changed. Truncated
    to keep it readable in context."""
    if not good_commit:
        return "(no good commit recorded; cannot diff)"
    rc, out, err = _git(["diff", "--stat", good_commit, bad_commit])
    rc2, full, _ = _git(["diff", good_commit, bad_commit])
    if rc != 0 and rc2 != 0:
        return f"(could not compute diff: {err})"
    diff = (out + "\n\n" + full).strip()
    if len(diff) > 6000:
        diff = diff[:6000] + "\n... [diff truncated]"
    return diff or "(no differences)"
