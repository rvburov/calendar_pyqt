from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QComboBox,
    QMessageBox, QMenu, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QBrush, QPainterPath

from core.styles import Colors
from core.database import CategoryManager


SIDEBAR_WIDTH = 220


# ─────────────────────────────────────────────
# ЧЕКБОКС — ОКРУГЛЁННЫЙ КВАДРАТ С ГАЛКОЙ
# ─────────────────────────────────────────────

class CalendarCheckBox(QWidget):
    """Округлённый квадрат: цвет календаря + чёрная галка если выбран."""

    toggled = pyqtSignal(bool)

    def __init__(self, color: str, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self._color = color
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool):
        self._checked = value
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if self._checked:
            # Закрашенный квадрат цвета календаря
            p.setBrush(QBrush(QColor(self._color)))
            p.setPen(QPen(QColor(self._color), 1.5))
            p.drawRoundedRect(r, 4, 4)

            # Чёрная галка
            p.setPen(QPen(QColor("#000000"), 1.8,
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            w, h = self.width(), self.height()
            path = QPainterPath()
            path.moveTo(w * 0.20, h * 0.52)
            path.lineTo(w * 0.42, h * 0.74)
            path.lineTo(w * 0.80, h * 0.28)
            p.drawPath(path)
        else:
            # Только рамка цвета календаря
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(self._color), 1.5))
            p.drawRoundedRect(r, 4, 4)

        p.end()


# ─────────────────────────────────────────────
# ДИАЛОГ СОЗДАНИЯ / РЕДАКТИРОВАНИЯ КАЛЕНДАРЯ
# ─────────────────────────────────────────────

