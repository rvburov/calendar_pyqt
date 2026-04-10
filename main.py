import sys
import sqlite3
import os
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QStackedWidget, QScrollArea,
    QDialog, QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit,
    QFrame, QSizePolicy, QMessageBox, QSpacerItem, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import (
    Qt, QDate, QTime, QDateTime, QTimer, QPoint, QRect, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPalette, QFontMetrics,
    QLinearGradient, QPainterPath, QPixmap, QIcon
)
                     

# ─────────────────────────────────────────────
# ЦВЕТА
# ─────────────────────────────────────────────


class Colors:
    BG            = "#FFFFFF"
    SECONDARY_BG  = "#F2F2F7"
    SEPARATOR     = "#E5E5EA"
    PRIMARY_TEXT  = "#1C1C1E"
    SECONDARY_TEXT= "#8E8E93"
    ACCENT        = "#007AFF"
    ACCENT_LIGHT  = "#E5F0FF"
    TODAY_TEXT    = "#FFFFFF"
    WEEKEND       = "#8E8E93"
    RED           = "#FF3B30"
    GREEN         = "#34C759"
    HOVER         = "#E5E5EA"
    WHITE         = "#FFFFFF"
    ACTIVITY_BAR  = "#EBEBEB"


# ─────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────


class Category:
    def __init__(self, name: str, color: str, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.color = color
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "color": self.color}

