#!/usr/bin/env python3
"""
observer.py -- Growing Spine dashboard (single-window, low-power).

Redesign 2026-07-07: the old 5-tab observer ran 5 concurrent timers,
rebuilt whole widget trees every tick, parsed the full ~37MB journal at
startup and polled `docker exec` -- ~33% of a core continuously, ~6 deg C
of CPU baseline (a contributor to the 07-06 thermal trip). This version:
  - ONE 2s timer, ONE refresh pass, all widgets updated IN PLACE
  - journal: tail the last 64KB at open, then incremental reads only;
    display capped via setMaximumBlockCount (oldest lines auto-trim)
  - zero subprocesses (no docker exec; brain liveness via a /proc scan
    every 5th tick)
  - files re-read only when size/mtime changed
  - memory panel: control keys + layer-1 only (no full ranked render)
Target: <1% CPU when idle.
"""
import sys, os, json, time, html
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (QColor, QFont, QPalette, QIcon, QPixmap, QPainter,
                         QPen, QBrush, QPainterPath)

MIND_DIR = os.path.expanduser("~/growing-spine-mind")
JOURNAL  = os.path.join(MIND_DIR, "journal.jsonl")
CHAT     = os.path.join(MIND_DIR, "chat.jsonl")
CONFIG   = os.path.expanduser("~/growing-spine/config.yaml")
QUOTA    = os.path.expanduser("~/growing-spine/keychain/quota_state.json")

# Live memory module (same code the creature uses -> panel cannot drift)
import importlib.util as _ilu
_ms = _ilu.spec_from_file_location(
    "gmem", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "volume", "memory.py"))
gmem = _ilu.module_from_spec(_ms)
_ms.loader.exec_module(gmem)

KIND_COLORS = {
    "wake": "#4CAF50", "sleep": "#9E9E9E", "think_end": "#64B5F6",
    "exec_start": "#FFB74D", "exec_end": "#A5D6A7", "exec_skip": "#78909C",
    "error": "#EF5350", "exec_timeout": "#FF8A65", "respawn": "#CE93D8",
    "birth": "#80CBC4", "savegame_preemptive": "#FFF176", "death": "#EF9A9A",
    "idea_gate": "#BA68C8", "chat_retry": "#F48FB1",
}
DEFAULT_COLOR = "#E0E0E0"
FONT_SIZE  = 13
TAIL_BYTES = 65536    # initial journal window -- never the whole file
MAX_BLOCKS = 500      # journal display cap (auto-trims oldest)
CHAT_INIT  = 30       # chat messages shown at open
TICK_MS    = 2000     # the single global tick
SLOW_EVERY = 5        # /proc scan + quota + memory panel every Nth tick


def _esc(s):
    return html.escape(str(s))


def _fmt_age(secs):
    if secs < 90:
        return f"{int(secs)}s"
    if secs < 5400:
        return f"{int(secs // 60)}m"
    return f"{secs / 3600:.1f}h"


def _brain_pid():
    """Find the creature via /proc -- no subprocess."""
    me = os.getpid()
    try:
        for d in os.listdir("/proc"):
            if not d.isdigit() or int(d) == me:
                continue
            try:
                with open(f"/proc/{d}/cmdline", "rb") as f:
                    cmd = f.read().decode("utf-8", "replace")
            except OSError:
                continue
            if "main.py" in cmd and "growing-spine" in cmd and "python" in cmd:
                return int(d)
    except OSError:
        pass
    return None


def _disk():
    try:
        import shutil
        u = shutil.disk_usage("/")
        return f"{u.used / u.total * 100:.0f}% used, {u.free / 1e9:.0f}G free"
    except Exception:
        return "?"


def dark_palette():
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,     QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Base,       QColor(20, 20, 20))
    p.setColor(QPalette.ColorRole.Text,       QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Button,     QColor(45, 45, 45))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Highlight,  QColor(60, 120, 200))
    return p


