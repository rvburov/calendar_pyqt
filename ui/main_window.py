import os, sys
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from PyQt5.QtGui import QIcon

from core.database import DatabaseManager
from ui.activity_bar import ActivityBar
from modules.calendar import CalendarModule
from modules.tasks import TasksModule


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

        self.activity_bar = ActivityBar()
        self.activity_bar.section_changed.connect(self._switch_section)
        h_root.addWidget(self.activity_bar)

        self.section_stack = QStackedWidget()
        self.section_stack.addWidget(CalendarModule(self.db))
        self.section_stack.addWidget(TasksModule(self.db))
        h_root.addWidget(self.section_stack, 1)

    def _switch_section(self, idx: int):
        self.section_stack.setCurrentIndex(idx)

    def _load_icon(self):
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        icon_path = os.path.join(base, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