class CategoryManager:
    """Управление пользовательскими категориями"""
    
    # Предустановленные цвета (10 цветов)
    PREDEFINED_COLORS = [
        ("#007AFF", "Синий"),
        ("#34C759", "Зеленый"),
        ("#FF3B30", "Красный"),
        ("#FF9500", "Оранжевый"),
        ("#FF2D55", "Розовый"),
        ("#AF52DE", "Фиолетовый"),
        ("#FFCC00", "Желтый"),
        ("#5E5CE6", "Индиго"),
        ("#64D2FF", "Голубой"),
        ("#FF6B6B", "Коралловый")
    ]
    
    def __init__(self, db_conn):
        self.conn = db_conn
        self._create_table()
        self._ensure_default_categories()
    
    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                color       TEXT NOT NULL
            )
        """)
        self.conn.commit()
    
    def _ensure_default_categories(self):
        """Добавляет стандартные категории, если их нет"""
        default_cats = [
            ("Работа", "#007AFF"),
            ("Личное", "#34C759"),
            ("Важное", "#FF3B30")
        ]
        
        for name, color in default_cats:
            cur = self.conn.execute("SELECT id FROM categories WHERE name = ?", (name,))
            if not cur.fetchone():
                self.add_category(name, color)
    
    def add_category(self, name: str, color: str) -> Optional[Category]:
        """Добавляет новую категорию"""
        try:
            cur = self.conn.execute(
                "INSERT INTO categories (name, color) VALUES (?, ?)",
                (name, color)
            )
            self.conn.commit()
            return Category(name, color, cur.lastrowid)
        except sqlite3.IntegrityError:
            return None
    
    def update_category(self, cat_id: int, name: str, color: str) -> bool:
        """Обновляет категорию"""
        try:
            self.conn.execute(
                "UPDATE categories SET name = ?, color = ? WHERE id = ?",
                (name, color, cat_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def delete_category(self, cat_id: int):
        """Удаляет категорию (события переназначаются в 'Личное')"""
        # Находим ID категории "Личное"
        personal = self.conn.execute(
            "SELECT id FROM categories WHERE name = 'Личное'"
        ).fetchone()
        
        if personal:
            # Переназначаем события
            self.conn.execute(
                "UPDATE events SET category = ? WHERE category = ?",
                (personal[0], cat_id)
            )
        
        # Удаляем категорию
        self.conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        self.conn.commit()
    
    def get_all_categories(self) -> List[Category]:
        """Возвращает все категории"""
        cur = self.conn.execute("SELECT id, name, color FROM categories ORDER BY name")
        return [Category(name, color, id) for id, name, color in cur.fetchall()]
    
    def get_category_by_id(self, cat_id: int) -> Optional[Category]:
        cur = self.conn.execute(
            "SELECT id, name, color FROM categories WHERE id = ?",
            (cat_id,)
        )
        row = cur.fetchone()
        if row:
            return Category(row[1], row[2], row[0])
        return None
    
    def get_category_by_name(self, name: str) -> Optional[Category]:
        cur = self.conn.execute(
            "SELECT id, name, color FROM categories WHERE name = ?",
            (name,)
        )
        row = cur.fetchone()
        if row:
            return Category(row[1], row[2], row[0])
        return None
    
class CategoryDialog(QDialog):
    """Диалог для управления категориями"""
    
    def __init__(self, parent, category_manager: CategoryManager):
        super().__init__(parent)
        self.category_manager = category_manager
        self.setWindowTitle("Управление категориями")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        self._build_ui()
        self._load_categories()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Список категорий
        self.category_list = QListWidget()
        self.category_list.setStyleSheet(f"""
            QListWidget {{
                background: {Colors.SECONDARY_BG};
                border: 1px solid {Colors.SEPARATOR};
                border-radius: 8px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background: {Colors.ACCENT_LIGHT};
            }}
        """)
        self.category_list.itemClicked.connect(self._on_category_selected)
        layout.addWidget(self.category_list)
        
        # Форма редактирования
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        form_layout.setSpacing(10)
        
        form_layout.addWidget(QLabel("Название:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название категории")
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("Цвет:"), 1, 0)
        self.color_combo = QComboBox()
        for color_code, color_name in CategoryManager.PREDEFINED_COLORS:
            # Создаем иконку с цветом
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color_code))
            icon = QIcon(pixmap)
            self.color_combo.addItem(icon, color_name, color_code)
        form_layout.addWidget(self.color_combo, 1, 1)
        
        layout.addWidget(form_widget)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.setFixedHeight(30)
        self.add_btn.setFixedWidth(90)
        self.add_btn.clicked.connect(self._add_category)
        btn_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("Изменить")
        self.update_btn.setFixedHeight(30)
        self.update_btn.setFixedWidth(90)
        self.update_btn.clicked.connect(self._update_category)
        btn_layout.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setFixedHeight(30)
        self.delete_btn.setFixedWidth(90)
        self.delete_btn.clicked.connect(self._delete_category)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(30)
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self._apply_styles()
    
    def _apply_styles(self):
        style = f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG};
                color: {Colors.PRIMARY_TEXT};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {Colors.SEPARATOR};
            }}
            QLineEdit, QComboBox {{
                background: {Colors.SECONDARY_BG};
                border: 1px solid {Colors.SEPARATOR};
                border-radius: 6px;
                padding: 6px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
        """
        self.setStyleSheet(style)
    
    def _load_categories(self):
        self.category_list.clear()
        categories = self.category_manager.get_all_categories()
        for cat in categories:
            item = QListWidgetItem(f"{cat.name}")
            item.setData(Qt.UserRole, cat.id)
            # Цветной индикатор
            item.setForeground(QColor(cat.color))
            self.category_list.addItem(item)
    
    def _on_category_selected(self, item):
        self.update_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
        cat_id = item.data(Qt.UserRole)
        category = self.category_manager.get_category_by_id(cat_id)
        if category:
            self.name_edit.setText(category.name)
            # Устанавливаем цвет в комбобоксе
            for i in range(self.color_combo.count()):
                if self.color_combo.itemData(i) == category.color:
                    self.color_combo.setCurrentIndex(i)
                    break
    
    def _add_category(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название категории")
            return
        
        color = self.color_combo.currentData()
        
        if self.category_manager.add_category(name, color):
            self._load_categories()
            self.name_edit.clear()
            QMessageBox.information(self, "Успех", f"Категория '{name}' добавлена")
        else:
            QMessageBox.warning(self, "Ошибка", "Категория с таким названием уже существует")
    
    def _update_category(self):
        current_item = self.category_list.currentItem()
        if not current_item:
            return
        
        cat_id = current_item.data(Qt.UserRole)
        new_name = self.name_edit.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Введите название категории")
            return
        
        new_color = self.color_combo.currentData()
        
        if self.category_manager.update_category(cat_id, new_name, new_color):
            self._load_categories()
            QMessageBox.information(self, "Успех", f"Категория обновлена")
        else:
            QMessageBox.warning(self, "Ошибка", "Категория с таким названием уже существует")
    
    def _delete_category(self):
        current_item = self.category_list.currentItem()
        if not current_item:
            return
        
        cat_id = current_item.data(Qt.UserRole)
        category = self.category_manager.get_category_by_id(cat_id)
        
        # Запрещаем удаление стандартных категорий
        if category.name in ["Работа", "Личное", "Важное"]:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить стандартную категорию")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f'Удалить категорию "{category.name}"?\nСобытия будут переназначены в "Личное"',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.category_manager.delete_category(cat_id)
            self._load_categories()
            self.name_edit.clear()
            self.update_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            QMessageBox.information(self, "Успех", "Категория удалена")

# ─────────────────────────────────────────────
# EVENT DATACLASS
# ─────────────────────────────────────────────

@dataclass
class Event:
    title: str
    start_dt: datetime
    end_dt: datetime
    category: str = "Личное"
    description: str = ""
    id: Optional[int] = None
    category_id: Optional[int] = None
    _db: Optional[object] = None  # Добавьте это поле

    @property
    def color(self) -> str:
        # Если есть доступ к БД через _db, получаем цвет оттуда
        if self._db and hasattr(self._db, 'category_manager'):
            category_obj = self._db.category_manager.get_category_by_name(self.category)
            if category_obj:
                return category_obj.color
        # Заглушка на случай отсутствия БД
        colors_map = {
            "Работа": "#007AFF",
            "Личное": "#34C759",
            "Важное": "#FF3B30"
        }
        return colors_map.get(self.category, Colors.ACCENT)

# ─────────────────────────────────────────────
# DATABASE MANAGER
# ─────────────────────────────────────────────

class DatabaseManager:
    def __init__(self):
        # Определяем путь для хранения базы
        if getattr(sys, 'frozen', False):
            # Запущено как .exe - сохраняем в AppData
            app_data = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'MyCalendar')
        else:
            # Запущено как .py - сохраняем рядом со скриптом
            app_data = os.path.dirname(os.path.abspath(__file__))
        
        os.makedirs(app_data, exist_ok=True)
        db_path = os.path.join(app_data, "calendar.db")
        
        self.conn = sqlite3.connect(db_path)
        self._create_table()
        self.category_manager = CategoryManager(self.conn)

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                start_dt    TEXT NOT NULL,
                end_dt      TEXT NOT NULL,
                category    INTEGER DEFAULT 1
            )
        """)
        self.conn.commit()

    def _row_to_event(self, row) -> Event:
        category_id = row[5]
        category = self.category_manager.get_category_by_id(category_id)
        category_name = category.name if category else "Личное"
        
        event = Event(
            id=row[0],
            title=row[1],
            description=row[2],
            start_dt=datetime.fromisoformat(row[3]),
            end_dt=datetime.fromisoformat(row[4]),
            category=category_name,
            category_id=category_id
        )
        event._db = self  # Добавьте эту строку - передаем ссылку на БД
        return event

    def add_event(self, event: Event) -> Event:
        category_obj = self.category_manager.get_category_by_name(event.category)
        category_id = category_obj.id if category_obj else 1
        
        cur = self.conn.execute(
            "INSERT INTO events (title, description, start_dt, end_dt, category) VALUES (?,?,?,?,?)",
            (event.title, event.description,
             event.start_dt.isoformat(), event.end_dt.isoformat(), category_id)
        )
        self.conn.commit()
        event.id = cur.lastrowid
        event.category_id = category_id
        event._db = self  # Добавьте эту строку
        return event

    def update_event(self, event: Event):
        category_obj = self.category_manager.get_category_by_name(event.category)
        category_id = category_obj.id if category_obj else 1
        
        self.conn.execute(
            "UPDATE events SET title=?, description=?, start_dt=?, end_dt=?, category=? WHERE id=?",
            (event.title, event.description,
             event.start_dt.isoformat(), event.end_dt.isoformat(), category_id, event.id)
        )
        self.conn.commit()
        event._db = self  # Добавьте эту строку

    def delete_event(self, event_id: int):
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.conn.commit()

    def get_events_by_date_range(self, start: datetime, end: datetime) -> List[Event]:
        cur = self.conn.execute(
            "SELECT * FROM events WHERE start_dt < ? AND end_dt > ? ORDER BY start_dt",
            (end.isoformat(), start.isoformat())
        )
        return [self._row_to_event(r) for r in cur.fetchall()]

    def get_all_events(self) -> List[Event]:
        cur = self.conn.execute("SELECT * FROM events ORDER BY start_dt")
        return [self._row_to_event(r) for r in cur.fetchall()]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

# ─────────────────────────────────────────────
# СТИЛИ
# ─────────────────────────────────────────────

APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {Colors.BG};
    color: {Colors.PRIMARY_TEXT};
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: {Colors.SECONDARY_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {Colors.SEPARATOR};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {Colors.SECONDARY_BG};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.SEPARATOR};
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""

# ─────────────────────────────────────────────
# EVENT DIALOG
# ─────────────────────────────────────────────

class EventDialog(QDialog):
    def __init__(self, parent=None, db=None, event: Optional[Event] = None,
                 preset_date: Optional[date] = None, preset_time: Optional[QTime] = None):
        super().__init__(parent)
        self.db = db  # Сохраняем ссылку на БД
        self.event = event
        self.setWindowTitle("Изменить событие" if event else "Новое событие")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build_ui(preset_date, preset_time)
        self._apply_style()
        if event:
            self._fill_from_event(event)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {Colors.BG};
                border-radius: 12px;
            }}
            QLabel {{
                color: {Colors.SECONDARY_TEXT};
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {{
                background: {Colors.SECONDARY_BG};
                border: 1.5px solid {Colors.SEPARATOR};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                color: {Colors.PRIMARY_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QDateEdit:focus, QTimeEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
            QPushButton#save_btn {{
                background: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#save_btn:hover {{
                background: #0063CC;
            }}
            QPushButton#cancel_btn {{
                background: {Colors.SECONDARY_BG};
                color: {Colors.PRIMARY_TEXT};
                border: none;
                border-radius: 8px;
                padding: 0px;
                font-size: 13px;
            }}
            QPushButton#cancel_btn:hover {{
                background: {Colors.SEPARATOR};
            }}
            QPushButton#delete_btn {{
                background: {Colors.RED};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0px;
                font-size: 13px;
            }}
        """)

    def _build_ui(self, preset_date, preset_time):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        lbl_title = QLabel("Название")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Добавить название")
        layout.addWidget(lbl_title)
        layout.addWidget(self.title_edit)

        # Date + times row
        dt_layout = QHBoxLayout()
        dt_layout.setSpacing(10)

        date_col = QVBoxLayout()
        date_col.addWidget(QLabel("Дата"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(
            QDate(preset_date.year, preset_date.month, preset_date.day)
            if preset_date else QDate.currentDate()
        )
        date_col.addWidget(self.date_edit)

        start_col = QVBoxLayout()
        start_col.addWidget(QLabel("Начало"))
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        if preset_time:
            self.start_time.setTime(preset_time)
        else:
            self.start_time.setTime(QTime(9, 0))
        start_col.addWidget(self.start_time)

        end_col = QVBoxLayout()
        end_col.addWidget(QLabel("Конец"))
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        if preset_time:
            end = preset_time.addSecs(3600)
            self.end_time.setTime(end)
        else:
            self.end_time.setTime(QTime(10, 0))
        end_col.addWidget(self.end_time)

        dt_layout.addLayout(date_col, 2)
        dt_layout.addLayout(start_col, 1)
        dt_layout.addLayout(end_col, 1)
        layout.addLayout(dt_layout)

        # Category
        layout.addWidget(QLabel("Категория"))
        self.category_combo = QComboBox()
        self._load_categories()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        layout.addWidget(self.category_combo)

        # Description
        layout.addWidget(QLabel("Описание"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Добавить описание (необязательно)")
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        if self.event:
            del_btn = QPushButton("Удалить")
            del_btn.setObjectName("delete_btn")
            del_btn.setFixedHeight(30)
            del_btn.setFixedWidth(120)
            del_btn.clicked.connect(self._delete)
            btn_layout.addWidget(del_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedHeight(30)
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("save_btn")
        save_btn.setFixedHeight(30)
        save_btn.setFixedWidth(120)
        save_btn.clicked.connect(self._save)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _fill_from_event(self, event: Event):
        self.title_edit.setText(event.title)
        self.date_edit.setDate(QDate(event.start_dt.year, event.start_dt.month, event.start_dt.day))
        self.start_time.setTime(QTime(event.start_dt.hour, event.start_dt.minute))
        self.end_time.setTime(QTime(event.end_dt.hour, event.end_dt.minute))
        self.desc_edit.setPlainText(event.description)
        
        # Находим категорию в комбобоксе по имени
        for i in range(self.category_combo.count()):
            if self.category_combo.itemText(i) == event.category:
                self.category_combo.setCurrentIndex(i)
                break
        
        # Обновляем цветовые индикаторы в UI
        self._update_category_color(event.category)

    def _update_category_color(self, category_name: str):
        """Обновляет цветовые индикаторы для выбранной категории"""
        if self.db and hasattr(self.db, 'category_manager'):
            category = self.db.category_manager.get_category_by_name(category_name)
            if category:
                # Меняем цвет рамки или фона для визуального отображения
                color = QColor(category.color)
                self.category_combo.setStyleSheet(f"""
                    QComboBox {{
                        background: {Colors.SECONDARY_BG};
                        border: 1.5px solid {color.name()};
                        border-radius: 8px;
                        padding: 6px 10px;
                    }}
                """)
            else:
                self.category_combo.setStyleSheet("")

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Ошибка", "Введите название события")
            return
        d = self.date_edit.date()
        st = self.start_time.time()
        et = self.end_time.time()
        if et <= st:
            QMessageBox.warning(self, "Ошибка", "Время конца должно быть позже начала")
            return
        
        self.result_event = Event(
            id=self.event.id if self.event else None,
            title=title,
            description=self.desc_edit.toPlainText(),
            start_dt=datetime(d.year(), d.month(), d.day(), st.hour(), st.minute()),
            end_dt=datetime(d.year(), d.month(), d.day(), et.hour(), et.minute()),
            category=self.category_combo.currentText(),
        )
        self.result_event._db = self.db  # Добавьте эту строку
        self.accept()

    def _delete(self):
        if QMessageBox.question(self, "Удалить", f'Удалить событие "{self.event.title}"?',
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.result_event = None
            self.done(2)  # код 2 = удаление

    def _load_categories(self):
        """Загружает категории из базы данных"""
        self.category_combo.clear()
        
        # ИСПРАВЬТЕ ЭТУ СТРОКУ:
        categories = []
        if self.db and hasattr(self.db, 'category_manager'):
            categories = self.db.category_manager.get_all_categories()
        
        # Если нет доступа к db, используем стандартные
        if not categories:
            categories = [
                Category("Работа", "#007AFF"),
                Category("Личное", "#34C759"),
                Category("Важное", "#FF3B30")
            ]
        
        for cat in categories:
            # Создаем иконку с цветом
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(cat.color))
            icon = QIcon(pixmap)
            self.category_combo.addItem(icon, cat.name, cat.name)

    def _on_category_changed(self, category_name: str):
        """Когда меняется категория, обновляем цвет"""
        self._update_category_color(category_name)

# ─────────────────────────────────────────────
# MONTH VIEW
# ─────────────────────────────────────────────

class MonthView(QWidget):
    day_clicked = pyqtSignal(date)
    event_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Day-of-week headers
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet(f"background: {Colors.SECONDARY_BG}; border-bottom: 1px solid {Colors.SEPARATOR};")
        h_lay = QGridLayout(header)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(0)
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, d in enumerate(days):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignCenter)
            color = Colors.WEEKEND if i >= 5 else Colors.SECONDARY_TEXT
            lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
            h_lay.addWidget(lbl, 0, i)
        layout.addWidget(header)

        # Grid
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet(f"background: {Colors.BG};")
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(0)
        layout.addWidget(self.grid_widget, 1)

        self.cells = []
        for row in range(6):
            row_cells = []
            for col in range(7):
                cell = DayCell(self.db)
                cell.double_clicked.connect(self._on_cell_double_clicked)
                cell.event_changed.connect(self.event_changed)
                self.grid.addWidget(cell, row, col)
                row_cells.append(cell)
            self.cells.append(row_cells)

    def _on_cell_double_clicked(self, d: date):
        # ИСПРАВЬТЕ - добавьте db=self.db
        dlg = EventDialog(self, db=self.db, preset_date=d)
        if dlg.exec_() == QDialog.Accepted:
            self.db.add_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def refresh(self):
        today = date.today()
        first = self.current_date.replace(day=1)
        start_weekday = first.weekday()  # 0=Mon
        # первая ячейка сетки
        grid_start = first - timedelta(days=start_weekday)

        events = self.db.get_events_by_date_range(
            datetime.combine(grid_start, datetime.min.time()),
            datetime.combine(grid_start + timedelta(days=42), datetime.max.time())
        )

        for row in range(6):
            for col in range(7):
                idx = row * 7 + col
                cell_date = grid_start + timedelta(days=idx)
                is_current_month = cell_date.month == self.current_date.month
                is_today = cell_date == today
                is_weekend = col >= 5

                day_events = [e for e in events if e.start_dt.date() == cell_date]
                self.cells[row][col].set_data(cell_date, day_events,
                                              is_current_month, is_today, is_weekend)

    def go_prev(self):
        m = self.current_date.month - 1
        y = self.current_date.year
        if m == 0:
            m, y = 12, y - 1
        self.current_date = self.current_date.replace(year=y, month=m, day=1)
        self.refresh()

    def go_next(self):
        m = self.current_date.month + 1
        y = self.current_date.year
        if m == 13:
            m, y = 1, y + 1
        self.current_date = self.current_date.replace(year=y, month=m, day=1)
        self.refresh()

    def go_today(self):
        self.current_date = date.today()
        self.refresh()

    def header_text(self) -> str:
        months = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                  "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
        return f"{months[self.current_date.month-1]} {self.current_date.year}"

# ─────────────────────────────────────────────
# DAY CELL (used by MonthView)
# ─────────────────────────────────────────────

class DayCell(QWidget):
    double_clicked = pyqtSignal(date)
    event_changed  = pyqtSignal()

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.cell_date: Optional[date] = None
        self.events: List[Event] = []
        self.is_current_month = True
        self.is_today = False
        self.is_weekend = False
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._hovered = False

    def set_data(self, cell_date: date, events: List[Event],
                 is_current_month: bool, is_today: bool, is_weekend: bool):
        self.cell_date = cell_date
        self.events = events
        self.is_current_month = is_current_month
        self.is_today = is_today
        self.is_weekend = is_weekend
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.cell_date:
            self.double_clicked.emit(self.cell_date)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton and self.cell_date:
            # find clicked event
            pass

    def paintEvent(self, e):
        if not self.cell_date:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        if self._hovered and self.is_current_month:
            p.fillRect(0, 0, w, h, QColor(Colors.ACCENT_LIGHT))
        elif not self.is_current_month:
            p.fillRect(0, 0, w, h, QColor("#FAFAFA"))
        else:
            p.fillRect(0, 0, w, h, QColor(Colors.BG))

        # Border
        p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
        p.drawRect(0, 0, w - 1, h - 1)

        # Day number
        day_str = str(self.cell_date.day)
        font = QFont("Helvetica Neue", 10, QFont.DemiBold if self.is_today else QFont.Normal)
        p.setFont(font)

        circle_size = 24
        circle_x = w - circle_size - 6
        circle_y = 6

        if self.is_today:
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(circle_x, circle_y, circle_size, circle_size)
            p.setPen(QColor(Colors.TODAY_TEXT))
        else:
            p.setPen(QColor(Colors.WEEKEND if self.is_weekend else
                            (Colors.SECONDARY_TEXT if not self.is_current_month else Colors.PRIMARY_TEXT)))

        p.drawText(circle_x, circle_y, circle_size, circle_size, Qt.AlignCenter, day_str)

        # Events
        max_events = 3
        tag_h = 18
        tag_y = circle_y + circle_size + 4
        for i, ev in enumerate(self.events[:max_events]):
            if tag_y + tag_h > h - 4:
                break
            
            color = QColor(ev.color)
            
            # Фон с прозрачностью
            light = QColor(color)
            light.setAlpha(40)
            p.setBrush(QBrush(light))
            p.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(6, tag_y, w - 12, tag_h, 4, 4)
            p.drawPath(path)
            
            # Левая цветная полоска
            p.setBrush(QBrush(color))
            p.drawRoundedRect(6, tag_y, 4, tag_h, 2, 2)
            
            # Текст
            p.setPen(color.darker(140))
            f2 = QFont("Helvetica Neue", 10)
            p.setFont(f2)
            time_str = ev.start_dt.strftime("%H:%M")
            full_text = f"{time_str} {ev.title}"
            
            font_metrics = QFontMetrics(f2)
            available_width = w - 28
            elided_text = font_metrics.elidedText(full_text, Qt.ElideRight, available_width)
            
            p.drawText(14, tag_y, w - 20, tag_h, Qt.AlignVCenter | Qt.AlignLeft, elided_text)
            tag_y += tag_h + 2

        # "+N more"
        remaining = len(self.events) - max_events
        if remaining > 0:
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            f3 = QFont("Helvetica Neue", 10)
            p.setFont(f3)
            p.drawText(6, tag_y, w - 12, 16, Qt.AlignVCenter | Qt.AlignLeft, f"+{remaining} ещё")

        p.end()

    def resizeEvent(self, event):
        """При изменении размера ячейки перерисовываем"""
        self.update()
        super().resizeEvent(event)

# ─────────────────────────────────────────────
# DAY VIEW
# ─────────────────────────────────────────────

class DayView(QWidget):
    event_changed = pyqtSignal()

    HOUR_H = 60  # px per hour

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._build_ui()
        self.refresh()
        # Timer to update "now" line
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._canvas.update)
        self._timer.start(60000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._canvas = DayCanvas(self.db)
        self._canvas.double_clicked_time.connect(self._on_double_click)
        self._canvas.event_clicked.connect(self._on_event_click)
        scroll.setWidget(self._canvas)
        layout.addWidget(scroll)

        # scroll to current hour
        QTimer.singleShot(100, lambda: scroll.verticalScrollBar().setValue(
            max(0, (datetime.now().hour - 2) * self.HOUR_H)
        ))

    def _on_double_click(self, t: QTime):
        # ИСПРАВЬТЕ - добавьте db=self.db
        dlg = EventDialog(self, db=self.db, preset_date=self.current_date, preset_time=t)
        if dlg.exec_() == QDialog.Accepted:
            self.db.add_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def _on_event_click(self, event: Event):
        dlg = EventDialog(self, db=self.db, event=event)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.db.update_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()
        elif result == 2:
            self.db.delete_event(event.id)
            self.refresh()
            self.event_changed.emit()

    def refresh(self):
        start = datetime.combine(self.current_date, datetime.min.time())
        end   = datetime.combine(self.current_date, datetime.max.time())
        events = self.db.get_events_by_date_range(start, end)
        self._canvas.set_data(self.current_date, events)

    def go_prev(self):
        self.current_date -= timedelta(days=1)
        self.refresh()

    def go_next(self):
        self.current_date += timedelta(days=1)
        self.refresh()

    def go_today(self):
        self.current_date = date.today()
        self.refresh()

    def header_text(self) -> str:
        days_ru = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        months  = ["января","февраля","марта","апреля","мая","июня",
                   "июля","августа","сентября","октября","ноября","декабря"]
        wd = self.current_date.weekday()
        return f"{days_ru[wd]}, {self.current_date.day} {months[self.current_date.month-1]} {self.current_date.year}"

class DayCanvas(QWidget):
    double_clicked_time = pyqtSignal(QTime)
    event_clicked       = pyqtSignal(Event)

    HOUR_H   = 60
    TIME_W   = 56
    PAD_R    = 12

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self.events: List[Event] = []
        self.setMinimumHeight(24 * self.HOUR_H)
        self._event_rects: List[tuple] = []  # (QRect, Event)

    def set_data(self, d: date, events: List[Event]):
        self.current_date = d
        self.events = events
        self._event_rects = []
        self.update()

    def mousePressEvent(self, e):
        """Одиночный клик - можно оставить пустым или добавить выделение"""
        pass

    def mouseDoubleClickEvent(self, e):
        """Двойной клик - открыть событие или создать новое"""
        # Проверяем, попали ли в существующее событие
        for rect, ev in self._event_rects:
            if rect.contains(e.pos()):
                self.event_clicked.emit(ev)  # открыть существующее событие
                return
        
        # Пустое место - создаём новое событие
        y = e.pos().y()
        hour = y // self.HOUR_H
        minute = (y % self.HOUR_H) * 60 // self.HOUR_H
        minute = (minute // 15) * 15  # округляем до 15 минут
        self.double_clicked_time.emit(QTime(min(hour, 23), minute))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        p.fillRect(0, 0, w, self.height(), QColor(Colors.BG))

        # Hour rows
        for hour in range(24):
            y = hour * self.HOUR_H
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            f = QFont("Helvetica Neue", 10)
            p.setFont(f)
            p.drawText(0, y, self.TIME_W - 8, self.HOUR_H, Qt.AlignRight | Qt.AlignTop,
                    f"{hour:02d}:00")
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(self.TIME_W, y, w - self.PAD_R, y)
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5, Qt.DashLine))
            p.drawLine(self.TIME_W, y + self.HOUR_H // 2, w - self.PAD_R, y + self.HOUR_H // 2)

        # Events - теперь как в WeekView
        self._event_rects = []
        
        # Группируем overlapping события
        overlapping_groups = self._group_overlapping_events(self.events)
        
        x = self.TIME_W + 3
        cw = w - self.TIME_W - self.PAD_R - 6
        
        for group in overlapping_groups:
            group_size = len(group)
            if group_size == 0:
                continue
                
            # Делим ширину между событиями в группе
            segment_width = cw // group_size
            
            for idx, ev in enumerate(group):
                sh, sm = ev.start_dt.hour, ev.start_dt.minute
                eh, em = ev.end_dt.hour, ev.end_dt.minute
                y1 = sh * self.HOUR_H + sm * self.HOUR_H // 60
                y2 = eh * self.HOUR_H + em * self.HOUR_H // 60
                if y2 <= y1:
                    y2 = y1 + self.HOUR_H // 2

                # Сдвигаем каждый блок в группе
                x_offset = x + (idx * segment_width)
                rect = QRect(x_offset, y1 + 1, segment_width - 2, y2 - y1 - 2)

                color = QColor(ev.color)
                
                # Отрисовка
                light = QColor(color)
                light.setAlpha(25)
                p.setBrush(QBrush(light))
                p.setPen(Qt.NoPen)
                path = QPainterPath()
                path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 5, 5)
                p.drawPath(path)

                p.setBrush(QBrush(color))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(rect.x(), rect.y(), 4, rect.height(), 2, 2)

                p.setPen(color.darker(140))
                f2 = QFont("Helvetica Neue", 10, QFont.Normal)
                p.setFont(f2)
                tr = rect.adjusted(8, 3, -3, -3)
                time_s = f"{ev.start_dt.strftime('%H:%M')}"

                font_metrics = QFontMetrics(f2)

                if rect.height() > 28:
                    if group_size > 2:
                        short_title = ev.title[:10] + "..." if len(ev.title) > 10 else ev.title
                        p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                                f"{short_title}\n{time_s}")
                    else:
                        available_width = rect.width() - 11
                        elided_title = font_metrics.elidedText(ev.title, Qt.ElideRight, available_width)
                        p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                                f"{elided_title}\n{time_s}")
                else:
                    if group_size > 2:
                        short_title = ev.title[:6] + "..." if len(ev.title) > 6 else ev.title
                        p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, f"{short_title} {time_s}")
                    else:
                        available_width = rect.width() - 11
                        full_text = f"{ev.title} {time_s}"
                        elided_text = font_metrics.elidedText(full_text, Qt.ElideRight, available_width)
                        p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, elided_text)
                
                self._event_rects.append((rect, ev))

        # Current time line
        if self.current_date == date.today():
            now = datetime.now()
            now_y = now.hour * self.HOUR_H + now.minute * self.HOUR_H // 60
            p.setPen(QPen(QColor(Colors.RED), 2))
            p.drawLine(self.TIME_W - 4, now_y, w - self.PAD_R, now_y)
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self.TIME_W - 8, now_y - 4, 8, 8)

        p.end()

    def resizeEvent(self, event):
        """При изменении размера окна перерисовываем"""
        self.update()
        super().resizeEvent(event)

    def _group_overlapping_events(self, events):
        """Группирует события, которые пересекаются по времени"""
        if not events:
            return []
        
        # Сортируем события по времени начала
        sorted_events = sorted(events, key=lambda e: (e.start_dt, e.end_dt))
        groups = []
        current_group = [sorted_events[0]]
        
        for ev in sorted_events[1:]:
            # Проверяем пересекается ли с любым событием в текущей группе
            overlaps = False
            for group_ev in current_group:
                if not (ev.start_dt >= group_ev.end_dt or ev.end_dt <= group_ev.start_dt):
                    overlaps = True
                    break
            
            if overlaps:
                current_group.append(ev)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [ev]
        
        if current_group:
            groups.append(current_group)
        
        return groups

