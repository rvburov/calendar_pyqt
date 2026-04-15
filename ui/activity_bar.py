from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt
from core.styles import Colors


class ActivityBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(49)

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

        btn = QPushButton("☰")
        btn.setToolTip("Календарь")
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.WHITE}; border: none;
                border-radius: 4px; font-size: 18px;
            }}
        """)
        layout.addWidget(btn)
        layout.addStretch()

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: #C8C8C8; border: none;")

        h_layout.addWidget(inner)
        h_layout.addWidget(line)
