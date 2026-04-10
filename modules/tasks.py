from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from core.database import DatabaseManager
from core.styles import Colors


class TasksModule(QWidget):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._create_table()
        self._build_ui()

    def _create_table(self):
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date    TEXT,
                priority    TEXT DEFAULT 'normal',
                status      TEXT DEFAULT 'todo',
                category    INTEGER DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self.db.conn.commit()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        for text, size, color in [
            ("✅", 48, Colors.SECONDARY_TEXT),
            ("Задачи", 18, Colors.SECONDARY_TEXT),
            ("Раздел в разработке", 13, Colors.SEPARATOR),
        ]:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {color}; font-size: {size}px; background: transparent;"
            )
            layout.addWidget(lbl)