def _make_spine_icon():
    """Golden vertebral column with three green sprouts (QPainter, no file)."""
    try:
        px = QPixmap(64, 64)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bone, cord = QColor("#D4A853"), QColor("#9B6E3A")
        green, leaf, dark = QColor("#5CB85C"), QColor("#4CAF50"), QColor("#3E2A0A")
        p.setPen(QPen(cord, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(32, 22, 32, 60)
        p.setPen(QPen(dark, 1.0)); p.setBrush(QBrush(bone))
        for i in range(4):
            p.drawRoundedRect(19, 24 + i * 10, 26, 6, 3, 3)
        pen = QPen(green, 2.5, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(32, 22, 32, 8)
        left = QPainterPath(); left.moveTo(32, 20); left.cubicTo(30, 15, 21, 13, 15, 8)
        p.drawPath(left)
        right = QPainterPath(); right.moveTo(32, 20); right.cubicTo(34, 15, 43, 13, 49, 8)
        p.drawPath(right)
        p.setPen(QPen(dark, 0.5)); p.setBrush(QBrush(leaf))
        p.drawEllipse(28, 4, 9, 6); p.drawEllipse(11, 5, 8, 6); p.drawEllipse(45, 5, 8, 6)
        p.end()
        return QIcon(px)
    except Exception:
        return QIcon()


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growing Spine -- Dashboard")
        self.setWindowIcon(_make_spine_icon())
        self.resize(1280, 800)

        self._tick_n   = 0
        self._jpos     = None      # journal read position (None = not opened yet)
        self._chat_n   = 0         # chat entries already rendered
        self._chat_sig = None      # (size, mtime) of chat file at last read
        self._quota_sig = None
        self._mem_html = None
        self._brain    = None
        self._providers = self._load_providers()

        root = QWidget(); outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 8); outer.setSpacing(6)

        # -- vitals strip ------------------------------------------------
        vit = QHBoxLayout()
        self.lbl_brain = QLabel("brain: ?")
        self.lbl_disk  = QLabel("disk: ?")
        self.lbl_last  = QLabel("journal: ?")
        self.lbl_quota = QLabel("providers: ?")
        for l in (self.lbl_brain, self.lbl_disk, self.lbl_last, self.lbl_quota):
            l.setFont(QFont("monospace", FONT_SIZE))
            l.setStyleSheet("color:#E0E0E0; padding:2px 10px; background:#1e1e2e;"
                            "border:1px solid #333; border-radius:4px;")
            vit.addWidget(l)
        vit.addStretch()
        outer.addLayout(vit)

        # -- main split: journal | memory ---------------------------------
        split = QSplitter(Qt.Orientation.Horizontal)

        self.journal = QTextEdit(); self.journal.setReadOnly(True)
        self.journal.setFont(QFont("monospace", FONT_SIZE - 1))
        self.journal.document().setMaximumBlockCount(MAX_BLOCKS)
        self.journal.setStyleSheet("background:#141414; border:1px solid #333;")
        split.addWidget(self.journal)

        self.mem = QTextEdit(); self.mem.setReadOnly(True)
        self.mem.setFont(QFont("monospace", FONT_SIZE - 1))
        self.mem.setStyleSheet("background:#141414; border:1px solid #333;")
        split.addWidget(self.mem)
        split.setSizes([760, 460])
        outer.addWidget(split, stretch=3)

        # -- chat ----------------------------------------------------------
        self.chat = QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setFont(QFont("sans-serif", FONT_SIZE - 1))
        self.chat.document().setMaximumBlockCount(400)
        self.chat.setStyleSheet("background:#141414; border:1px solid #333;")
        outer.addWidget(self.chat, stretch=1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Message the creature and press Enter...")
        self.input.setFont(QFont("sans-serif", FONT_SIZE))
        self.input.setStyleSheet("background:#1e1e2e; color:#E0E0E0;"
                                 "border:1px solid #555; padding:6px;")
        self.input.returnPressed.connect(self._send)
        btn = QPushButton("Send"); btn.setFixedWidth(80)
        btn.clicked.connect(self._send)
        row.addWidget(self.input); row.addWidget(btn)
        outer.addLayout(row)

        self.setCentralWidget(root)
        self.statusBar().setFont(QFont("monospace", FONT_SIZE - 2))

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)
        self._tick(first=True)

    # -- config (read once) ------------------------------------------------
    def _load_providers(self):
        try:
            import yaml
            with open(CONFIG) as f:
                cfg = yaml.safe_load(f)
            return [(p["key"], p.get("display_name", p["key"]))
                    for p in cfg.get("providers", []) if p.get("enabled", True)]
        except Exception:
            return []

    # -- the single tick ----------------------------------------------------
    def _tick(self, first=False):
        self._tick_n += 1
        slow = first or (self._tick_n % SLOW_EVERY == 0)
        try:
            self._tick_journal(first)
            self._tick_chat(first)
            if slow:
                self._tick_slow()
            self.statusBar().showMessage(
                f"tick {self._tick_n}  |  {time.strftime('%H:%M:%S')}")
        except Exception as e:
            self.statusBar().showMessage(f"refresh error: {e}")

    # -- journal: tail 64KB once, then incremental --------------------------
    def _tick_journal(self, first):
        try:
            size = os.path.getsize(JOURNAL)
        except OSError:
            if first:
                self.journal.setHtml("<i>journal not found -- creature running?</i>")
            return
        seeked_mid = False
        if self._jpos is None or size < self._jpos:      # first open / rotation
            self._jpos = max(0, size - TAIL_BYTES)
            seeked_mid = self._jpos > 0
        if size == self._jpos:
            return
        with open(JOURNAL, encoding="utf-8", errors="replace") as f:
            f.seek(self._jpos)
            if seeked_mid:
                f.readline()                              # drop partial line
            chunk = f.readlines()
            self._jpos = f.tell()
        out = []
        for line in chunk:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = e.get("kind", "?")
            c = KIND_COLORS.get(kind, DEFAULT_COLOR)
            ts = time.strftime("%H:%M:%S", time.localtime(e.get("ts", 0)))
            txt = _esc(str(e.get("content", ""))[:220]).replace("\n", " ")
            out.append(f'<span style="color:#666">{ts}</span> '
                       f'<span style="color:{c}">[{_esc(kind)}]</span> '
                       f'<span style="color:#CFCFCF">{txt}</span>')
        if out:
            self.journal.append("<br>".join(out))
            sb = self.journal.verticalScrollBar()
            sb.setValue(sb.maximum())
            try:
                last_ts = json.loads(chunk[-1]).get("ts", time.time())
            except Exception:
                last_ts = time.time()
            self.lbl_last.setText(
                f"journal: {_fmt_age(max(0, time.time() - last_ts))} ago")

    # -- chat: incremental append -------------------------------------------
    def _tick_chat(self, first):
        try:
            st = os.stat(CHAT)
            sig = (st.st_size, st.st_mtime)
        except OSError:
            return
        if sig == self._chat_sig:
            return
        self._chat_sig = sig
        entries = []
        with open(CHAT, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("kind") in ("from_tue", "from_creature"):
                    entries.append(e)
        if first:
            self._chat_n = max(0, len(entries) - CHAT_INIT)
        new = entries[self._chat_n:]
        self._chat_n = len(entries)
        for e in new:
            is_tue = e.get("kind") == "from_tue"
            who = "Tue" if is_tue else "Creature"
            col = "#64B5F6" if is_tue else "#A5D6A7"
            ts = time.strftime("%H:%M", time.localtime(e.get("ts", 0)))
            self.chat.append(
                f'<span style="color:{col}"><b>{who}</b></span> '
                f'<span style="color:#666;font-size:11px">{ts}</span>  '
                f'<span style="color:#DDD">{_esc(e.get("content", ""))}</span>')
        if new:
            sb = self.chat.verticalScrollBar()
            sb.setValue(sb.maximum())

    # -- slow lane: /proc, disk, quota, memory panel --------------------------
    def _tick_slow(self):
        self._brain = _brain_pid()
        if self._brain:
            self.lbl_brain.setText(f"brain: pid {self._brain}")
            self.lbl_brain.setStyleSheet(
                "color:#4CAF50; padding:2px 10px; background:#1e1e2e;"
                "border:1px solid #333; border-radius:4px;")
        else:
            self.lbl_brain.setText("brain: NOT RUNNING")
            self.lbl_brain.setStyleSheet(
                "color:#EF5350; padding:2px 10px; background:#1e1e2e;"
                "border:1px solid #333; border-radius:4px;")
        self.lbl_disk.setText(f"disk: {_disk()}")
        self._tick_quota()
        self._tick_memory()

    def _tick_quota(self):
        # No mtime gating: green/orange depend on the CLOCK, not just file
        # changes -- a frozen label showed stale green through a wall once.
        try:
            with open(QUOTA) as f:
                state = json.load(f)
        except OSError:
            self.lbl_quota.setText("providers: no state file")
            return
        except Exception:
            return
        now, parts = time.time(), []
        for key, name in self._providers or [(k, k) for k in state]:
            ps = state.get(key, {})
            ls = ps.get("last_success_at") or 0
            ex = ps.get("exhausted_at") or 0
            rec = ps.get("last_recovery_secs")
            if ex > ls:
                # walled: exhaustion is the latest event
                hint = f", recovers ~{_fmt_age(rec)}" if rec else ""
                parts.append(f'<span style="color:#FFB74D">{_esc(name)} '
                             f'(walled {_fmt_age(now - ex)}{hint})</span>')
            elif ls:
                parts.append(f'<span style="color:#4CAF50">{_esc(name)} '
                             f'(ok {_fmt_age(now - ls)} ago)</span>')
            else:
                parts.append(f'<span style="color:#9E9E9E">{_esc(name)} (unused)</span>')
        self.lbl_quota.setText("providers: " + "  ".join(parts))

    def _tick_memory(self):
        try:
            cur = gmem._cur_slug(MIND_DIR)
            l1 = gmem.layer1(MIND_DIR)
            total = gmem.count(MIND_DIR)
            proj = gmem.retrieve(MIND_DIR, "current-project")
            phase = gmem.retrieve(MIND_DIR, "current-phase")
        except Exception as e:
            self.mem.setHtml(f"<i>memory read error: {_esc(e)}</i>")
            return
        h = ['<div style="color:#4CAF50"><b>FOCUS</b></div>']
        pv = (proj or {}).get("value", "-") if isinstance(proj, dict) else (proj or "-")
        fv = (phase or {}).get("value", "-") if isinstance(phase, dict) else (phase or "-")
        h.append(f'<div style="color:#CFCFCF">project: {_esc(str(pv)[:150])}</div>')
        h.append(f'<div style="color:#CFCFCF">phase: {_esc(str(fv)[:80])}'
                 f' &nbsp; <span style="color:#666">({total} memories,'
                 f' slug: {_esc(cur or "-")})</span></div>')
        h.append('<div style="color:#64B5F6;margin-top:8px"><b>WORKING MEMORY'
                 ' (layer 1)</b></div>')
        for m in l1:
            ts = time.strftime("%m-%d %H:%M", time.localtime(m.get("updated", 0)))
            head = _esc(str(m.get("value", "")).replace("\n", " ")[:110])
            h.append(f'<div><span style="color:#80DEEA">{_esc(m.get("key", "?"))}'
                     f'</span> <span style="color:#666">[{ts}]</span><br>'
                     f'<span style="color:#B0BEC5">&nbsp;&nbsp;{head}</span></div>')
        if not l1:
            h.append('<div style="color:#555">(no working memories)</div>')
        out = "".join(h)
        if out != self._mem_html:
            self._mem_html = out
            self.mem.setHtml(out)

    # -- chat send -------------------------------------------------------------
    def _send(self):
        msg = self.input.text().strip()
        if not msg:
            return
        try:
            entry = {"ts": time.time(), "kind": "from_tue",
                     "content": msg, "read": False}
            with open(CHAT, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self.input.clear()
            self._chat_sig = None            # force re-read next tick
            self._tick_chat(first=False)
        except Exception as e:
            self.statusBar().showMessage(f"send error: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(_make_spine_icon())
    app.setPalette(dark_palette())
    win = Dashboard()

    # Some window managers ignore showMaximized() issued before the window is
    # mapped -- it can leave a 10x10 stub. Show at an explicit geometry first,
    # then maximize on the next event-loop pass once the WM has the window.
    scr = app.primaryScreen().availableGeometry()
    win.setGeometry(scr.x() + 40, scr.y() + 40,
                    min(1280, scr.width() - 80), min(800, scr.height() - 80))
    win.show()
    win.raise_()
    win.activateWindow()
    QTimer.singleShot(200, win.showMaximized)
    sys.exit(app.exec())