# ─────────────────────────────────────────────
# WEEK VIEW  (Пн–Пт, рабочая неделя)
# ─────────────────────────────────────────────

class WeekView(QWidget):
    event_changed = pyqtSignal()

    HOUR_H  = 56        # px per hour
    TIME_W  = 52        # left time-label column
    DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт"]

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._build_ui()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._canvas.update)
        self._timer.start(60000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Day-header row (fixed, above scroll)
        self._header_bar = WeekHeaderBar(self.HOUR_H, self.TIME_W, self.DAY_NAMES)
        layout.addWidget(self._header_bar)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        # Убираем горизонтальный скроллбар
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._canvas = WeekCanvas(self.db, self.HOUR_H, self.TIME_W)
        self._canvas.event_clicked.connect(self._on_event_click)
        self._canvas.slot_double_clicked.connect(self._on_slot_dblclick)

        # Синхронизируем ширину заголовка с шириной канваса
        self._canvas.width_changed.connect(self._header_bar.set_canvas_width)

        scroll.setWidget(self._canvas)
        layout.addWidget(scroll, 1)

        QTimer.singleShot(120, lambda: scroll.verticalScrollBar().setValue(
            max(0, 7 * self.HOUR_H - 20)
        ))

    def _on_event_click(self, ev: 'Event'):
        dlg = EventDialog(self, db=self.db, event=ev)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.db.update_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()
        elif result == 2:
            self.db.delete_event(ev.id)
            self.refresh()
            self.event_changed.emit()

    def _on_slot_dblclick(self, d: date, t: QTime):
        dlg = EventDialog(self, db=self.db, preset_date=d, preset_time=t)
        if dlg.exec_() == QDialog.Accepted:
            self.db.add_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def refresh(self):
        monday = self.current_date - timedelta(days=self.current_date.weekday())
        days = [monday + timedelta(days=i) for i in range(5)]  # Mon-Fri
        start_dt = datetime.combine(days[0], datetime.min.time())
        end_dt   = datetime.combine(days[-1], datetime.max.time())
        events   = self.db.get_events_by_date_range(start_dt, end_dt)
        self._header_bar.set_days(days)
        self._canvas.set_data(days, events)

    def go_prev(self):
        self.current_date -= timedelta(weeks=1)
        self.refresh()

    def go_next(self):
        self.current_date += timedelta(weeks=1)
        self.refresh()

    def go_today(self):
        self.current_date = date.today()
        self.refresh()

    def header_text(self) -> str:
        monday = self.current_date - timedelta(days=self.current_date.weekday())
        friday = monday + timedelta(days=4)
        months = ["января","февраля","марта","апреля","мая","июня",
                  "июля","августа","сентября","октября","ноября","декабря"]
        if monday.month == friday.month:
            return f"{monday.day}–{friday.day} {months[friday.month-1]} {friday.year}"
        return f"{monday.day} {months[monday.month-1]} – {friday.day} {months[friday.month-1]} {friday.year}"

class WeekHeaderBar(QWidget):
    """Фиксированная шапка с датами дней недели"""
    def __init__(self, hour_h, time_w, day_names):
        super().__init__()
        self.hour_h  = hour_h
        self.time_w  = time_w
        self.day_names = day_names
        self.days: List[date] = []
        self._canvas_width = 0
        self.setFixedHeight(30)
        self.setStyleSheet(f"background: {Colors.SECONDARY_BG}; border-bottom: 1px solid {Colors.SEPARATOR};")

    def set_canvas_width(self, w: int):
        self._canvas_width = w
        self.update()

    def set_days(self, days: List[date]):
        self.days = days
        self.update()

    def paintEvent(self, e):
        if not self.days:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Используем ширину канваса если она известна, иначе свою
        w = self._canvas_width if self._canvas_width > 0 else self.width()

        col_w = (w - self.time_w) / 5
        today = date.today()

        p.fillRect(0, 0, self.width(), self.height(), QColor(Colors.SECONDARY_BG))

        for i, d in enumerate(self.days):
            x = self.time_w + i * col_w
            is_today = (d == today)

            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(int(x), 0, int(x), self.height())

            text = f"{self.day_names[i]} {d.day}"

            if is_today:
                p.setPen(QColor(Colors.RED))
            else:
                p.setPen(QColor(Colors.SECONDARY_TEXT))

            f = QFont("Helvetica Neue", 10, QFont.Normal)
            p.setFont(f)
            p.drawText(int(x), 0, int(col_w), self.height(), Qt.AlignCenter, text)

        p.end()

class WeekCanvas(QWidget):
    """Рисуемая сетка рабочей недели"""
    event_clicked       = pyqtSignal(object)
    slot_double_clicked = pyqtSignal(date, QTime)
    width_changed       = pyqtSignal(int)

    def __init__(self, db, hour_h, time_w):
        super().__init__()
        self.db     = db
        self.HOUR_H = hour_h
        self.TIME_W = time_w
        self.days: List[date] = []
        self.events: List['Event'] = []
        self._event_rects: List[tuple] = []
        self.setMinimumHeight(24 * hour_h)

    def set_data(self, days: List[date], events: List['Event']):
        self.days   = days
        self.events = events
        self._event_rects = []
        self.update()

    def mousePressEvent(self, e):
        """Одиночный клик - можно оставить пустым"""
        pass

    def mouseDoubleClickEvent(self, e):
        """Двойной клик - открыть событие или создать новое"""
        if not self.days:
            return
        
        # Проверяем, попали ли в существующее событие
        for rect, ev in self._event_rects:
            if rect.contains(e.pos()):
                self.event_clicked.emit(ev)  # открыть существующее событие
                return
        
        # Пустое место - создаём новое событие
        x, y = e.pos().x(), e.pos().y()
        col_w = (self.width() - self.TIME_W) / 5
        col = int((x - self.TIME_W) / col_w)
        if 0 <= col < 5:
            hour = y // self.HOUR_H
            minute = ((y % self.HOUR_H) * 60 // self.HOUR_H // 15) * 15
            self.slot_double_clicked.emit(self.days[col], QTime(min(hour, 23), minute))

    def paintEvent(self, e):
        if not self.days:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w  = self.width()
        col_w = (w - self.TIME_W) / 5
        today = date.today()

        p.fillRect(0, 0, w, self.height(), QColor(Colors.BG))

        # Hour rows
        for hour in range(24):
            y = hour * self.HOUR_H
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            f = QFont("Helvetica Neue", 10)
            p.setFont(f)
            p.drawText(0, y, self.TIME_W - 6, self.HOUR_H, Qt.AlignRight | Qt.AlignTop,
                       f"{hour:02d}:00")
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(self.TIME_W, y, w, y)
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5, Qt.DashLine))
            p.drawLine(self.TIME_W, y + self.HOUR_H // 2, w, y + self.HOUR_H // 2)

        # Column separators + today highlight
        for i in range(5):
            x = int(self.TIME_W + i * col_w)
            if self.days[i] == today:
                p.fillRect(x, 0, int(col_w), self.height(), QColor(Colors.ACCENT_LIGHT))
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(x, 0, x, self.height())

        # Events
        self._event_rects = []

        # Группируем события по дням
        events_by_day = {day: [] for day in self.days}
        for ev in self.events:
            ev_date = ev.start_dt.date()
            if ev_date in events_by_day:
                events_by_day[ev_date].append(ev)

        for col, day in enumerate(self.days):
            day_events = events_by_day.get(day, [])
            if not day_events:
                continue
            
            # Группируем overlapping события для этого дня
            overlapping_groups = self._group_overlapping_events(day_events)
            
            x = int(self.TIME_W + col * col_w) + 3
            cw = int(col_w) - 6
            
            for group in overlapping_groups:
                group_size = len(group)
                if group_size == 0:
                    continue
                    
                # Делим ширину колонки между событиями в группе
                segment_width = cw // group_size
                
                for idx, ev in enumerate(group):
                    sh, sm = ev.start_dt.hour, ev.start_dt.minute
                    eh, em = ev.end_dt.hour, ev.end_dt.minute
                    y1 = sh * self.HOUR_H + sm * self.HOUR_H // 60
                    y2 = eh * self.HOUR_H + em * self.HOUR_H // 60
                    if y2 <= y1:
                        y2 = y1 + self.HOUR_H // 2

                    # Сдвигаем каждый блок в группе
                    x_offset = x + (idx * segment_width)
                    rect = QRect(x_offset, y1 + 1, segment_width - 2, y2 - y1 - 2)

                    color = QColor(ev.color)
                    
                    # Отрисовка
                    light = QColor(color)
                    light.setAlpha(25)
                    p.setBrush(QBrush(light))
                    p.setPen(Qt.NoPen)
                    path = QPainterPath()
                    path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 5, 5)
                    p.drawPath(path)

                    p.setBrush(QBrush(color))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(rect.x(), rect.y(), 4, rect.height(), 2, 2)

                    p.setPen(color.darker(140))
                    f2 = QFont("Helvetica Neue", 10, QFont.Normal)
                    p.setFont(f2)
                    tr = rect.adjusted(8, 3, -3, -3)
                    time_s = f"{ev.start_dt.strftime('%H:%M')}"

                    font_metrics = QFontMetrics(f2)

                    if rect.height() > 28:
                        if group_size > 2:
                            short_title = ev.title[:10] + "..." if len(ev.title) > 10 else ev.title
                            p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                                    f"{short_title}\n{time_s}")
                        else:
                            available_width = rect.width() - 11
                            elided_title = font_metrics.elidedText(ev.title, Qt.ElideRight, available_width)
                            p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                                    f"{elided_title}\n{time_s}")
                    else:
                        if group_size > 2:
                            short_title = ev.title[:6] + "..." if len(ev.title) > 6 else ev.title
                            p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, f"{short_title} {time_s}")
                        else:
                            available_width = rect.width() - 11
                            full_text = f"{ev.title} {time_s}"
                            elided_text = font_metrics.elidedText(full_text, Qt.ElideRight, available_width)
                            p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, elided_text)
                    
                    self._event_rects.append((rect, ev))

        # Current-time line
        if today in self.days:
            now  = datetime.now()
            ny   = now.hour * self.HOUR_H + now.minute * self.HOUR_H // 60
            col  = self.days.index(today)
            lx   = int(self.TIME_W + col * col_w)
            rx   = int(self.TIME_W + (col + 1) * col_w)
            p.setPen(QPen(QColor(Colors.RED), 2))
            p.drawLine(lx, ny, rx, ny)
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(lx - 4, ny - 4, 8, 8)

        p.end()

    def resizeEvent(self, event):
        """При изменении размера окна перерисовываем"""
        self.update()
        self.width_changed.emit(self.width())
        super().resizeEvent(event)

    def _group_overlapping_events(self, events):
        """Группирует события, которые пересекаются по времени"""
        if not events:
            return []
        
        sorted_events = sorted(events, key=lambda e: (e.start_dt, e.end_dt))
        groups = []
        current_group = [sorted_events[0]]
        
        for ev in sorted_events[1:]:
            overlaps = False
            for group_ev in current_group:
                if not (ev.start_dt >= group_ev.end_dt or ev.end_dt <= group_ev.start_dt):
                    overlaps = True
                    break
            
            if overlaps:
                current_group.append(ev)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [ev]
        
        if current_group:
            groups.append(current_group)
        
        return groups

