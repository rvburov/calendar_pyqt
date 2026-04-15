import os, sys
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PyQt5.QtGui import QIcon

from core.database import DatabaseManager
from ui.activity_bar import ActivityBar
from modules.calendar import CalendarModule


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.setWindowTitle("Планировщик")
        self.setMinimumSize(1050, 780)
        self._build_ui()
        self._load_icon()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        h_root = QHBoxLayout(central)
        h_root.setContentsMargins(0, 0, 0, 0)
        h_root.setSpacing(0)

        h_root.addWidget(ActivityBar())
        h_root.addWidget(CalendarModule(self.db), 1)

    def _load_icon(self):
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        icon_path = os.path.join(base, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
