import os, sys
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QFrame
from PyQt5.QtGui import QIcon

from core.database import DatabaseManager
from ui.activity_bar import ActivityBar
from ui.sidebar import CalendarSidebar
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

        # ActivityBar — узкая панель с иконками секций
        self.activity_bar = ActivityBar()
        h_root.addWidget(self.activity_bar)

        # Сайдбар с категориями (открыт по умолчанию)
        self.sidebar = CalendarSidebar(self.db)
        h_root.addWidget(self.sidebar)

        # Разделитель между сайдбаром и основным контентом
        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.VLine)
        self._separator.setFixedWidth(1)
        self._separator.setStyleSheet("background: #C8C8C8; border: none;")
        h_root.addWidget(self._separator)

        # Основной модуль календаря
        self.calendar_module = CalendarModule(self.db)
        h_root.addWidget(self.calendar_module, 1)

        # Сигналы ActivityBar
        self.activity_bar.section_toggled.connect(self._on_section_toggled)

        # Сигналы сайдбара
        self.sidebar.visibility_changed.connect(self._on_visibility_changed)
        self.sidebar.calendars_changed.connect(self._on_calendars_changed)

        # Инициализируем фильтр после создания обоих виджетов
        self.calendar_module.set_active_ids(self.sidebar.get_active_ids())

    # ── Обработчики ─────────────────────────────────────────

    def _on_section_toggled(self, section_id: str, is_open: bool):
        """ActivityBar: пользователь нажал кнопку секции."""
        if section_id == "calendars":
            # Синхронизируем состояние анимации сайдбара с кнопкой
            if is_open != self.sidebar.is_open:
                self.sidebar.toggle()

    def _on_visibility_changed(self):
        self.calendar_module.set_active_ids(self.sidebar.get_active_ids())

    def _on_calendars_changed(self):
        self.sidebar.refresh()
        self.calendar_module.set_active_ids(self.sidebar.get_active_ids())

    def _load_icon(self):
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        icon_path = os.path.join(base, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