# ─────────────────────────────────────────────
# YEAR VIEW  (12 мини-календарей 3×4)
# ─────────────────────────────────────────────

class YearView(QWidget):
    event_changed  = pyqtSignal()
    month_selected = pyqtSignal(date)   # при клике → MonthView

    MONTH_NAMES = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                   "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._event_dates: set = set()
        self._month_rects: List[tuple] = []   # (QRect, month_idx 1-12)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # Контейнер может растягиваться
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet(f"background: {Colors.BG};")
        
        # Контейнер для центрирования canvas
        container = QWidget()
        container.setStyleSheet(f"background: {Colors.BG};")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignCenter)  # ← центрируем содержимое
        
        self._canvas = YearCanvas(self)
        self._canvas.month_clicked.connect(self.month_selected)
        container_layout.addWidget(self._canvas)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def refresh(self):
        year = self.current_date.year
        start = datetime(year, 1, 1)
        end   = datetime(year, 12, 31, 23, 59, 59)
        events = self.db.get_events_by_date_range(start, end)
        self._event_dates = {e.start_dt.date() for e in events}
        self._canvas.set_data(year, self._event_dates, date.today())

    def go_prev(self):
        self.current_date = self.current_date.replace(year=self.current_date.year - 1, day=1)
        self.refresh()

    def go_next(self):
        self.current_date = self.current_date.replace(year=self.current_date.year + 1, day=1)
        self.refresh()

    def go_today(self):
        self.current_date = date.today()
        self.refresh()

    def header_text(self) -> str:
        return str(self.current_date.year)