class CalendarEditDialog(QDialog):
    def __init__(self, parent, category_manager: CategoryManager, category=None):
        super().__init__(parent)
        self.category_manager = category_manager
        self.category = category
        self.setWindowTitle("Изменить календарь" if category else "Новый календарь")
        self.setFixedWidth(300)
        self.setModal(True)
        self._build_ui()
        if category:
            self._fill(category)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Название"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название календаря")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Цвет"))
        self.color_combo = QComboBox()
        for code, name in CategoryManager.PREDEFINED_COLORS:
            px = QPixmap(16, 16)
            px.fill(QColor(code))
            self.color_combo.addItem(QIcon(px), name, code)
        layout.addWidget(self.color_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setStyleSheet(f"""
            QDialog {{ background: {Colors.BG}; }}
            QLabel {{ color: {Colors.SECONDARY_TEXT}; font-size: 13px; font-weight: 600; }}
            QLineEdit, QComboBox {{
                background: {Colors.SECONDARY_BG}; border: 1px solid {Colors.SEPARATOR};
                border-radius: 6px; padding: 6px; font-size: 13px; color: {Colors.PRIMARY_TEXT};
            }}
            QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}
            QPushButton {{
                background: {Colors.SECONDARY_BG}; color: {Colors.PRIMARY_TEXT};
                border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
        """)

    def _fill(self, cat):
        self.name_edit.setText(cat.name)
        for i in range(self.color_combo.count()):
            if self.color_combo.itemData(i) == cat.color:
                self.color_combo.setCurrentIndex(i)
                break

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название календаря")
            return
        self.result_name = name
        self.result_color = self.color_combo.currentData()
        self.accept()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

class CalendarSidebar(QWidget):
    visibility_changed = pyqtSignal()  # переключена видимость календаря
    calendars_changed  = pyqtSignal()  # добавлен/изменён/удалён календарь

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._active_ids: set = set()
        self._open = True

        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setMinimumWidth(0)
        self._build_ui()
        self.refresh()

        self._anim = QPropertyAnimation(self, b"maximumWidth")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _build_ui(self):
        self.setStyleSheet(f"background: {Colors.SECONDARY_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Заголовок
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background: {Colors.SECONDARY_BG};"
            f"border-bottom: 1px solid {Colors.SEPARATOR};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        title = QLabel("Мои календари")
        title.setStyleSheet(
            f"color: {Colors.PRIMARY_TEXT}; font-size: 13px;"
            f"font-weight: 600; background: transparent;"
        )
        hl.addWidget(title)
        layout.addWidget(header)

        # Список календарей
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {Colors.SECONDARY_BG};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 0px;
                border: none;
                background: transparent;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._list, 1)

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {Colors.SEPARATOR}; border: none;")
        layout.addWidget(sep)

        # Кнопка добавления
        add_btn = QPushButton("+ Добавить календарь")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Colors.ACCENT};
                border: none; font-size: 13px;
                text-align: left; padding: 0 16px;
            }}
            QPushButton:hover {{ background: {Colors.ACCENT_LIGHT}; }}
        """)
        add_btn.clicked.connect(self._add_calendar)
        layout.addWidget(add_btn)

    # ── Данные ──────────────────────────────

    def refresh(self):
        self._list.clear()
        cats = self.db.category_manager.get_all_categories()
        if not self._active_ids:
            self._active_ids = {cat.id for cat in cats}
        for cat in cats:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, cat.id)
            item.setSizeHint(QSize(SIDEBAR_WIDTH, 36))
            self._list.addItem(item)
            row = self._make_row(cat, cat.id in self._active_ids)
            self._list.setItemWidget(item, row)

    def get_active_ids(self) -> set:
        return self._active_ids.copy()

    # ── Строка календаря ────────────────────

    def _make_row(self, cat, checked: bool) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        checkbox = CalendarCheckBox(cat.color, checked)
        checkbox.toggled.connect(
            lambda state, cid=cat.id: self._on_toggle(cid, state)
        )
        layout.addWidget(checkbox)

        lbl = QLabel(cat.name)
        lbl.setStyleSheet(
            f"color: {Colors.PRIMARY_TEXT}; font-size: 13px; background: transparent;"
        )
        layout.addWidget(lbl, 1)
        return w

    def _on_toggle(self, cat_id: int, checked: bool):
        if checked:
            self._active_ids.add(cat_id)
        else:
            self._active_ids.discard(cat_id)
        self.visibility_changed.emit()

    # ── Контекстное меню ────────────────────

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        cat = self.db.category_manager.get_category_by_id(item.data(Qt.UserRole))
        if not cat:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {Colors.SECONDARY_BG};
                border: 1px solid {Colors.SEPARATOR};
                border-radius: 6px; padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px; font-size: 13px;
                color: {Colors.PRIMARY_TEXT}; border-radius: 4px;
            }}
            QMenu::item:selected {{ background: {Colors.ACCENT_LIGHT}; }}
            QMenu::item:disabled {{ color: {Colors.SEPARATOR}; }}
        """)
        edit_action   = menu.addAction("Изменить")
        delete_action = menu.addAction("Удалить")

        if cat.name in ["Работа", "Личное", "Важное"]:
            delete_action.setEnabled(False)

        action = menu.exec_(self._list.viewport().mapToGlobal(pos))
        if action == edit_action:
            self._edit_calendar(cat)
        elif action == delete_action:
            self._delete_calendar(cat)

    # ── CRUD ────────────────────────────────

    def _add_calendar(self):
        dlg = CalendarEditDialog(self, self.db.category_manager)
        if dlg.exec_() == QDialog.Accepted:
            cat = self.db.category_manager.add_category(dlg.result_name, dlg.result_color)
            if cat:
                self._active_ids.add(cat.id)
                self.refresh()
                self.calendars_changed.emit()
            else:
                QMessageBox.warning(self, "Ошибка", "Календарь с таким названием уже существует")

    def _edit_calendar(self, cat):
        dlg = CalendarEditDialog(self, self.db.category_manager, cat)
        if dlg.exec_() == QDialog.Accepted:
            if self.db.category_manager.update_category(cat.id, dlg.result_name, dlg.result_color):
                self.refresh()
                self.calendars_changed.emit()
            else:
                QMessageBox.warning(self, "Ошибка", "Календарь с таким названием уже существует")

    def _delete_calendar(self, cat):
        if QMessageBox.question(
            self, "Подтверждение",
            f'Удалить календарь "{cat.name}"?\nСобытия будут перенесены в "Личное"',
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._active_ids.discard(cat.id)
            self.db.category_manager.delete_category(cat.id)
            self.refresh()
            self.calendars_changed.emit()

    # ── Анимация ────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._open

    def toggle(self):
        if self._open:
            self._anim.setStartValue(SIDEBAR_WIDTH)
            self._anim.setEndValue(0)
        else:
            self._anim.setStartValue(0)
            self._anim.setEndValue(SIDEBAR_WIDTH)
        self._anim.start()
        self._open = not self._open
