#!/usr/bin/env python3
"""
observer.py — Growing Spine observer GUI.
Run on the Debian laptop: python3 observer.py
"""
import sys, os, json, time, sqlite3, subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QSplitter, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher, QSize
from PyQt6.QtGui import QColor, QFont, QPalette, QFontMetrics, QIcon, QPixmap, QPainter, QPen, QBrush, QPainterPath

# ── Paths ────────────────────────────────────────────────────────────
MIND_DIR      = os.path.expanduser("~/growing-spine-mind")
JOURNAL_PATH  = os.path.join(MIND_DIR, "journal.jsonl")
MEMORY_DB     = os.path.join(MIND_DIR, "memory.db")
TUE_MSG_PATH  = os.path.join(MIND_DIR, "tue-message.txt")
CHAT_PATH     = os.path.join(MIND_DIR, "chat.jsonl")
CONFIG_PATH   = os.path.expanduser("~/growing-spine/config.yaml")
QUOTA_PATH    = os.path.expanduser("~/growing-spine/keychain/quota_state.json")
CONTAINER     = "growing-spine-body"

# -- Live memory module (same code the creature uses -> Memory tab can't drift) --
import importlib.util as _ilu
_memspec = _ilu.spec_from_file_location(
    "gmem", os.path.join(os.path.dirname(os.path.abspath(__file__)), "volume", "memory.py"))
gmem = _ilu.module_from_spec(_memspec)
_memspec.loader.exec_module(gmem)

# ── Colours per journal kind ─────────────────────────────────────────
KIND_COLORS = {
    "wake":       "#4CAF50",
    "sleep":      "#9E9E9E",
    "think_end":  "#64B5F6",
    "exec_start": "#FFB74D",
    "exec_end":   "#A5D6A7",
    "exec_skip":  "#78909C",
    "error":      "#EF5350",
    "exec_timeout": "#FF8A65",
    "respawn":    "#CE93D8",
    "birth":      "#80CBC4",
    "savegame_preemptive": "#FFF176",
    "death":      "#EF9A9A",
}
DEFAULT_COLOR = "#E0E0E0"

FONT_SIZE = 14


def dark_palette():
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Base,            QColor(20, 20, 20))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(35, 35, 35))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Button,          QColor(45, 45, 45))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 100, 100))
    p.setColor(QPalette.ColorRole.Link,            QColor(100, 180, 255))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(60, 120, 200))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return p


# ── Journal Tab ──────────────────────────────────────────────────────
class JournalTab(QWidget):
    def __init__(self):
        super().__init__()
        self._last_pos = 0
        self._auto_scroll = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Status bar
        self.status = QLabel("Watching journal...")
        self.status.setFont(QFont("monospace", FONT_SIZE - 2))
        self.status.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(self.status)

        # Journal table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Time", "Kind", "Content"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont("monospace", FONT_SIZE))
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        # Click to expand content
        self.table.cellDoubleClicked.connect(self._show_full)
        layout.addWidget(self.table)

        # Detail view (expandable)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("monospace", FONT_SIZE))
        self.detail.setMaximumHeight(120)
        self.detail.setPlaceholderText("Double-click a row to see full content...")
        self.detail.setStyleSheet("background: #1a1a2e; color: #E0E0E0; border: 1px solid #333;")
        layout.addWidget(self.detail)


        # File watcher
        self.watcher = QFileSystemWatcher()
        if os.path.exists(JOURNAL_PATH):
            self.watcher.addPath(JOURNAL_PATH)
        self.watcher.fileChanged.connect(self._on_file_changed)

        # Initial load
        self._load_journal()

    def _load_journal(self):
        if not os.path.exists(JOURNAL_PATH):
            self.status.setText("Journal not found — is the creature running?")
            return
        with open(JOURNAL_PATH, encoding="utf-8") as f:
            f.seek(self._last_pos)
            new_lines = f.readlines()
            self._last_pos = f.tell()

        if not new_lines and self.table.rowCount() == 0:
            # Full load on first open
            with open(JOURNAL_PATH, encoding="utf-8") as f:
                all_lines = f.readlines()
                self._last_pos = f.tell()
            new_lines = all_lines

        for line in new_lines:
            try:
                e = json.loads(line)
                self._add_row(e)
            except json.JSONDecodeError:
                pass

        count = self.table.rowCount()
        self.status.setText(f"{count} journal entries  |  last updated: {time.strftime('%H:%M:%S')}")
        if self._auto_scroll and count > 0:
            self.table.scrollToBottom()

        # Re-add watcher if file was rotated
        if JOURNAL_PATH not in self.watcher.files():
            if os.path.exists(JOURNAL_PATH):
                self.watcher.addPath(JOURNAL_PATH)

    def _add_row(self, entry):
        row = self.table.rowCount()
        self.table.insertRow(row)
        ts = time.strftime("%H:%M:%S", time.localtime(entry.get("ts", 0)))
        kind = entry.get("kind", "")
        content = entry.get("content", "").replace("\n", " ")
        color = QColor(KIND_COLORS.get(kind, DEFAULT_COLOR))

        for col, text in enumerate([ts, kind, content]):
            item = QTableWidgetItem(text)
            item.setForeground(color)
            if col == 2:
                item.setData(Qt.ItemDataRole.UserRole, entry.get("content", ""))
            self.table.setItem(row, col, item)

    def _on_file_changed(self, path):
        self._load_journal()

    def _show_full(self, row, col):
        item = self.table.item(row, 2)
        if item:
            full = item.data(Qt.ItemDataRole.UserRole) or item.text()
            kind = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            ts = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            self.detail.setPlainText(f"[{ts}] {kind}:\n{full}")