class YearCanvas(QWidget):
    month_clicked = pyqtSignal(date)

    COLS = 4
    DAY_LABELS = ["П","В","С","Ч","П","С","В"]
    
    # ПАРАМЕТРЫ БЛОКОВ ГОДА
    CARD_WIDTH = 220       # ШИРИНА КАРТОЧКИ МЕСЯЦА
    CARD_HEIGHT = 200      # ВЫСОТА КАРТОЧКИ МЕСЯЦА
    GAP = 26               # РАССТОЯНИЕ МЕЖДУ МЕСЯЦАМИ
    PAD = 0                # ОТСТУП ОТ КРАЁВ

    def __init__(self, parent=None):
        super().__init__(parent)
        self.year = date.today().year
        self.event_dates: set = set()
        self.today = date.today()
        self._month_rects: List[tuple] = []
        # 4 колонки × 3 строки = 12 месяцев
        total_width = self.PAD * 2 + self.COLS * self.CARD_WIDTH + (self.COLS - 1) * self.GAP
        total_height = self.PAD * 2 + 3 * self.CARD_HEIGHT + 2 * self.GAP
        self.setFixedSize(total_width, total_height)

    def set_data(self, year: int, event_dates: set, today: date):
        self.year = year
        self.event_dates = event_dates
        self.today = today
        self._month_rects = []
        self.update()

    def mousePressEvent(self, e):
        for rect, month_idx in self._month_rects:
            if rect.contains(e.pos()):
                self.month_clicked.emit(date(self.year, month_idx, 1))
                return

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        p.fillRect(0, 0, W, H, QColor(Colors.BG))

        self._month_rects = []

        for m in range(12):
            row = m // self.COLS
            col = m % self.COLS
            mx = self.PAD + col * (self.CARD_WIDTH + self.GAP)
            my = self.PAD + row * (self.CARD_HEIGHT + self.GAP)
            mw = self.CARD_WIDTH
            mh = self.CARD_HEIGHT

            month_rect = QRect(mx, my, mw, mh)
            self._month_rects.append((month_rect, m + 1))


            # Month name
            is_cur_month = (self.year == self.today.year and m + 1 == self.today.month)
            p.setPen(QColor(Colors.RED if is_cur_month else Colors.PRIMARY_TEXT))
            f_title = QFont("Helvetica Neue", 10, QFont.DemiBold)
            p.setFont(f_title)
            p.drawText(mx + 10, my + 6, mw - 20, 22, Qt.AlignLeft | Qt.AlignVCenter,
                       YearView.MONTH_NAMES[m])

            # Day-of-week headers
            header_y = my + 30
            day_cell_w = mw / 7
            day_cell_h = (mh - 34) / 7

            p.setPen(QColor(Colors.SECONDARY_TEXT))
            f_hdr = QFont("Helvetica Neue", 10)
            p.setFont(f_hdr)
            for di, dl in enumerate(self.DAY_LABELS):
                dx = int(mx + di * day_cell_w)
                color = Colors.RED if di >= 5 else Colors.SECONDARY_TEXT
                p.setPen(QColor(color))
                p.drawText(dx, header_y, int(day_cell_w), int(day_cell_h),
                           Qt.AlignCenter, dl)

            # Days grid
            first = date(self.year, m + 1, 1)
            start_wd = first.weekday()
            grid_start = first - timedelta(days=start_wd)
            f_day = QFont("Helvetica Neue", 10)
            p.setFont(f_day)

            for di in range(42):
                dr = di // 7
                dc = di % 7
                d = grid_start + timedelta(days=di)
                dx = int(mx + dc * day_cell_w)
                dy = int(header_y + (dr + 1) * day_cell_h)
                dw = int(day_cell_w)
                dh = int(day_cell_h)

                is_this_month = (d.month == m + 1)
                is_today = (d == self.today)
                has_event = (d in self.event_dates)

                if is_today:
                    circle_size = 18  # размер кружка
                    cx = dx + dw // 2 - circle_size // 2
                    cy = dy + dh // 2 - circle_size // 2
                    
                    p.setBrush(QBrush(QColor(Colors.RED)))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(cx, cy, circle_size, circle_size)
                    p.setPen(QColor("white"))
                    p.drawText(cx, cy, circle_size, circle_size, Qt.AlignCenter, str(d.day))
                else:
                    alpha_color = Colors.PRIMARY_TEXT if is_this_month else Colors.SEPARATOR
                    p.setPen(QColor(alpha_color))
                    if dc >= 5 and is_this_month:
                        p.setPen(QColor(Colors.WEEKEND))
                    p.drawText(dx, dy, dw, dh, Qt.AlignCenter, str(d.day))

                # Dot for events
                if has_event and is_this_month and not is_today:
                    dot_r = 2
                    cx = dx + dw // 2
                    cy = dy + dh - 1
                    p.setBrush(QBrush(QColor(Colors.ACCENT)))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

        p.end()

