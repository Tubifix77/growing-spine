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
from PyQt6.QtGui import QColor, QFont, QPalette, QFontMetrics

# ── Paths ────────────────────────────────────────────────────────────
MIND_DIR      = os.path.expanduser("~/growing-spine-mind")
JOURNAL_PATH  = os.path.join(MIND_DIR, "journal.jsonl")
MEMORY_DB     = os.path.join(MIND_DIR, "memory.db")
TUE_MSG_PATH  = os.path.join(MIND_DIR, "tue-message.txt")
CHAT_PATH     = os.path.join(MIND_DIR, "chat.jsonl")
CONFIG_PATH   = os.path.expanduser("~/growing-spine/config.yaml")
QUOTA_PATH    = os.path.expanduser("~/growing-spine/keychain/quota_state.json")
CONTAINER     = "growing-spine-body"

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



# ── Memory Tab ───────────────────────────────────────────────────────
class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Status + refresh
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

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Detail panel at bottom
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("monospace", FONT_SIZE))
        self.detail.setMaximumHeight(400)
        self.detail.setPlaceholderText("Click any memory to see full content...")
        self.detail.setStyleSheet("background: #0d1117; color: #E0E0E0; border: 1px solid #444;")
        layout.addWidget(self.detail)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        self.refresh()

    def _section_label(self, text, color):
        lbl = QLabel(text)
        lbl.setFont(QFont("sans-serif", FONT_SIZE - 1, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; padding: 4px 2px 2px 2px;")
        return lbl

    def _make_table(self, headers, stretch_col):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        for i in range(len(headers)):
            if i == stretch_col:
                t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setFont(QFont("monospace", FONT_SIZE))
        t.verticalHeader().setDefaultSectionSize(32)
        t.setAlternatingRowColors(True)
        t.setWordWrap(False)
        return t

    def refresh(self):
        if not os.path.exists(MEMORY_DB):
            self.status.setText("memory.db not found — creature has not written any memories yet")
            return
        try:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT key, value, tags, updated FROM memories ORDER BY id DESC"
            ).fetchall()
            conn.close()
        except Exception as e:
            self.status.setText(f"DB error: {e}")
            return

        # Clear content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(rows)
        l1 = rows[:5]
        l2 = rows[5:50]
        l3 = rows[50:]

        # ── Layer 1: Working memory ──
        self.content_layout.addWidget(
            self._section_label(f"🟢  Working memory — last {len(l1)} entries (full content, injected every cycle)", "#4CAF50"))
        if l1:
            for key, value, tags, updated in l1:
                card = QFrame()
                card.setStyleSheet("QFrame { background: #0d1f0d; border: 1px solid #2d5a2d; border-radius: 4px; padding: 6px; }")
                card_layout = QVBoxLayout(card)
                card_layout.setSpacing(2)
                card_layout.setContentsMargins(8, 6, 8, 6)
                ts = time.strftime("%m-%d %H:%M", time.localtime(updated))
                header = QLabel(f"<b style=\'color:#4CAF50;\'>{key}</b>"
                                f"<span style=\'color:#555; font-size:11px;\'> — {ts}"
                                + (f" — {tags}" if tags else "") + "</span>")
                header.setTextFormat(Qt.TextFormat.RichText)
                header.setFont(QFont("monospace", FONT_SIZE - 1))
                body = QLabel(value)
                body.setWordWrap(True)
                body.setFont(QFont("monospace", FONT_SIZE - 1))
                body.setStyleSheet("color: #C8E6C9;")
                card_layout.addWidget(header)
                card_layout.addWidget(body)
                card.mousePressEvent = lambda e, k=key, v=value: self.detail.setPlainText("[" + k + "]" + chr(10) + v)
                self.content_layout.addWidget(card)
        else:
            lbl = QLabel("  (no memories yet — creature has not called remember)")
            lbl.setStyleSheet("color: #555; padding: 4px 8px;")
            lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            self.content_layout.addWidget(lbl)

        # ── Layer 2: Intermediate ──
        self.content_layout.addWidget(
            self._section_label(f"🔵  Intermediate — {len(l2)} entries (one-liner injected, click for full)", "#64B5F6"))
        if l2:
            t2 = self._make_table(["Key", "Preview", "Updated"], stretch_col=1)
            for key, value, tags, updated in l2:
                r = t2.rowCount()
                t2.insertRow(r)
                ts = time.strftime("%m-%d %H:%M", time.localtime(updated))
                headline = value.replace("\n", " ")[:120]
                for col, (text, color) in enumerate([
                    (key,      "#64B5F6"),
                    (headline, "#B0BEC5"),
                    (ts,       "#555"),
                ]):
                    item = QTableWidgetItem(text)
                    item.setForeground(QColor(color))
                    if col == 1:
                        item.setData(Qt.ItemDataRole.UserRole, (key, value))
                    t2.setItem(r, col, item)
            t2.cellClicked.connect(lambda row, col, t=t2: self._expand(t, row))
            t2.setMaximumHeight(min(len(l2) * 34 + 30, 300))
            self.content_layout.addWidget(t2)
        else:
            lbl = QLabel("  (empty — fills as working memory grows past 5)")
            lbl.setStyleSheet("color: #555; padding: 4px 8px;")
            lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            self.content_layout.addWidget(lbl)

        # ── Layer 3: Archive ──
        self.content_layout.addWidget(
            self._section_label(f"⚫  Archive — {len(l3)} entries (key only injected, click for full)", "#9E9E9E"))
        if l3:
            t3 = self._make_table(["Key", "Updated"], stretch_col=0)
            for key, value, tags, updated in l3:
                r = t3.rowCount()
                t3.insertRow(r)
                ts = time.strftime("%m-%d %H:%M", time.localtime(updated))
                for col, (text, color) in enumerate([
                    (key, "#9E9E9E"),
                    (ts,  "#555"),
                ]):
                    item = QTableWidgetItem(text)
                    item.setForeground(QColor(color))
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole, (key, value))
                    t3.setItem(r, col, item)
            t3.cellClicked.connect(lambda row, col, t=t3: self._expand(t, row))
            t3.setMaximumHeight(min(len(l3) * 34 + 30, 200))
            self.content_layout.addWidget(t3)
        else:
            lbl = QLabel("  (empty — fills as intermediate grows past 50)")
            lbl.setStyleSheet("color: #555; padding: 4px 8px;")
            lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            self.content_layout.addWidget(lbl)


        # ── Recent thoughts (think_end) ──
        self.content_layout.addWidget(
            self._section_label("💭  Growing Spine outputs (click to read full)", "#64B5F6"))
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
        thoughts = thoughts[::-1]  # newest first
        if thoughts:
            tt = self._make_table(["Time", "Preview"], stretch_col=1)
            for e in thoughts:
                r = tt.rowCount()
                tt.insertRow(r)
                ts = time.strftime("%m-%d %H:%M", time.localtime(e.get("ts", 0)))
                preview = e.get("content", "").replace("\n", " ")[:120]
                full = e.get("content", "")
                for col, (text, color) in enumerate([
                    (ts,      "#64B5F6"),
                    (preview, "#B0BEC5"),
                ]):
                    item = QTableWidgetItem(text)
                    item.setForeground(QColor(color))
                    if col == 1:
                        item.setData(Qt.ItemDataRole.UserRole, (ts, full))
                    tt.setItem(r, col, item)
            tt.setFixedHeight(226)  # 6 rows * 32px + 30px header, measured
            tt.setMaximumHeight(226)  # 6 rows * 32px + 30px header
            self.content_layout.addWidget(tt)
        else:
            lbl = QLabel("  (no thoughts yet)")
            lbl.setStyleSheet("color: #555; padding: 4px 8px;")
            lbl.setFont(QFont("monospace", FONT_SIZE - 1))
            self.content_layout.addWidget(lbl)

        self.status.setText(
            f"{total} memories  |  "
            f"working: {len(l1)}  intermediate: {len(l2)}  archive: {len(l3)}  |  "
            f"{time.strftime('%H:%M:%S')}"
        )

    def _expand(self, table, row):
        item = table.item(row, 0)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                key, value = data
                self.detail.setPlainText("[" + key + "]" + chr(10) + value)

    def _expand_thought(self, table, row):
        item = table.item(row, 1)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                ts, full = data
                self.detail.setPlainText("[" + ts + "]" + chr(10) + full)


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

            remaining = (limit - used) if isinstance(limit, int) else "?"
            pct = int(100 * used / limit) if isinstance(limit, int) and limit > 0 else 0

            if not enabled:
                status_color = "#9E9E9E"
                status_text = "DISABLED"
            elif isinstance(remaining, int) and remaining <= 0:
                status_color = "#EF5350"
                status_text = "EXHAUSTED"
            elif isinstance(remaining, int) and remaining < limit * 0.2:
                status_color = "#FFB74D"
                status_text = "LOW"
            else:
                status_color = "#4CAF50"
                status_text = "OK"

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

            usage_lbl = QLabel(f"Used: {used} / {limit}  ({pct}%)   Remaining: {remaining}")
            usage_lbl.setFont(QFont("monospace", FONT_SIZE))
            usage_lbl.setStyleSheet("color: #E0E0E0; border: none;")
            card_layout.addWidget(usage_lbl)

            reset_lbl = QLabel(f"Resets: {reset_str}")
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
class ObserverWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growing Spine — Observer")
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
