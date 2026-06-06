# Deploy -- Growing Spine launcher + desktop icon

One-click launcher for the Growing Spine creature + observer on the Debian laptop.
Paths in `growing-spine.desktop` and `start-growing-spine.sh` assume the laptop
layout (user `boas`, project at `~/growing-spine`); edit them for another host.

## Contents
- `start-growing-spine.sh` -- starts creature (main.py) + observer (observer.py) together; safe to re-run (restarts whatever is already running).
- `growing-spine.desktop` -- desktop entry that runs the launcher with the icon.
- `growing-spine.png` -- 256x256 spine-sprout icon.
- `make_spine_icon.py` -- regenerates `growing-spine.png` (needs PyQt6): `python3 make_spine_icon.py`.

## Install on the laptop
```bash
# 1. launcher
cp start-growing-spine.sh ~/start-growing-spine.sh
chmod +x ~/start-growing-spine.sh

# 2. icon
mkdir -p ~/.local/share/icons
cp growing-spine.png ~/.local/share/icons/growing-spine.png

# 3. desktop entry  (Skrivebord = Desktop on a Danish-locale system)
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo ~/Desktop)"
cp growing-spine.desktop "$DESK/growing-spine.desktop"
chmod +x "$DESK/growing-spine.desktop"
gio set "$DESK/growing-spine.desktop" metadata::trusted true   # GNOME: Allow Launching
```
Then double-click the icon, or just run `~/start-growing-spine.sh`.

## Notes
- The observer also draws this icon at runtime (`_make_spine_icon()` in `observer.py`); this PNG is the same design, for the desktop launcher.
- The creature runs forever while the laptop is on, but does NOT auto-start after a reboot -- launch via the icon. For unattended-through-reboot, add a systemd user service or an XDG autostart entry.
- Laptop also carries `~/restart-creature.sh` and `~/start-observer.sh` (laptop-only helpers, not in this repo by convention).