# ─────────────────────────────────────────────
# LIST VIEW  (все события, сгруппированные по датам)
# ─────────────────────────────────────────────

class ListView(QWidget):
    event_changed = pyqtSignal()

    MONTHS = ["января","февраля","марта","апреля","мая","июня",
              "июля","августа","сентября","октября","ноября","декабря"]
    WEEKDAYS = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._first_show = True
        self._build_ui()
        self.refresh()

    def showEvent(self, event):
        """Вызывается при первом показе виджета"""
        super().showEvent(event)
        if self._first_show:
            QTimer.singleShot(100, self.go_today)
            self._first_show = False

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {Colors.BG};")
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)
        self._vbox.addStretch()

        self.scroll.setWidget(self._content)
        root.addWidget(self.scroll)

    def refresh(self):
        # Remove all widgets except the trailing stretch
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        events = self.db.get_all_events()
        
        # Group by date
        groups: dict = defaultdict(list)
        for ev in events:
            groups[ev.start_dt.date()].append(ev)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Гарантируем, что "Сегодня" всегда отображается
        if today not in groups:
            groups[today] = []
        
        # Если вообще нет событий, показываем только "Сегодня" с сообщением
        if not events:
            # Всё равно создаём заголовок "Сегодня"
            pass  # groups уже содержит today = []
        
        idx = 0
        for d in sorted(groups.keys()):
            evs = groups[d]

            # Date header
            if d == today:
                label = "Сегодня"
            elif d == tomorrow:
                label = "Завтра"
            else:
                label = f"{self.WEEKDAYS[d.weekday()]}, {d.day} {self.MONTHS[d.month-1]} {d.year}"

            is_past = d < today
            header = self._make_date_header(label, is_past)
            self._vbox.insertWidget(idx, header)
            idx += 1

            # Если это сегодня и нет событий, показываем сообщение
            if d == today and len(evs) == 0:
                empty_lbl = QLabel("Нет событий на сегодня")
                empty_lbl.setStyleSheet(f"color: {Colors.SECONDARY_TEXT}; font-size: 12px; padding: 8px 24px; background: transparent;")
                self._vbox.insertWidget(idx, empty_lbl)
                idx += 1
            else:
                for ev in evs:
                    row = self._make_event_row(ev, is_past)
                    self._vbox.insertWidget(idx, row)
                    idx += 1

        # Добавляем принудительное обновление после добавления всех виджетов
        QTimer.singleShot(50, self._update_all_texts)

    def _update_all_texts(self):
        """Обновляет тексты во всех строках событий"""
        for child in self._content.findChildren(EventRowWidget):
            child._update_elided_texts()

    def resizeEvent(self, event):
        """При изменении размера окна обновляем обрезку текста в строках"""
        super().resizeEvent(event)
        self._update_all_texts()

    def _make_date_header(self, label: str, is_past: bool) -> QWidget:
        w = QWidget()
        w.setFixedHeight(30)
        w.setStyleSheet(f"background: {Colors.SECONDARY_BG};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(24, 0, 24, 0)
        lbl = QLabel(label)
        # Определяем цвет в зависимости от текста заголовка
        if label == "Сегодня":
            color = Colors.RED  # Красный для "Сегодня"
        elif is_past:
            color = Colors.SECONDARY_TEXT  # Серый для прошедших дат
        else:
            color = Colors.PRIMARY_TEXT  # Обычный цвет для будущих дат
        lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        lay.addWidget(lbl)
        lay.addStretch()
        return w

    def _make_event_row(self, ev: 'Event', is_past: bool) -> QWidget:
        w = EventRowWidget(ev, is_past)
        w.edit_requested.connect(self._on_edit)
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Убираем скругление у самого виджета
        w.setStyleSheet("border-radius: 0px;")
        return w

    def _on_edit(self, ev: 'Event'):
        dlg = EventDialog(self, db=self.db, event=ev)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            self.db.update_event(dlg.result_event)
            self.refresh()
            self.event_changed.emit()
        elif result == 2:
            self.db.delete_event(ev.id)
            self.refresh()
            self.event_changed.emit()

    def go_prev(self):  pass
    def go_next(self):  pass
    def go_today(self):
        """Плавно прокручивает список так, чтобы 'Сегодня' было в самом верху"""
        today = date.today()
        
        # Ищем заголовок с сегодняшней датой
        for i in range(self._vbox.count()):
            item = self._vbox.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Проверяем, является ли виджет заголовком даты
                if isinstance(widget, QWidget) and widget.findChild(QLabel):
                    label = widget.findChild(QLabel)
                    if label and label.text() == "Сегодня":
                        # Получаем позицию виджета
                        y_pos = widget.mapTo(self._content, QPoint(0, 0)).y()

                        scrollbar = self.scroll.verticalScrollBar()
                        animation = QPropertyAnimation(scrollbar, b"value")
                        animation.setDuration(500)  # Длительность в миллисекундах
                        animation.setStartValue(scrollbar.value())
                        animation.setEndValue(y_pos)
                        animation.setEasingCurve(QEasingCurve.OutCubic)  # Плавное замедление в конце
                        animation.start()
                        
                        # Сохраняем ссылку на анимацию чтобы она не удалилась
                        self._scroll_animation = animation
                        return
    def header_text(self) -> str: return "Список событий"

class EventRowWidget(QWidget):
    """Одна строка события в List View"""
    edit_requested = pyqtSignal(object)

    def __init__(self, ev: 'Event', is_past: bool):
        super().__init__()
        self.ev = ev
        self.is_past = is_past
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._build()
        # Устанавливаем атрибут для корректной работы стилей
        self.setAttribute(Qt.WA_StyledBackground, True)

    def showEvent(self, event):
        """Когда виджет становится видимым, обновляем текст"""
        super().showEvent(event)
        QTimer.singleShot(10, self._update_elided_texts)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_texts()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 0, 0)

        # Колонка 0: Цветовая точка
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet(
            f"background: {self.ev.color}; border-radius: 5px;"
            f"{'opacity: 0.4;' if self.is_past else ''}"
        )
        layout.addWidget(self.dot, 0, alignment=Qt.AlignVCenter)
        layout.addSpacing(6)

        # Колонка 1: Время
        time_str = f"{self.ev.start_dt.strftime('%H:%M')} – {self.ev.end_dt.strftime('%H:%M')}"
        self.time_lbl = QLabel(time_str)
        self.time_lbl.setFixedWidth(85)
        alpha = Colors.SECONDARY_TEXT
        self.time_lbl.setStyleSheet(f"color: {alpha}; font-size: 13px; background: transparent;")
        layout.addWidget(self.time_lbl, 0, alignment=Qt.AlignVCenter)
        layout.addSpacing(2)

        # Колонка 2: Название (растягивается)
        tc = Colors.SECONDARY_TEXT if self.is_past else Colors.PRIMARY_TEXT
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet(
            f"color: {tc}; font-size: 13px; background: transparent;"
            + ("text-decoration: line-through;" if self.is_past else "")
        )
        self.title_lbl.setWordWrap(False)
        self.title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.title_lbl, 1)

        # Колонка 3: Иконка категории
        cat_map = {"Работа": "💼", "Личное": "🏠", "Важное": "⭐"}
        self.badge = QLabel(cat_map.get(self.ev.category, "📌"))
        self.badge.setFixedWidth(40)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(self.badge, 0, alignment=Qt.AlignVCenter)

        # Принудительно включаем прозрачный фон по умолчанию
        self.setStyleSheet("background: transparent;")

    def _update_elided_texts(self):
        """Обновляет текст с обрезкой по ширине"""
        if self.width() <= 0:
            return
        
        available_width = self.width() - 214
        
        if available_width > 50:
            font_metrics = QFontMetrics(self.title_lbl.font())
            self.title_lbl.setText(font_metrics.elidedText(self.ev.title, Qt.ElideRight, available_width))

    def enterEvent(self, e):
        """При наведении мыши - подсветка всей строки"""
        super().enterEvent(e)
        # Подсветка всей строки от левого до правого края
        self.setStyleSheet(f"""
            background: {Colors.ACCENT_LIGHT};
            margin: 0px;
            padding: 0px;
        """)

    def leaveEvent(self, e):
        """При уходе мыши - убираем подсветку"""
        super().leaveEvent(e)
        self.setStyleSheet("background: transparent;")

    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e)
        self.edit_requested.emit(self.ev)

