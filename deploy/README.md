# Deploy -- Growing Spine launcher + desktop icon

One-click launcher for the Growing Spine creature + observer on the Debian laptop.
Paths in `growing-spine.desktop` and `start-growing-spine.sh` assume the laptop
layout (user `boas`, project at `~/growing-spine`); edit them for another host.

## Architecture the launcher assumes
- **Brain** (`main.py`) runs as a **systemd user service** `growing-spine`
  (see `INSTALL-systemd.md`), which auto-restarts it if it dies and can be
  configured to start on boot. The launcher NEVER runs `main.py` directly --
  doing so once created a second brain alongside the systemd one (different
  command strings, `pkill` couldn't match). It only ensures the service is up.
- **Observer** (`observer.py`) is the GUI dashboard, one instance, launched on
  the X display. It is NOT a service (it needs `DISPLAY`), so the launcher
  (re)starts it each click.
- **Health probe** (`scripts/spine_health.py`) runs daily via the
  `spine-health.timer` systemd user timer; the launcher also arms it.

## Contents
- `start-growing-spine.sh` -- ensures the brain service is up, arms the health
  timer, and (re)opens the observer window. Idempotent; never starts a 2nd brain.
- `growing-spine.desktop` -- desktop entry that runs the launcher with the icon.
- `growing-spine.png` -- 256x256 spine-sprout icon.
- `make_spine_icon.py` -- regenerates `growing-spine.png` (needs PyQt6).

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

# 4. the systemd services must exist first -- see INSTALL-systemd.md for
#    growing-spine.service AND spine-health.timer/.service
```
Then double-click the icon, or just run `~/start-growing-spine.sh`.

## Observer launch note (why setsid, not bare nohup)
The launcher starts the observer with `DISPLAY=:0 setsid python3 observer.py
... < /dev/null & disown`. A bare `nohup ... &` once left an unmapped 10x10
window under xfwm4 (the WM ignored an early `showMaximized`). `observer.py`
now shows at an explicit geometry then maximizes on the next event-loop pass;
the `setsid`/`disown`/`</dev/null` form is what reliably survives the SSH or
desktop parent exiting.

## Reboot / autostart behaviour
- `systemctl --user stop growing-spine` stops the brain but leaves the unit
  enabled. After a reboot the brain returns only once the user's systemd
  session starts -- i.e. after graphical login -- unless lingering is enabled
  (`loginctl enable-linger boas`) to start it at boot without login.
- Clicking the desktop icon after login brings up brain + health timer +
  observer together.
- `gate-eval-watch` is a transient on-demand unit (`systemd-run`), started
  only when actively validating the idea gate; it is intentionally NOT in the
  launcher.

## Notes
- The observer also draws this icon at runtime (`_make_spine_icon()` in
  `observer.py`); this PNG is the same design for the desktop launcher.
- Laptop-local helpers (`~/restart-creature.sh` etc.) are not in this repo by
  convention.
