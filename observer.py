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

        # Chat input row
        chat_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Send a message to the creature (press Enter)...")
        self.chat_input.setFont(QFont("sans-serif", FONT_SIZE))
        self.chat_input.returnPressed.connect(self._send_message)
        self.chat_input.setStyleSheet("background: #1e1e2e; color: #E0E0E0; border: 1px solid #555; padding: 4px;")
        send_btn = QPushButton("Send")
        send_btn.setFont(QFont("sans-serif", FONT_SIZE))
        send_btn.clicked.connect(self._send_message)
        send_btn.setFixedWidth(80)
        chat_row.addWidget(self.chat_input)
        chat_row.addWidget(send_btn)
        layout.addLayout(chat_row)

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

    def _send_message(self):
        msg = self.chat_input.text().strip()
        if not msg:
            return
        try:
            with open(TUE_MSG_PATH, "w", encoding="utf-8") as f:
                f.write(msg)
            self.chat_input.clear()
            self.chat_input.setPlaceholderText(f"Sent: {msg[:60]}... (waiting for next cycle)")
        except Exception as e:
            self.chat_input.setPlaceholderText(f"Error: {e}")


# ── Memory Tab ───────────────────────────────────────────────────────
class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Layer", "Key", "Value", "Tags", "Updated"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont("monospace", FONT_SIZE))
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.cellDoubleClicked.connect(self._show_full)
        layout.addWidget(self.table)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("monospace", FONT_SIZE))
        self.detail.setMaximumHeight(70)
        self.detail.setPlaceholderText("Double-click a row to see full value...")
        self.detail.setStyleSheet("background: #1a1a2e; color: #E0E0E0; border: 1px solid #333;")
        layout.addWidget(self.detail)

        # Journal section label
        journal_label = QLabel("Recent journal (last 5 entries — also injected into creature context each cycle)")
        journal_label.setFont(QFont("monospace", FONT_SIZE - 2))
        journal_label.setStyleSheet("color: #FFB74D; padding-top: 6px;")
        layout.addWidget(journal_label)

        self.journal_table = QTableWidget(0, 3)
        self.journal_table.setHorizontalHeaderLabels(["Time", "Kind", "Content"])
        self.journal_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.journal_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.journal_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.journal_table.verticalHeader().setVisible(False)
        self.journal_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.journal_table.setFont(QFont("monospace", FONT_SIZE - 1))
        self.journal_table.verticalHeader().setDefaultSectionSize(28)
        self.journal_table.setMaximumHeight(180)
        layout.addWidget(self.journal_table)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        self.refresh()

    def refresh(self):
        if not os.path.exists(MEMORY_DB):
            self.status.setText("memory.db not found")
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

        self.table.setRowCount(0)
        total = len(rows)

        for idx, (key, value, tags, updated) in enumerate(rows):
            r = self.table.rowCount()
            self.table.insertRow(r)
            ts = time.strftime("%m-%d %H:%M", time.localtime(updated))

            # Determine layer
            if idx < 5:
                layer = "working"
                preview = value.replace("\n", " ")[:200]
                layer_color = QColor("#4CAF50")   # green
            elif idx < 50:
                layer = "intermediate"
                preview = value.replace("\n", " ")[:120]
                layer_color = QColor("#64B5F6")   # blue
            else:
                layer = "archive"
                preview = ""                       # theme only — key is enough
                layer_color = QColor("#9E9E9E")   # grey

            layer_item = QTableWidgetItem(layer)
            layer_item.setForeground(layer_color)
            key_item = QTableWidgetItem(key)
            key_item.setForeground(layer_color)
            preview_item = QTableWidgetItem(preview)
            preview_item.setForeground(QColor(DEFAULT_COLOR))
            preview_item.setData(Qt.ItemDataRole.UserRole, value)
            tags_item = QTableWidgetItem(tags or "")
            tags_item.setForeground(QColor("#9E9E9E"))
            ts_item = QTableWidgetItem(ts)
            ts_item.setForeground(QColor("#9E9E9E"))

            self.table.setItem(r, 0, layer_item)
            self.table.setItem(r, 1, key_item)
            self.table.setItem(r, 2, preview_item)
            self.table.setItem(r, 3, tags_item)
            self.table.setItem(r, 4, ts_item)

        self.status.setText(
            f"{total} memories  |  "
            f"working: {min(total,5)}  "
            f"intermediate: {max(0,min(total,50)-5)}  "
            f"archive: {max(0,total-50)}  |  "
            f"{time.strftime('%H:%M:%S')}"
        )

        # Refresh journal section
        self.journal_table.setRowCount(0)
        if os.path.exists(JOURNAL_PATH):
            try:
                with open(JOURNAL_PATH, encoding="utf-8") as f:
                    entries = [json.loads(l) for l in f if l.strip()]
                for e in entries[-5:]:
                    r = self.journal_table.rowCount()
                    self.journal_table.insertRow(r)
                    ts = time.strftime("%H:%M:%S", time.localtime(e.get("ts", 0)))
                    kind = e.get("kind", "")
                    text = e.get("content", "").replace("\n", " ")[:200]
                    color = QColor(KIND_COLORS.get(kind, DEFAULT_COLOR))
                    for col, val in enumerate([ts, kind, text]):
                        item = QTableWidgetItem(val)
                        item.setForeground(color)
                        self.journal_table.setItem(r, col, item)
            except Exception:
                pass

    def _show_full(self, row, col):
        item = self.table.item(row, 2)
        if item:
            key = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            layer = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            full = item.data(Qt.ItemDataRole.UserRole) or item.text()
            self.detail.setPlainText(f"[{layer}] [{key}]\n{full}")


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