# ─────────────────────────────────────────────
# SEGMENTED CONTROL
# ─────────────────────────────────────────────

class SegmentedControl(QWidget):
    tab_changed = pyqtSignal(int)

    def __init__(self, labels: list):
        super().__init__()
        self.labels = labels
        self.active = 3  # default = Month
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.buttons = []
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setFixedHeight(28)
            btn.setFixedWidth(75)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)
        self._update_styles()

    def _on_click(self, idx: int):
        self.active = idx
        self._update_styles()
        self.tab_changed.emit(idx)

    def _update_styles(self):
        for i, btn in enumerate(self.buttons):
            if i == self.active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.ACCENT};
                        color: white;
                        border: none;
                        border-radius: 7px;
                        padding: 0 14px;
                        font-size: 13px;
                        font-weight: 600;
                        min-width: 70px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.SECONDARY_BG};
                        color: {Colors.PRIMARY_TEXT};
                        border: none;
                        border-radius: 7px;
                        padding: 0 14px;
                        font-size: 13px;
                        min-width: 70px;
                    }}
                    QPushButton:hover {{
                        background: {Colors.SEPARATOR};
                    }}
                """)

    def set_active(self, idx: int):
        self.active = idx
        self._update_styles()

# ─────────────────────────────────────────────
# NAVIGATION BAR
# ─────────────────────────────────────────────

class NavBar(QWidget):
    today_clicked = pyqtSignal()
    prev_clicked  = pyqtSignal()
    next_clicked  = pyqtSignal()
    add_clicked   = pyqtSignal()
    manage_categories = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QWidget {{
                background: {Colors.BG};
                border-bottom: 1px solid {Colors.SEPARATOR};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Today button
        self.today_btn = self._make_btn("Сегодня")
        self.today_btn.setFixedHeight(30)
        self.today_btn.setFixedWidth(120)
        self.today_btn.clicked.connect(self.today_clicked)
        layout.addWidget(self.today_btn)

        # Prev button <
        self.prev_btn = self._make_arrow_btn("<")
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.clicked.connect(self.prev_clicked)
        layout.addWidget(self.prev_btn)

        # Next button >
        self.next_btn = self._make_arrow_btn(">")
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.clicked.connect(self.next_clicked)
        layout.addWidget(self.next_btn)

        # Левая растяжка перед заголовком
        layout.addStretch()

        # Title - по центру
        self.title_lbl = QLabel()
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet(f"color: {Colors.PRIMARY_TEXT}; font-size: 13px; font-weight: 600; border: none;")
        layout.addWidget(self.title_lbl)

        # Правая растяжка после заголовка
        layout.addStretch()

        # Кнопка управления категориями
        self.cat_btn = QPushButton("Категории")
        self.cat_btn.setFixedHeight(30)
        self.cat_btn.setFixedWidth(120)
        self.cat_btn.setCursor(Qt.PointingHandCursor)
        self.cat_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG};
                color: {Colors.PRIMARY_TEXT};
                border: none;
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {Colors.SEPARATOR};
            }}
        """)
        self.cat_btn.clicked.connect(self.manage_categories)
        layout.addWidget(self.cat_btn)

        # Add event button
        self.add_btn = QPushButton("Событие")
        self.add_btn.setFixedHeight(30)
        self.add_btn.setFixedWidth(120)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #0063CC; }}
        """)
        self.add_btn.clicked.connect(self.add_clicked)
        layout.addWidget(self.add_btn)

    def _make_arrow_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG};
                color: {Colors.PRIMARY_TEXT};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
        """)
        return btn
    
    def _make_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG};
                color: {Colors.PRIMARY_TEXT};
                border: none;
                border-radius: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
        """)
        return btn

    def set_title(self, text: str):
        self.title_lbl.setText(text)

# ─────────────────────────────────────────────
# ACTIVITY BAR (аналог VS Code)
# ─────────────────────────────────────────────

class ActivityBar(QWidget):
    section_changed = pyqtSignal(int)  # 0 = Календарь, 1 = Задачи

    def __init__(self):
        super().__init__()
        self.setFixedWidth(49)
        self._active = 0

        # Основной горизонтальный layout: панель + линия-разделитель
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Внутренняя панель с кнопками
        inner = QWidget()
        inner.setStyleSheet(f"background: {Colors.ACTIVITY_BAR};;")
        inner.setFixedWidth(48)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self._btns = []
        icons = [("📅", "Календарь"), ("✅", "Задачи")]
        for i, (icon, tip) in enumerate(icons):
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self._btns.append(btn)

        layout.addStretch()

        # Линия-разделитель справа (1px)
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
                        background: {Colors.WHITE};
                        color: {Colors.WHITE};
                        border: none;
                        border-radius: 4px;
                        font-size: 18px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {Colors.SECONDARY_TEXT};
                        border: none;
                        border-radius: 4px;
                        font-size: 18px;
                    }}
                    QPushButton:hover {{
                        background: {Colors.WHITE};
                    }}
                """)