# ── Memory Tab (tree-style, like Container tab) ────────────────────────────────
class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Status + refresh row
        top = QHBoxLayout()
        self.status = QLabel("Memory")
        self.status.setFont(QFont("monospace", FONT_SIZE - 2))
        self.status.setStyleSheet("color: #9E9E9E;")
        top.addWidget(self.status)
        top.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        # Horizontal splitter: tree (left) + detail (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Memory & Outputs")
        self.tree.setFont(QFont("monospace", FONT_SIZE))
        self.tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self.tree)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("monospace", FONT_SIZE - 1))
        self.detail.setPlaceholderText("Click any entry to read it here...")
        self.detail.setStyleSheet("background: #0d1117; color: #c9d1d9; border: 1px solid #333;")
        splitter.addWidget(self.detail)

        splitter.setSizes([420, 860])
        layout.addWidget(splitter)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        self.refresh()

    def _make_root(self, label, color):
        item = QTreeWidgetItem(self.tree, [label])
        item.setForeground(0, QColor(color))
        item.setFont(0, QFont("sans-serif", FONT_SIZE - 1, QFont.Weight.Bold))
        return item

    def refresh(self):
        # Remember which roots were expanded
        expanded = set()
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            if root.isExpanded():
                expanded.add(root.text(0).split("  ")[0])

        self.tree.clear()

        # -- Memory (gage view: exactly what the creature sees) --
        # Rendered via the live memory.py layer functions so this panel can
        # never drift from the creature's actual context. Control-state keys
        # are surfaced separately below (the creature acts on them but no
        # longer sees them in its ranked memory).
        try:
            cur = gmem._cur_slug(MIND_DIR)
            l1 = gmem.layer1(MIND_DIR)
            rest = gmem._ranked_rest(MIND_DIR)
            split = gmem.LAYER2_MAX - gmem.LAYER1_SIZE
            l2 = rest[:split]
            l3 = rest[split:]
            total_all = gmem.count(MIND_DIR)
            control_n = total_all - (len(l1) + len(rest))
        except Exception as e:
            self.status.setText(f"DB error: {e}")
            return
        total = total_all

        STATE_NAMES = {0: "ACTIVE", 1: "STANDING", 2: "ARCHIVED"}
        STATE_COLORS = {0: "#80DEEA", 1: "#B0BEC5", 2: "#9E9E9E"}

        def _gtag(m):
            st = gmem._state(m.get("project", ""), cur)
            return st, f"{STATE_NAMES[st]} / {m.get('project') or '-'}"

        # Working Memory (Layer 1) -- 5 newest non-control, full content
        l1_root = self._make_root(
            f"Working Memory  ({len(l1)} entries, full content each cycle)", "#4CAF50")
        if l1:
            for m in l1:
                st, tag = _gtag(m)
                ts = time.strftime("%m-%d %H:%M", time.localtime(m["updated"]))
                headline = m["value"].replace("\n", " ")[:78]
                child = QTreeWidgetItem(l1_root, [f"{m['key']}  -  {headline}   [{tag}]  [{ts}]"])
                child.setForeground(0, QColor("#C8E6C9"))
                child.setData(0, Qt.ItemDataRole.UserRole, ("memory", m["key"], m["value"]))
        else:
            empty = QTreeWidgetItem(l1_root, ["(no memories yet -- creature has not called remember)"])
            empty.setForeground(0, QColor("#555"))

        # Intermediate (Layer 2) -- ordered by (gage state, recency); active first
        l2_root = self._make_root(
            f"Intermediate  ({len(l2)} entries, headline -- active first)", "#64B5F6")
        for m in l2:
            st, tag = _gtag(m)
            ts = time.strftime("%m-%d %H:%M", time.localtime(m["updated"]))
            headline = m["value"].replace("\n", " ")[:78]
            child = QTreeWidgetItem(l2_root, [f"{m['key']}  -  {headline}   [{tag}]  [{ts}]"])
            child.setForeground(0, QColor(STATE_COLORS[st]))
            child.setData(0, Qt.ItemDataRole.UserRole, ("memory", m["key"], m["value"]))
        if not l2:
            empty = QTreeWidgetItem(l2_root, ["(empty -- fills as working memory grows past 5)"])
            empty.setForeground(0, QColor("#555"))

        # Archive (Layer 3) -- ordered by (gage state, recency); keys only
        l3_root = self._make_root(
            f"Archive  ({len(l3)} entries, key only in context)", "#9E9E9E")
        for m in l3:
            st, tag = _gtag(m)
            ts = time.strftime("%m-%d %H:%M", time.localtime(m["updated"]))
            child = QTreeWidgetItem(l3_root, [f"{m['key']}   [{tag}]  [{ts}]"])
            child.setForeground(0, QColor(STATE_COLORS[st]))
            child.setData(0, Qt.ItemDataRole.UserRole, ("memory", m["key"], m["value"]))
        if not l3:
            empty = QTreeWidgetItem(l3_root, ["(empty)"])
            empty.setForeground(0, QColor("#555"))

        # Control state -- executive keys, hidden from the creature's ranked
        # layers; shown here so the overview is complete.
        ctrl_root = self._make_root(
            f"Control state  ({control_n} keys -- not in creature's ranked memory)", "#FFB74D")
        _any_ctrl = False
        for k in ("current-project", "current-phase", "current-plan",
                  "current-project-done-when", "completed-projects"):
            row = gmem.retrieve(MIND_DIR, k)
            if not row:
                continue
            _any_ctrl = True
            ts = time.strftime("%m-%d %H:%M", time.localtime(row["updated"]))
            headline = row["value"].replace("\n", " ")[:90]
            child = QTreeWidgetItem(ctrl_root, [f"{k}  -  {headline}  [{ts}]"])
            child.setForeground(0, QColor("#FFE0B2"))
            child.setData(0, Qt.ItemDataRole.UserRole, ("memory", k, row["value"]))
        if not _any_ctrl:
            empty = QTreeWidgetItem(ctrl_root, ["(no control state yet)"])
            empty.setForeground(0, QColor("#555"))

        # Pending done-gate block (transient; shown to creature next cycle)
        _dbpath = os.path.join(MIND_DIR, "done_block.txt")
        if os.path.exists(_dbpath):
            try:
                _reason = open(_dbpath, encoding="utf-8").read().strip()
            except Exception:
                _reason = ""
            if _reason:
                dg_root = self._make_root("Pending done-gate block (next cycle)", "#EF5350")
                child = QTreeWidgetItem(dg_root, [_reason.replace("\n", " ")[:200]])
                child.setForeground(0, QColor("#FFCDD2"))

        # Outputs (think_end entries)
        thoughts = []
        if os.path.exists(JOURNAL_PATH):
            try:
                with open(JOURNAL_PATH, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                e = json.loads(line)
                                if e.get("kind") == "think_end":
                                    thoughts.append(e)
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass
        thoughts = thoughts[::-1]

        out_label = f"Outputs  ({len(thoughts)} think_end cycles)"
        out_root = self._make_root(out_label, "#64B5F6")
        for e in thoughts:
            ts = time.strftime("%m-%d %H:%M", time.localtime(e.get("ts", 0)))
            preview = e.get("content", "").replace("\n", " ")[:80]
            full = e.get("content", "")
            child = QTreeWidgetItem(out_root, [f"{ts}  —  {preview}"])
            child.setForeground(0, QColor("#B0BEC5"))
            child.setData(0, Qt.ItemDataRole.UserRole, ("output", ts, full))
        if not thoughts:
            empty = QTreeWidgetItem(out_root, ["(no outputs yet)"])
            empty.setForeground(0, QColor("#555"))

        # Restore expansion state (defaults: Working Memory + Outputs open)
        defaults_open = {"Working Memory", "Outputs"}
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            key = root.text(0).split("  ")[0]
            should_open = key in expanded if expanded else key in defaults_open
            root.setExpanded(should_open)

        self.status.setText(
            f"{total} memories  |  "
            f"working: {len(l1)}  intermediate: {len(l2)}  archive: {len(l3)}  |  "
            f"outputs: {len(thoughts)}  |  {time.strftime('%H:%M:%S')}"
        )

    def _on_item_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        if kind == "memory":
            _, key, value = data
            self.detail.setPlainText(f"[{key}]\n\n{value}")
        elif kind == "output":
            _, ts, full = data
            self.detail.setPlainText(f"[{ts}]\n\n{full}")


# ── Container Tab ────────────────────────────────────────────────────
class ContainerTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.status = QLabel("Container files")
        self.status.setFont(QFont("monospace", FONT_SIZE - 2))
        self.status.setStyleSheet("color: #9E9E9E;")
        top.addWidget(self.status)
        top.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("/workspace")
        self.tree.setFont(QFont("monospace", FONT_SIZE))
        self.tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self.tree)

        self.file_view = QTextEdit()
        self.file_view.setReadOnly(True)
        self.file_view.setFont(QFont("monospace", FONT_SIZE - 1))
        self.file_view.setPlaceholderText("Click a file to read it...")
        self.file_view.setStyleSheet("background: #0d1117; color: #c9d1d9; border: 1px solid #333;")
        splitter.addWidget(self.file_view)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(10000)
        self.refresh()

    def _docker_exec(self, cmd):
        r = subprocess.run(
            ["docker", "exec", CONTAINER, "bash", "-c", cmd],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()

    def refresh(self):
        # Check container is running
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER],
            capture_output=True, text=True
        )
        if r.stdout.strip() != "true":
            self.status.setText("Container not running")
            self.tree.clear()
            return

        try:
            output = self._docker_exec("find /workspace -maxdepth 3 ! -path '*/.git/*' -not -name '.git' 2>/dev/null")
        except Exception as e:
            self.status.setText(f"Error: {e}")
            return

        self.tree.clear()
        root_item = QTreeWidgetItem(self.tree, ["/workspace"])
        nodes = {"/workspace": root_item}

        for path in sorted(output.splitlines()):
            if path == "/workspace":
                continue
            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_node = nodes.get(parent_path, root_item)
            item = QTreeWidgetItem(parent_node, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            nodes[path] = item

        root_item.setExpanded(True)
        self.status.setText(f"Container running  |  {time.strftime('%H:%M:%S')}")

    def _on_item_clicked(self, item, col):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        try:
            content = self._docker_exec(f"cat '{path}' 2>/dev/null | head -200")
            if content:
                self.file_view.setPlainText(content)
            else:
                self.file_view.setPlainText(f"(empty or directory: {path})")
        except Exception as e:
            self.file_view.setPlainText(f"Error reading {path}: {e}")


# ── Quota Tab ────────────────────────────────────────────────────────
class QuotaTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Provider Quota Status")
        title.setFont(QFont("sans-serif", FONT_SIZE + 2, QFont.Weight.Bold))
        title.setStyleSheet("color: #64B5F6;")
        top.addWidget(title)
        top.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("sans-serif", FONT_SIZE))
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setFixedWidth(100)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.cards_layout = QVBoxLayout()
        layout.addLayout(self.cards_layout)
        layout.addStretch()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(10000)
        self.refresh()

    def refresh(self):
        # Clear cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            import yaml
            with open(CONFIG_PATH) as f:
                cfg = yaml.safe_load(f)
            providers = cfg.get("providers", [])
        except Exception as e:
            lbl = QLabel(f"Could not load config: {e}")
            lbl.setStyleSheet("color: #EF5350;")
            self.cards_layout.addWidget(lbl)
            return

        state = {}
        try:
            with open(QUOTA_PATH) as f:
                state = json.load(f)
        except Exception:
            pass

        for p in providers:
            key = p["key"]
            enabled = p.get("enabled", True)
            limit = p.get("quota", {}).get("limit", "?")
            resets = p.get("quota", {}).get("resets", "?")
            used = state.get(key, {}).get("used", 0)
            reset_at = state.get(key, {}).get("reset_at", 0)
            reset_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(reset_at)) if reset_at else "unknown"

            # Ceiling: prefer the discovered limit (real, from a 429); fall back to
            # the config limit so the page matches the runtime's availability check.
            discovered = state.get(key, {}).get("discovered_limit")
            cfg_limit = limit if isinstance(limit, (int, float)) else None
            ceiling = discovered if discovered is not None else cfg_limit
            remaining = (ceiling - used) if ceiling is not None else None
            pct = int(100 * used / ceiling) if ceiling and ceiling > 0 else None
            # exhausted_at is the definitive "currently rate-limited" signal: the
            # keychain sets it on a quota 429 and clears it only when a call
            # succeeds (quota recovered) or the window rolls over. While it is set
            # the runtime keeps 429-ing and pausing -- so the provider is NOT green.
            exhausted_at = state.get(key, {}).get("exhausted_at")

            if not enabled:
                status_color = "#9E9E9E"
                status_text = "DISABLED"
            elif exhausted_at is not None:
                status_color = "#EF5350"
                status_text = "EXHAUSTED"
            elif remaining is not None and remaining <= 0:
                status_color = "#EF5350"
                status_text = "EXHAUSTED"
            elif remaining is not None and ceiling and remaining < (ceiling * 0.2):
                status_color = "#FFB74D"
                status_text = "LOW"
            elif used == 0:
                status_color = "#9E9E9E"
                status_text = "FRESH"
            else:
                status_color = "#4CAF50"
                status_text = "RUNNING"

            card = QFrame()
            card.setStyleSheet(f"QFrame {{ background: #1e1e2e; border: 1px solid {status_color}; border-radius: 6px; padding: 8px; }}")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            row1 = QHBoxLayout()
            name_lbl = QLabel(p.get("display_name", key))
            name_lbl.setFont(QFont("sans-serif", FONT_SIZE + 1, QFont.Weight.Bold))
            name_lbl.setStyleSheet(f"color: {status_color}; border: none;")
            status_lbl = QLabel(status_text)
            status_lbl.setFont(QFont("sans-serif", FONT_SIZE))
            status_lbl.setStyleSheet(f"color: {status_color}; border: none;")
            row1.addWidget(name_lbl)
            row1.addStretch()
            row1.addWidget(status_lbl)
            card_layout.addLayout(row1)

            model_lbl = QLabel(f"Model: {p.get('model_id', '?')}")
            model_lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            model_lbl.setStyleSheet("color: #9E9E9E; border: none;")
            card_layout.addWidget(model_lbl)

            if ceiling is not None and exhausted_at is not None:
                usage_lbl = QLabel(f"Used: {used} / {ceiling}  --  rate-limited, cooling down")
            elif ceiling is not None:
                usage_lbl = QLabel(f"Used: {used} / {ceiling}  ({pct}%)   Remaining: {max(0, remaining)}")
            else:
                usage_lbl = QLabel(f"Used: {used} / ?  (ceiling unknown until first 429)")
            usage_lbl.setFont(QFont("monospace", FONT_SIZE))
            usage_lbl.setStyleSheet("color: #E0E0E0; border: none;")
            card_layout.addWidget(usage_lbl)

            # Reset interval display
            discovered_interval = state.get(key, {}).get("discovered_reset_interval")
            exhausted_at = state.get(key, {}).get("exhausted_at")
            if discovered_interval is not None:
                h, m = int(discovered_interval // 3600), int((discovered_interval % 3600) // 60)
                interval_str = f"{h}h {m:02d}m" if h else f"{m}m"
                if exhausted_at:
                    waited = time.time() - exhausted_at
                    wh, wm = int(waited // 3600), int((waited % 3600) // 60)
                    waited_str = f"{wh}h {wm:02d}m" if wh else f"{wm}m"
                    reset_text = f"Reset interval: {waited_str} waited / {interval_str} last known"
                else:
                    reset_text = f"Reset interval: last known {interval_str}  |  Next reset: {reset_str}"
            elif exhausted_at:
                waited = time.time() - exhausted_at
                wh, wm = int(waited // 3600), int((waited % 3600) // 60)
                waited_str = f"{wh}h {wm:02d}m" if wh else f"{wm}m"
                reset_text = f"Reset interval: {waited_str} waited / ? (first window)"
            else:
                reset_text = f"Resets: {reset_str}"
            reset_lbl = QLabel(reset_text)
            reset_lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            reset_lbl.setStyleSheet("color: #9E9E9E; border: none;")
            card_layout.addWidget(reset_lbl)

            self.cards_layout.addWidget(card)


# ── Chat Tab ─────────────────────────────────────────────────────────
class ChatTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.status = QLabel("Chat with the creature — your messages queue until its next cycle")
        self.status.setFont(QFont("monospace", FONT_SIZE - 2))
        self.status.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(self.status)

        # Scroll area for chat bubbles
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #333; background: #0d1117; }")
        self.bubble_widget = QWidget()
        self.bubble_layout = QVBoxLayout(self.bubble_widget)
        self.bubble_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.bubble_layout.setSpacing(8)
        self.bubble_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll.setWidget(self.bubble_widget)
        layout.addWidget(self.scroll)

        # Input row
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message and press Enter...")
        self.input.setFont(QFont("sans-serif", FONT_SIZE))
        self.input.setStyleSheet("background: #1e1e2e; color: #E0E0E0; border: 1px solid #555; padding: 6px;")
        self.input.returnPressed.connect(self._send)
        send_btn = QPushButton("Send")
        send_btn.setFont(QFont("sans-serif", FONT_SIZE))
        send_btn.setFixedWidth(80)
        send_btn.clicked.connect(self._send)
        input_row.addWidget(self.input)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        self._last_count = 0

        # File watcher
        self.watcher = QFileSystemWatcher()
        if os.path.exists(CHAT_PATH):
            self.watcher.addPath(CHAT_PATH)
        self.watcher.fileChanged.connect(self._refresh)

        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(3000)

        self._refresh()

    def _load_chat(self):
        if not os.path.exists(CHAT_PATH):
            return []
        entries = []
        with open(CHAT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    def _refresh(self):
        entries = [e for e in self._load_chat()
                   if e.get("kind") in ("from_tue", "from_creature")]
        if len(entries) == self._last_count:
            return
        self._last_count = len(entries)

        # Rebuild bubbles
        while self.bubble_layout.count():
            item = self.bubble_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for e in entries:
            kind = e.get("kind")
            content = e.get("content", "")
            ts = time.strftime("%H:%M", time.localtime(e.get("ts", 0)))
            is_tue = (kind == "from_tue")

            row = QHBoxLayout()
            bubble = QLabel(f"<b>{'Tue' if is_tue else 'Creature'}</b> <span style=\'color:#666;font-size:11px;\'>{ts}</span><br>{content}")
            bubble.setWordWrap(True)
            bubble.setFont(QFont("sans-serif", FONT_SIZE))
            bubble.setTextFormat(Qt.TextFormat.RichText)
            bubble.setMaximumWidth(700)
            bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

            if is_tue:
                bubble.setStyleSheet(
                    "background: #1a3a5c; color: #E0E0E0; border-radius: 10px; padding: 8px 12px;"
                )
                row.addStretch()
                row.addWidget(bubble)
            else:
                bubble.setStyleSheet(
                    "background: #1e2e1e; color: #A5D6A7; border-radius: 10px; padding: 8px 12px;"
                )
                row.addWidget(bubble)
                row.addStretch()

            container = QWidget()
            container.setLayout(row)
            self.bubble_layout.addWidget(container)

        # Pending indicator
        pending = [e for e in self._load_chat()
                   if e.get("kind") == "from_tue" and not e.get("read", True)]
        if pending:
            lbl = QLabel(f"⏳  {len(pending)} message(s) queued — waiting for next creature cycle")
            lbl.setStyleSheet("color: #FFB74D; padding: 4px;")
            lbl.setFont(QFont("sans-serif", FONT_SIZE - 1))
            self.bubble_layout.addWidget(lbl)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

        # Re-add watcher
        if CHAT_PATH not in self.watcher.files() and os.path.exists(CHAT_PATH):
            self.watcher.addPath(CHAT_PATH)

        self.status.setText(f"{len(entries)} messages  |  {time.strftime('%H:%M:%S')}")

    def _send(self):
        msg = self.input.text().strip()
        if not msg:
            return
        try:
            entry = {"ts": time.time(), "kind": "from_tue", "content": msg, "read": False}
            with open(CHAT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self.input.clear()
            self._refresh()
            if CHAT_PATH not in self.watcher.files():
                self.watcher.addPath(CHAT_PATH)
        except Exception as e:
            self.status.setText(f"Error sending: {e}")


# ── Main Window ──────────────────────────────────────────────────────

def _make_spine_icon() -> "QIcon":
    """Growing Spine icon: a golden vertebral column with three green
    sprouts curving upward from its top. Drawn with QPainter so there
    is no external file dependency."""
    try:
        SIZE = 64
        px = QPixmap(SIZE, SIZE)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bone  = QColor("#D4A853")   # warm golden vertebrae
        cord  = QColor("#9B6E3A")   # darker connecting cord
        green = QColor("#5CB85C")   # sprout stem
        leaf  = QColor("#4CAF50")   # leaf tips
        dark  = QColor("#3E2A0A")   # outline

        # Spine cord (thin central line, lower two-thirds)
        p.setPen(QPen(cord, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(32, 22, 32, 60)

        # Four vertebrae (rounded rects)
        p.setPen(QPen(dark, 1.0))
        p.setBrush(QBrush(bone))
        for i in range(4):
            p.drawRoundedRect(19, 24 + i * 10, 26, 6, 3, 3)

        # Sprout stems
        pen = QPen(green, 2.5, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        p.drawLine(32, 22, 32, 8)           # centre stem, straight up

        left = QPainterPath()               # left stem, curves up-left
        left.moveTo(32, 20)
        left.cubicTo(30, 15, 21, 13, 15, 8)
        p.drawPath(left)

        right = QPainterPath()              # right stem, curves up-right
        right.moveTo(32, 20)
        right.cubicTo(34, 15, 43, 13, 49, 8)
        p.drawPath(right)

        # Leaf tips
        p.setPen(QPen(dark, 0.5))
        p.setBrush(QBrush(leaf))
        p.drawEllipse(28, 4,  9, 6)         # centre
        p.drawEllipse(11, 5,  8, 6)         # left
        p.drawEllipse(45, 5,  8, 6)         # right

        p.end()
        return QIcon(px)
    except Exception:
        return QIcon()                      # fallback: null icon, no crash


class ObserverWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growing Spine — Observer")
        self.setWindowIcon(_make_spine_icon())
        self.resize(1280, 800)

        tabs = QTabWidget()
        tabs.setFont(QFont("sans-serif", FONT_SIZE))
        tabs.addTab(JournalTab(),   "📋  Journal")
        tabs.addTab(MemoryTab(),    "🧠  Memory")
        tabs.addTab(ContainerTab(), "📁  Container")
        tabs.addTab(QuotaTab(),     "📊  Quota")
        tabs.addTab(ChatTab(),      "💬  Chat")

        self.setCentralWidget(tabs)

        # Status bar
        self.statusBar().setFont(QFont("monospace", FONT_SIZE - 2))
        self.statusBar().showMessage("Growing Spine Observer — running")


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(_make_spine_icon())
    app.setPalette(dark_palette())
    app.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #333; }
        QTabBar::tab { background: #2a2a2a; color: #aaa; padding: 10px 22px; font-size: 15px; }
        QTabBar::tab:selected { background: #1e1e2e; color: #fff; border-bottom: 2px solid #64B5F6; }
        QTabBar::tab:hover { background: #333; }
        QHeaderView::section { background: #2a2a2a; color: #aaa; padding: 4px; border: none; font-size: 13px; }
        QTreeWidget { border: 1px solid #333; }
        QPushButton { background: #2a2a3e; color: #E0E0E0; border: 1px solid #555; padding: 4px 12px; border-radius: 3px; }
        QPushButton:hover { background: #3a3a5e; }
        QScrollBar:vertical { background: #1e1e1e; width: 10px; }
        QScrollBar::handle:vertical { background: #444; border-radius: 4px; }
    """)

    win = ObserverWindow()
    win.showMaximized()
    sys.exit(app.exec())
