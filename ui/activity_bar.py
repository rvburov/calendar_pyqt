from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from core.styles import Colors


class ActivityBar(QWidget):
    section_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(49)
        self._active = 0

        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        inner = QWidget()
        inner.setStyleSheet(f"background: {Colors.ACTIVITY_BAR};")
        inner.setFixedWidth(48)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self._btns = []
        for i, (icon, tip) in enumerate([("📅", "Календарь"), ("✅", "Задачи")]):
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self._btns.append(btn)

        layout.addStretch()

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: #C8C8C8; border: none;")

        h_layout.addWidget(inner)
        h_layout.addWidget(line)
        self._update_styles()

    def _on_click(self, idx: int):
        self._active = idx
        self._update_styles()
        self.section_changed.emit(idx)

    def _update_styles(self):
        for i, btn in enumerate(self._btns):
            if i == self._active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.WHITE}; border: none;
                        border-radius: 4px; font-size: 18px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; border: none;
                        border-radius: 4px; font-size: 18px;
                    }}
                    QPushButton:hover {{ background: {Colors.WHITE}; }}
                """)