class TasksPlaceholder(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        lbl = QLabel("✅")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(lbl)

        lbl2 = QLabel("Задачи")
        lbl2.setAlignment(Qt.AlignCenter)
        lbl2.setStyleSheet(f"color: {Colors.SECONDARY_TEXT}; font-size: 18px; background: transparent;")
        layout.addWidget(lbl2)

        lbl3 = QLabel("Раздел в разработке")
        lbl3.setAlignment(Qt.AlignCenter)
        lbl3.setStyleSheet(f"color: {Colors.SEPARATOR}; font-size: 13px; background: transparent;")
        layout.addWidget(lbl3)

# ─────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self._seed_data_if_empty()
        self.setWindowTitle("Планировщик")
        self.setMinimumSize(1050, 780) # Ширина - высота
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # Горизонтальный корень: ActivityBar слева + контент справа
        h_root = QHBoxLayout(central)
        h_root.setContentsMargins(0, 0, 0, 0)
        h_root.setSpacing(0)

        # Activity Bar
        self.activity_bar = ActivityBar()
        self.activity_bar.section_changed.connect(self._switch_section)
        h_root.addWidget(self.activity_bar)

        # Правая часть: всё остальное
        right_widget = QWidget()
        root = QVBoxLayout(right_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        h_root.addWidget(right_widget, 1)

        # Top bar: segmented control
        top_bar = QWidget()
        top_bar.setFixedHeight(42)
        top_bar.setStyleSheet(f"""
            background: {Colors.ACTIVITY_BAR};
            border-bottom: 1px solid #C8C8C8;
            border-top: 1px solid #C8C8C8;
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(16, 4, 16, 4)
        self.segmented = SegmentedControl(["Список", "День", "Неделя", "Месяц", "Год"])
        self.segmented.tab_changed.connect(self._switch_view)
        tb_layout.addStretch()
        tb_layout.addWidget(self.segmented)
        tb_layout.addStretch()
        root.addWidget(top_bar)
        self.top_bar = top_bar

        # Nav bar
        self.navbar = NavBar()
        self.navbar.today_clicked.connect(self._go_today)
        self.navbar.prev_clicked.connect(self._go_prev)
        self.navbar.next_clicked.connect(self._go_next)
        self.navbar.add_clicked.connect(self._add_event)
        self.navbar.manage_categories.connect(self._manage_categories)
        root.addWidget(self.navbar)

        # Секции: Календарь и Задачи
        self.section_stack = QStackedWidget()

        # Секция 0 — Календарь (stacked views)
        calendar_widget = QWidget()
        cal_layout = QVBoxLayout(calendar_widget)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.list_view  = ListView(self.db)
        self.day_view   = DayView(self.db)
        self.week_view  = WeekView(self.db)
        self.month_view = MonthView(self.db)
        self.year_view  = YearView(self.db)

        for v in [self.list_view, self.day_view, self.week_view, self.month_view, self.year_view]:
            self.stack.addWidget(v)
            v.event_changed.connect(self._on_event_changed)

        self.month_view.day_clicked.connect(self._on_day_clicked)
        self.year_view.month_selected.connect(self._on_month_selected)
        cal_layout.addWidget(self.stack, 1)

        self.section_stack.addWidget(calendar_widget)

        # Секция 1 — Задачи (заглушка)
        self.tasks_placeholder = TasksPlaceholder()
        self.section_stack.addWidget(self.tasks_placeholder)

        root.addWidget(self.section_stack, 1)

        # Default: Month view
        self.stack.setCurrentIndex(3)
        self._update_title()

    def _current_view(self):
        return self.stack.currentWidget()

    def _switch_view(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self._update_title()

    def _switch_section(self, idx: int):
        self.section_stack.setCurrentIndex(idx)
        is_calendar = (idx == 0)
        self.top_bar.setVisible(is_calendar)
        self.navbar.setVisible(is_calendar)

    def _update_title(self):
        v = self._current_view()
        if hasattr(v, 'header_text'):
            self.navbar.set_title(v.header_text())

    def _go_today(self):
        self._current_view().go_today()
        self._update_title()

    def _go_prev(self):
        self._current_view().go_prev()
        self._update_title()

    def _go_next(self):
        self._current_view().go_next()
        self._update_title()

    def _on_day_clicked(self, d: date):
        self.day_view.current_date = d
        self.day_view.refresh()
        self.stack.setCurrentIndex(1)
        self.segmented.set_active(1)
        self._update_title()

    def _on_month_selected(self, d: date):
        self.month_view.current_date = d
        self.month_view.refresh()
        self.stack.setCurrentIndex(3)
        self.segmented.set_active(3)
        self._update_title()

    def _add_event(self):
        v = self._current_view()
        preset_date = getattr(v, 'current_date', date.today())
        if isinstance(preset_date, datetime):
            preset_date = preset_date.date()
        # ИСПРАВЬТЕ - добавьте db=self.db
        dlg = EventDialog(self, db=self.db, preset_date=preset_date)
        if dlg.exec_() == QDialog.Accepted:
            self.db.add_event(dlg.result_event)
            self._on_event_changed()

    def _on_event_changed(self):
        for v in [self.list_view, self.day_view, self.week_view, self.month_view, self.year_view]:
            v.refresh()
        self._update_title()

    def _seed_data_if_empty(self):
        if self.db.count() > 0:
            return
        today = date.today()
        seed = [
            Event("Планёрка команды", datetime(today.year, today.month, today.day, 9, 0),
                datetime(today.year, today.month, today.day, 10, 0), "Работа", "Еженедельная встреча"),
            Event("Обед с клиентом", datetime(today.year, today.month, today.day, 12, 30),
                datetime(today.year, today.month, today.day, 14, 0), "Важное", "Ресторан Центральный"),
            Event("Дедлайн проекта", (datetime.now() + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0),
                (datetime.now() + timedelta(days=3)).replace(hour=19, minute=0, second=0, microsecond=0), "Важное"),
            Event("День рождения Ани", (datetime.now() + timedelta(days=5)).replace(hour=19, minute=0, second=0, microsecond=0),
                (datetime.now() + timedelta(days=5)).replace(hour=22, minute=0, second=0, microsecond=0), "Личное"),
            Event("Код-ревью", (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0),
                (datetime.now() + timedelta(days=1)).replace(hour=16, minute=30, second=0, microsecond=0), "Работа"),
        ]
        for e in seed:
            self.db.add_event(e)

    def _manage_categories(self):
        """Открывает диалог управления категориями"""
        dlg = CategoryDialog(self, self.db.category_manager)
        if dlg.exec_() == QDialog.Accepted:
            # Обновляем все view
            self._on_event_changed()
            # Обновляем цвета всех событий
            for v in [self.list_view, self.day_view, self.week_view, self.month_view, self.year_view]:
                v.refresh()

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    # Определяем базовый путь
    if getattr(sys, 'frozen', False):
        # Запущено как .exe (PyInstaller)
        base_path = sys._MEIPASS
    else:
        # Запущено как .py скрипт
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Путь к папке с иконками
    icon_folder = os.path.join(base_path, "icon_windows")
    
    # Ищем иконку (можно .png или .ico)
    icon_path = os.path.join(icon_folder, "icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(icon_folder, "icon.ico")
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Иконка не найдена в {icon_folder}")

    font = QFont("Helvetica Neue", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

# ─────────────────────────────────────────────
# УСТАНОВКА И ЗАПУСК
# ─────────────────────────────────────────────

# pip install PyQt5
# python calendar_app.py

# Требования: Python 3.8+, PyQt5

# Реализовано:
# ✅ Segmented control (5 кнопок)
# ✅ Month View — сетка 6x7, события, подсветка сегодня
# ✅ Day View   — временная шкала, события, линия "сейчас"
# ✅ Week View  — Пн–Пт, временная шкала, события, линия "сейчас"
# ✅ Year View  — 12 мини-календарей 3×4, точки событий,
#    клик на месяц → Month View
# ✅ List View  — все события сгруппированы по датам,
#    прошедшие зачёркнуты, hover → редактирование
# ✅ SQLite хранилище с автосохранением
# ✅ EventDialog — добавление, редактирование, удаление
# ✅ Навигация вперёд/назад/сегодня
# ✅ Цветовые категории: work / personal / important

# Coming soon:
# ⬜ Тёмная тема
# ⬜ Drag & Drop
# ⬜ Повторяющиеся события