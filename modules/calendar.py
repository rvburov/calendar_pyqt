import sqlite3
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, List
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QDialog, QLineEdit, QTextEdit, QComboBox,
    QDateEdit, QTimeEdit, QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import (
    Qt, QDate, QTime, QTimer, QPoint, QRect, QSize, pyqtSignal,
    QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QFontMetrics,
    QPainterPath, QPixmap, QIcon
)

from core.styles import Colors
from core.database import DatabaseManager, Category, CategoryManager


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
    _db: Optional[object] = None

    @property
    def color(self) -> str:
        if self._db and hasattr(self._db, 'category_manager'):
            cat = self._db.category_manager.get_category_by_name(self.category)
            if cat:
                return cat.color
        return {"Работа": "#007AFF", "Личное": "#34C759",
                "Важное": "#FF3B30"}.get(self.category, Colors.ACCENT)


# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def _row_to_event(db, row) -> Event:
    cat = db.category_manager.get_category_by_id(row[5])
    ev = Event(
        id=row[0], title=row[1], description=row[2],
        start_dt=datetime.fromisoformat(row[3]),
        end_dt=datetime.fromisoformat(row[4]),
        category=cat.name if cat else "Личное",
        category_id=row[5]
    )
    ev._db = db
    return ev

def db_add_event(db, event: Event) -> Event:
    cat = db.category_manager.get_category_by_name(event.category)
    cat_id = cat.id if cat else 1
    cur = db.conn.execute(
        "INSERT INTO events (title, description, start_dt, end_dt, category) VALUES (?,?,?,?,?)",
        (event.title, event.description,
         event.start_dt.isoformat(), event.end_dt.isoformat(), cat_id)
    )
    db.conn.commit()
    event.id = cur.lastrowid
    event.category_id = cat_id
    event._db = db
    return event

def db_update_event(db, event: Event):
    cat = db.category_manager.get_category_by_name(event.category)
    cat_id = cat.id if cat else 1
    db.conn.execute(
        "UPDATE events SET title=?, description=?, start_dt=?, end_dt=?, category=? WHERE id=?",
        (event.title, event.description,
         event.start_dt.isoformat(), event.end_dt.isoformat(), cat_id, event.id)
    )
    db.conn.commit()
    event.category_id = cat_id
    event._db = db

def db_delete_event(db, event_id: int):
    db.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
    db.conn.commit()

def db_get_events_by_date_range(db, start: datetime, end: datetime,
                                active_ids=None) -> List[Event]:
    cur = db.conn.execute(
        "SELECT * FROM events WHERE start_dt < ? AND end_dt > ? ORDER BY start_dt",
        (end.isoformat(), start.isoformat())
    )
    events = [_row_to_event(db, r) for r in cur.fetchall()]
    if active_ids is not None:
        events = [e for e in events if e.category_id in active_ids]
    return events

def db_get_all_events(db, active_ids=None) -> List[Event]:
    cur = db.conn.execute("SELECT * FROM events ORDER BY start_dt")
    events = [_row_to_event(db, r) for r in cur.fetchall()]
    if active_ids is not None:
        events = [e for e in events if e.category_id in active_ids]
    return events

def db_count_events(db) -> int:
    return db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]




# ─────────────────────────────────────────────
# EVENT DIALOG
# ─────────────────────────────────────────────

class EventDialog(QDialog):
    def __init__(self, parent=None, db=None, event: Optional[Event] = None,
                 preset_date: Optional[date] = None, preset_time: Optional[QTime] = None):
        super().__init__(parent)
        self.db = db
        self.event = event
        self.setWindowTitle("Изменить событие" if event else "Новое событие")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build_ui(preset_date, preset_time)
        self._apply_style()
        if event:
            self._fill_from_event(event)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: {Colors.BG}; border-radius: 12px; }}
            QLabel {{ color: {Colors.SECONDARY_TEXT}; font-size: 13px; font-weight: 600; }}
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {{
                background: {Colors.SECONDARY_BG}; border: 1.5px solid {Colors.SEPARATOR};
                border-radius: 8px; padding: 6px 10px; font-size: 13px;
                color: {Colors.PRIMARY_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QDateEdit:focus, QTimeEdit:focus {{ border-color: {Colors.ACCENT}; }}
            QPushButton#save_btn {{
                background: {Colors.ACCENT}; color: white; border: none;
                border-radius: 8px; font-size: 13px; font-weight: 600;
            }}
            QPushButton#save_btn:hover {{ background: #0063CC; }}
            QPushButton#delete_btn {{
                background: {Colors.RED}; color: white; border: none;
                border-radius: 8px; font-size: 13px;
            }}
        """)

    def _build_ui(self, preset_date, preset_time):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("Название"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Добавить название")
        layout.addWidget(self.title_edit)

        # Блок НАЧАЛО
        layout.addWidget(QLabel("Начало"))
        start_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd.MM.yyyy")
        if preset_date:
            self.start_date.setDate(QDate(preset_date.year, preset_date.month, preset_date.day))
        else:
            self.start_date.setDate(QDate.currentDate())
        start_layout.addWidget(self.start_date, 2)
        
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        if preset_time:
            self.start_time.setTime(preset_time)
        else:
            self.start_time.setTime(QTime(9, 0))
        start_layout.addWidget(self.start_time, 1)
        
        layout.addLayout(start_layout)

        # Блок КОНЕЦ
        layout.addWidget(QLabel("Конец"))
        end_layout = QHBoxLayout()
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd.MM.yyyy")
        if preset_date:
            self.end_date.setDate(QDate(preset_date.year, preset_date.month, preset_date.day))
        else:
            self.end_date.setDate(QDate.currentDate())
        end_layout.addWidget(self.end_date, 2)
        
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        if preset_time:
            self.end_time.setTime(preset_time.addSecs(3600))
        else:
            self.end_time.setTime(QTime(10, 0))
        end_layout.addWidget(self.end_time, 1)
        
        layout.addLayout(end_layout)

        layout.addWidget(QLabel("Календарь"))
        self.category_combo = QComboBox()
        self._load_categories()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Описание"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Добавить описание (необязательно)")
        self.desc_edit.setMaximumHeight(80)
        layout.addWidget(self.desc_edit)

        btn_layout = QHBoxLayout()
        if self.event:
            del_btn = QPushButton("Удалить")
            del_btn.setObjectName("delete_btn")
            del_btn.setFixedSize(120, 30)
            del_btn.clicked.connect(self._delete)
            btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("save_btn")
        save_btn.setFixedSize(120, 30)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_categories(self):
        self.category_combo.clear()
        cats = self.db.category_manager.get_all_categories() \
               if self.db and hasattr(self.db, 'category_manager') else []
        if not cats:
            cats = [Category("Работа","#007AFF"),
                    Category("Личное","#34C759"),
                    Category("Важное","#FF3B30")]
        for cat in cats:
            px = QPixmap(16, 16)
            px.fill(QColor(cat.color))
            self.category_combo.addItem(QIcon(px), cat.name, cat.name)

    def _fill_from_event(self, event: Event):
        self.title_edit.setText(event.title)
        self.start_date.setDate(QDate(event.start_dt.year, event.start_dt.month, event.start_dt.day))
        self.start_time.setTime(QTime(event.start_dt.hour, event.start_dt.minute))
        self.end_date.setDate(QDate(event.end_dt.year, event.end_dt.month, event.end_dt.day))
        self.end_time.setTime(QTime(event.end_dt.hour, event.end_dt.minute))
        self.desc_edit.setPlainText(event.description)
        for i in range(self.category_combo.count()):
            if self.category_combo.itemText(i) == event.category:
                self.category_combo.setCurrentIndex(i)
                break
        self._on_category_changed(event.category)

    def _on_category_changed(self, name: str):
        if self.db and hasattr(self.db, 'category_manager'):
            cat = self.db.category_manager.get_category_by_name(name)
            if cat:
                self.category_combo.setStyleSheet(f"""
                    QComboBox {{
                        background: {Colors.SECONDARY_BG};
                        border: 1.5px solid {cat.color};
                        border-radius: 8px; padding: 6px 10px;
                    }}
                """)
                return
        self.category_combo.setStyleSheet("")

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Ошибка", "Введите название события")
            return
        
        start_dt = datetime(
            self.start_date.date().year(),
            self.start_date.date().month(),
            self.start_date.date().day(),
            self.start_time.time().hour(),
            self.start_time.time().minute()
        )
        
        end_dt = datetime(
            self.end_date.date().year(),
            self.end_date.date().month(),
            self.end_date.date().day(),
            self.end_time.time().hour(),
            self.end_time.time().minute()
        )
        
        if end_dt <= start_dt:
            QMessageBox.warning(self, "Ошибка", "Время конца должно быть позже начала")
            return
        
        self.result_event = Event(
            id=self.event.id if self.event else None,
            title=title,
            description=self.desc_edit.toPlainText(),
            start_dt=start_dt,
            end_dt=end_dt,
            category=self.category_combo.currentText(),
        )
        self.result_event._db = self.db
        self.accept()

    def _delete(self):
        if QMessageBox.question(
            self, "Удалить", f'Удалить событие "{self.event.title}"?',
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.result_event = None
            self.done(2)


# ─────────────────────────────────────────────
# SEGMENTED CONTROL + NAVBAR
# ─────────────────────────────────────────────

class SegmentedControl(QWidget):
    tab_changed = pyqtSignal(int)

    def __init__(self, labels: list):
        super().__init__()
        self.active = 3
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.buttons = []
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setFixedSize(75, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)
        self._update_styles()

    def _on_click(self, idx: int):
        self.active = idx
        self._update_styles()
        self.tab_changed.emit(idx)

    def set_active(self, idx: int):
        self.active = idx
        self._update_styles()

    def _update_styles(self):
        for i, btn in enumerate(self.buttons):
            if i == self.active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.ACCENT}; color: white; border: none;
                        border-radius: 7px; font-size: 13px; font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.SECONDARY_BG}; color: {Colors.PRIMARY_TEXT};
                        border: none; border-radius: 7px; font-size: 13px;
                    }}
                    QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
                """)


class NavBar(QWidget):
    today_clicked = pyqtSignal()
    prev_clicked  = pyqtSignal()
    next_clicked  = pyqtSignal()
    add_clicked   = pyqtSignal()

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

        self.today_btn = self._btn("Сегодня")
        self.today_btn.clicked.connect(self.today_clicked)
        layout.addWidget(self.today_btn)

        for text, signal in [("<", self.prev_clicked), (">", self.next_clicked)]:
            btn = self._arrow_btn(text)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(signal)
            layout.addWidget(btn)

        layout.addStretch()

        self.title_lbl = QLabel()
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet(
            f"color: {Colors.PRIMARY_TEXT}; font-size: 13px;"
            f"font-weight: 600; border: none;"
        )
        layout.addWidget(self.title_lbl)

        layout.addStretch()

        self.add_btn = QPushButton("+ Событие")
        self.add_btn.setFixedSize(120, 30)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.ACCENT}; color: white; border: none;
                border-radius: 8px; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #0063CC; }}
        """)
        self.add_btn.clicked.connect(self.add_clicked)
        layout.addWidget(self.add_btn)

    def _btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(120, 30)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG}; color: {Colors.PRIMARY_TEXT};
                border: none; border-radius: 8px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
        """)
        return btn

    def _arrow_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SECONDARY_BG}; color: {Colors.PRIMARY_TEXT};
                border: none; border-radius: 8px; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {Colors.SEPARATOR}; }}
        """)
        return btn

    def set_title(self, text: str):
        self.title_lbl.setText(text)


# ─────────────────────────────────────────────
# DAY CELL
# ─────────────────────────────────────────────

class DayCell(QWidget):
    double_clicked = pyqtSignal(date)
    clicked = pyqtSignal(date)
    event_changed  = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.cell_date = None
        self.events: List[Event] = []
        self.is_current_month = True
        self.is_today = False
        self.is_weekend = False
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._hovered = False

    def set_data(self, cell_date, events, is_current_month, is_today, is_weekend):
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
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.cell_date:
            self.clicked.emit(self.cell_date)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.cell_date:
            self.double_clicked.emit(self.cell_date)

    def paintEvent(self, e):
        if not self.cell_date:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        bg = (Colors.ACCENT_LIGHT if self._hovered and self.is_current_month
              else "#FAFAFA" if not self.is_current_month else Colors.BG)
        p.fillRect(0, 0, w, h, QColor(bg))
        p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
        p.drawRect(0, 0, w - 1, h - 1)

        cs, cx, cy = 24, w - 30, 6
        p.setFont(QFont("Helvetica Neue", 10,
                        QFont.DemiBold if self.is_today else QFont.Normal))
        if self.is_today:
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(cx, cy, cs, cs)
            p.setPen(QColor(Colors.TODAY_TEXT))
        else:
            p.setPen(QColor(
                Colors.WEEKEND if self.is_weekend
                else Colors.SECONDARY_TEXT if not self.is_current_month
                else Colors.PRIMARY_TEXT
            ))
        p.drawText(cx, cy, cs, cs, Qt.AlignCenter, str(self.cell_date.day))

        tag_h, tag_y = 18, cy + cs + 4
        for ev in self.events[:3]:
            if tag_y + tag_h > h - 4:
                break
            color = QColor(ev.color)
            light = QColor(color); light.setAlpha(40)
            p.setBrush(QBrush(light)); p.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(6, tag_y, w - 12, tag_h, 4, 4)
            p.drawPath(path)
            p.setBrush(QBrush(color))
            p.drawRoundedRect(6, tag_y, 4, tag_h, 2, 2)
            p.setPen(color.darker(140))
            f2 = QFont("Helvetica Neue", 10)
            p.setFont(f2)
            txt = QFontMetrics(f2).elidedText(
                f"{ev.start_dt.strftime('%H:%M')} {ev.title}", Qt.ElideRight, w - 28
            )
            p.drawText(14, tag_y, w - 20, tag_h, Qt.AlignVCenter | Qt.AlignLeft, txt)
            tag_y += tag_h + 2

        rem = len(self.events) - 3
        if rem > 0:
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            p.setFont(QFont("Helvetica Neue", 10))
            p.drawText(6, tag_y, w - 12, 16, Qt.AlignVCenter | Qt.AlignLeft, f"+{rem} ещё")
        p.end()

    def resizeEvent(self, e): self.update(); super().resizeEvent(e)


# ─────────────────────────────────────────────
# MONTH VIEW
# ─────────────────────────────────────────────

class MonthView(QWidget):
    day_clicked   = pyqtSignal(date)
    event_changed = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._active_ids = None
        self._build_ui()
        self.refresh()

    def set_active_ids(self, ids):
        self._active_ids = ids
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet(
            f"background:{Colors.SECONDARY_BG}; border-bottom:1px solid {Colors.SEPARATOR};"
        )
        h_lay = QGridLayout(header)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(0)
        for i, d in enumerate(["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {Colors.WEEKEND if i >= 5 else Colors.SECONDARY_TEXT}; font-size: 13px;"
            )
            h_lay.addWidget(lbl, 0, i)
        layout.addWidget(header)

        gw = QWidget()
        gw.setStyleSheet(f"background: {Colors.BG};")
        self.grid = QGridLayout(gw)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(0)
        layout.addWidget(gw, 1)

        self.cells = []
        for row in range(6):
            row_cells = []
            for col in range(7):
                cell = DayCell(self.db)
                cell.double_clicked.connect(self._on_cell_dblclick)
                cell.clicked.connect(self._on_cell_click)
                cell.event_changed.connect(self.event_changed)
                self.grid.addWidget(cell, row, col)
                row_cells.append(cell)
            self.cells.append(row_cells)

    def _on_cell_dblclick(self, d: date):
        dlg = EventDialog(self, db=self.db, preset_date=d)
        if dlg.exec_() == QDialog.Accepted:
            db_add_event(self.db, dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def _on_cell_click(self, d: date):
        self.day_clicked.emit(d)

    def refresh(self):
        today = date.today()
        first = self.current_date.replace(day=1)
        grid_start = first - timedelta(days=first.weekday())
        events = db_get_events_by_date_range(
            self.db,
            datetime.combine(grid_start, datetime.min.time()),
            datetime.combine(grid_start + timedelta(days=42), datetime.max.time()),
            active_ids=self._active_ids
        )
        for row in range(6):
            for col in range(7):
                cd = grid_start + timedelta(days=row * 7 + col)
                # Показываем события, которые попадают на этот день
                day_events = []
                for ev in events:
                    if ev.start_dt.date() <= cd <= ev.end_dt.date():
                        day_events.append(ev)
                self.cells[row][col].set_data(
                    cd,
                    day_events,
                    cd.month == self.current_date.month,
                    cd == today, 
                    col >= 5
                )

    def go_prev(self):
        m, y = self.current_date.month - 1, self.current_date.year
        if m == 0: m, y = 12, y - 1
        self.current_date = self.current_date.replace(year=y, month=m, day=1)
        self.refresh()

    def go_next(self):
        m, y = self.current_date.month + 1, self.current_date.year
        if m == 13: m, y = 1, y + 1
        self.current_date = self.current_date.replace(year=y, month=m, day=1)
        self.refresh()

    def go_today(self):
        self.current_date = date.today(); self.refresh()

    def header_text(self) -> str:
        months = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                  "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
        return f"{months[self.current_date.month-1]} {self.current_date.year}"


# ─────────────────────────────────────────────
# DAY VIEW + DAY CANVAS
# ─────────────────────────────────────────────

class DayView(QWidget):
    event_changed = pyqtSignal()
    HOUR_H = 60

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._active_ids = None
        self._build_ui()
        self.refresh()

    def set_active_ids(self, ids):
        self._active_ids = ids
        self.refresh()
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
        self._canvas.double_clicked_time.connect(self._on_dblclick)
        self._canvas.event_clicked.connect(self._on_event_click)
        self._canvas.event_moved.connect(self._on_event_moved)
        self._canvas.event_resized.connect(self._on_event_resized)  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        scroll.setWidget(self._canvas)
        layout.addWidget(scroll)
        QTimer.singleShot(100, lambda: scroll.verticalScrollBar().setValue(
            max(0, (datetime.now().hour - 2) * self.HOUR_H)
        ))

    def _on_dblclick(self, t: QTime):
        dlg = EventDialog(self, db=self.db, preset_date=self.current_date, preset_time=t)
        if dlg.exec_() == QDialog.Accepted:
            db_add_event(self.db, dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def _on_event_click(self, ev: Event):
        dlg = EventDialog(self, db=self.db, event=ev)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            db_update_event(self.db, dlg.result_event)
        elif result == 2:
            db_delete_event(self.db, ev.id)
        if result in (QDialog.Accepted, 2):
            self.refresh()
            self.event_changed.emit()

    def _on_event_moved(self, event: Event, new_start_time: QTime, new_end_time: QTime):
        """Обработчик перемещения события"""
        # event.start_dt и event.end_dt уже корректно обновлены в DayCanvas._update_event_position
        # (включая переход через полночь), поэтому сохраняем их без перезаписи даты
        db_update_event(self.db, event)
        self.refresh()
        self.event_changed.emit()

    def _on_event_resized(self, event: Event, new_start_time: QTime, new_end_time: QTime):
        """Обработчик изменения размера события"""
        # event.start_dt и event.end_dt уже корректно обновлены в DayCanvas.mouseMoveEvent
        db_update_event(self.db, event)
        self.refresh()
        self.event_changed.emit()

    def refresh(self):
        events = db_get_events_by_date_range(
            self.db,
            datetime.combine(self.current_date, datetime.min.time()),
            datetime.combine(self.current_date, datetime.max.time()),
            active_ids=self._active_ids
        )
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
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        months = ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        d = self.current_date
        return f"{days[d.weekday()]}, {d.day} {months[d.month-1]} {d.year}"


class DayCanvas(QWidget):
    double_clicked_time = pyqtSignal(QTime)
    event_clicked       = pyqtSignal(Event)
    event_moved         = pyqtSignal(Event, QTime, QTime)
    event_resized       = pyqtSignal(Event, QTime, QTime)
    HOUR_H = 60
    TIME_W = 56
    PAD_R = 12
    RESIZE_MARGIN = 10

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self.events: List[Event] = []  # Оригинальные события
        self._event_rects: List[tuple] = []
        self.setMinimumHeight(24 * self.HOUR_H)
        self.setMouseTracking(True)
        
        # Для перемещения
        self.dragging_event = None
        self.drag_start_y = None
        self.drag_original_start_minutes = None
        self.drag_original_start = None
        self.drag_original_end = None
        
        # Для изменения размера
        self.resizing_event = None
        self.resizing_edge = None
        self.resize_start_y = None
        self.resize_original_start = None
        self.resize_original_end = None
        
        # Выделенное событие
        self.selected_event = None
        self.hover_edge = None

    def set_data(self, d, events):
        self.current_date = d
        self.events = events  # Сохраняем оригинальные события
        self._event_rects = []
        self.selected_event = None
        self.hover_edge = None
        self.update()

    def _get_display_time(self, ev, day):
        """Получить время отображения события для конкретного дня"""
        if day == ev.start_dt.date():
            start_time = ev.start_dt
        else:
            start_time = datetime(day.year, day.month, day.day, 0, 0)
        
        if day == ev.end_dt.date():
            end_time = ev.end_dt
        else:
            end_time = datetime(day.year, day.month, day.day, 23, 59)
        
        return start_time, end_time

    def _get_event_at_pos(self, pos):
        """Найти событие по позиции мыши"""
        for rect, ev in self._event_rects:
            if rect.contains(pos):
                return rect, ev
        return None, None

    def _get_resize_edge(self, rect, pos):
        if abs(pos.y() - rect.y()) <= self.RESIZE_MARGIN:
            return 'top'
        if abs(pos.y() - (rect.y() + rect.height())) <= self.RESIZE_MARGIN:
            return 'bottom'
        return None

    def _update_event_position(self, event, new_start_minutes):
        """Обновить позицию события с фиксацией 15 минут"""
        duration = int((event.end_dt - event.start_dt).total_seconds()) // 60
        
        # Округляем начальное время до 15 минут
        new_start_minutes = round(new_start_minutes / 15) * 15
        
        # Нормализуем минуты
        days_offset = new_start_minutes // (24 * 60)
        new_start_minutes = new_start_minutes % (24 * 60)
        
        if new_start_minutes < 0:
            new_start_minutes += 24 * 60
            days_offset -= 1
        
        new_hour = new_start_minutes // 60
        new_minute = new_start_minutes % 60
        new_date = self.current_date + timedelta(days=days_offset)
        
        new_start_dt = datetime(
            new_date.year, new_date.month, new_date.day,
            new_hour, new_minute
        )
        new_end_dt = new_start_dt + timedelta(minutes=duration)
        
        event.start_dt = new_start_dt
        event.end_dt = new_end_dt
        self.update()
        return True

    def mouseMoveEvent(self, e):
        rect, ev = self._get_event_at_pos(e.pos())
        
        if rect and ev:
            edge = self._get_resize_edge(rect, e.pos())
            if edge == 'top' or edge == 'bottom':
                self.setCursor(Qt.SizeVerCursor)
                self.hover_edge = edge
            else:
                self.setCursor(Qt.ArrowCursor)
                self.hover_edge = None
        else:
            self.setCursor(Qt.ArrowCursor)
            self.hover_edge = None
        
        if self.resizing_event and self.resize_start_y is not None:
            delta_y = e.pos().y() - self.resize_start_y
            delta_minutes = int(delta_y / self.HOUR_H * 60)
            
            if self.resizing_edge == 'top':
                new_start = self.resize_original_start + timedelta(minutes=delta_minutes)
                rounded_minutes = round(new_start.minute / 15) * 15
                if rounded_minutes >= 60:
                    new_start = new_start + timedelta(hours=1)
                    new_start = new_start.replace(minute=0)
                else:
                    new_start = new_start.replace(minute=rounded_minutes)

                min_start = datetime(new_start.year, new_start.month, new_start.day, 0, 0)
                max_start = self.resize_original_end - timedelta(minutes=15)
                if new_start < min_start:
                    new_start = min_start
                if new_start > max_start:
                    new_start = max_start

                self.resizing_event.start_dt = new_start
                self.update()

            elif self.resizing_edge == 'bottom':
                new_end = self.resize_original_end + timedelta(minutes=delta_minutes)
                rounded_minutes = round(new_end.minute / 15) * 15
                if rounded_minutes >= 60:
                    new_end = new_end + timedelta(hours=1)
                    new_end = new_end.replace(minute=0)
                else:
                    new_end = new_end.replace(minute=rounded_minutes)

                max_end = datetime(new_end.year, new_end.month, new_end.day, 23, 59)
                min_end = self.resize_original_start + timedelta(minutes=15)
                if new_end > max_end:
                    new_end = max_end
                if new_end < min_end:
                    new_end = min_end

                self.resizing_event.end_dt = new_end
                self.update()

        elif self.dragging_event and self.drag_start_y is not None:
            delta_y = e.pos().y() - self.drag_start_y
            delta_minutes = int(delta_y / self.HOUR_H * 60)
            new_start_minutes = self.drag_original_start_minutes + delta_minutes
            self._update_event_position(self.dragging_event, new_start_minutes)

        else:
            super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            rect, ev = self._get_event_at_pos(e.pos())
            
            if rect and ev:
                edge = self._get_resize_edge(rect, e.pos())
                
                if edge:
                    self.resizing_event = ev
                    self.resizing_edge = edge
                    self.resize_start_y = e.pos().y()
                    self.resize_original_start = ev.start_dt
                    self.resize_original_end = ev.end_dt
                    self.selected_event = ev
                    self.update()
                    return
                else:
                    self.dragging_event = ev
                    self.drag_start_y = e.pos().y()
                    # Учитываем дату события относительно current_date,
                    # чтобы многодневные события не прыгали при начале drag
                    date_offset = (ev.start_dt.date() - self.current_date).days
                    self.drag_original_start_minutes = (
                        date_offset * 24 * 60 + ev.start_dt.hour * 60 + ev.start_dt.minute
                    )
                    self.drag_original_start = ev.start_dt
                    self.drag_original_end = ev.end_dt
                    self.selected_event = ev
                    self.update()
                    return

            if self.selected_event:
                self.selected_event = None
                self.update()

        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self.dragging_event and self.drag_start_y is not None:
            if (self.dragging_event.start_dt != self.drag_original_start or
                self.dragging_event.end_dt != self.drag_original_end):
                self.event_moved.emit(
                    self.dragging_event,
                    self.dragging_event.start_dt.time(),
                    self.dragging_event.end_dt.time()
                )

        if self.resizing_event and self.resize_start_y is not None:
            if (self.resizing_event.start_dt != self.resize_original_start or
                self.resizing_event.end_dt != self.resize_original_end):
                self.event_resized.emit(
                    self.resizing_event,
                    self.resizing_event.start_dt.time(),
                    self.resizing_event.end_dt.time()
                )

        self.dragging_event = None
        self.drag_start_y = None
        self.drag_original_start_minutes = None
        self.drag_original_start = None
        self.drag_original_end = None
        self.resizing_event = None
        self.resizing_edge = None
        self.resize_start_y = None
        self.resize_original_start = None
        self.resize_original_end = None
        
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        rect, ev = self._get_event_at_pos(e.pos())
        if rect and ev:
            self.event_clicked.emit(ev)
            return
        y = e.pos().y()
        minutes = int(y / self.HOUR_H * 60)
        minutes = max(0, min(minutes, 23 * 60 + 45))
        self.double_clicked_time.emit(QTime(minutes // 60, minutes % 60))

    def _draw_block(self, p, rect, color, ev, gsz):
        is_selected = (self.selected_event and self.selected_event.id == ev.id)
        is_dragging = (self.dragging_event and self.dragging_event.id == ev.id)
        
        if is_selected or is_dragging:
            light = QColor(color)
            light.setAlpha(80 if is_dragging else 60)
            p.setBrush(QBrush(light))
            p.setPen(QPen(color, 2))
        else:
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
        f2 = QFont("Helvetica Neue", 10)
        p.setFont(f2)
        tr = rect.adjusted(8, 3, -3, -3)
        fm = QFontMetrics(f2)
        avail = rect.width() - 11
        time_s = ev.start_dt.strftime('%H:%M')
        if rect.height() > 28:
            title = fm.elidedText(ev.title, Qt.ElideRight, avail) if gsz <= 2 \
                    else (ev.title[:10] + "..." if len(ev.title) > 10 else ev.title)
            p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                       f"{title}\n{time_s}")
        else:
            p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft,
                       fm.elidedText(f"{ev.title} {time_s}", Qt.ElideRight, avail))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        p.fillRect(0, 0, w, self.height(), QColor(Colors.BG))

        # Рисуем сетку времени
        for hour in range(24):
            y = hour * self.HOUR_H
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            p.setFont(QFont("Helvetica Neue", 10))
            p.drawText(0, y, self.TIME_W - 8, self.HOUR_H,
                       Qt.AlignRight | Qt.AlignTop, f"{hour:02d}:00")
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(self.TIME_W, y, w - self.PAD_R, y)
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5, Qt.DashLine))
            p.drawLine(self.TIME_W, y + self.HOUR_H // 2, w - self.PAD_R, y + self.HOUR_H // 2)

        # Фильтруем события для текущего дня
        day_events = []
        for ev in self.events:
            if ev.start_dt.date() <= self.current_date <= ev.end_dt.date():
                day_events.append(ev)

        # Рисуем события
        self._event_rects = []
        x = self.TIME_W + 3
        cw = w - self.TIME_W - self.PAD_R - 6
        
        # Сортируем и группируем
        day_events.sort(key=lambda e: (e.start_dt, e.end_dt))
        for group in self._group_overlapping(day_events):
            seg = cw // len(group)
            for idx, ev in enumerate(group):
                start_time, end_time = self._get_display_time(ev, self.current_date)
                y1 = start_time.hour * self.HOUR_H + start_time.minute * self.HOUR_H // 60
                y2 = end_time.hour * self.HOUR_H + end_time.minute * self.HOUR_H // 60
                if y2 <= y1:
                    y2 = y1 + self.HOUR_H // 2
                rect = QRect(x + idx * seg, y1 + 1, seg - 2, y2 - y1 - 2)
                self._draw_block(p, rect, QColor(ev.color), ev, len(group))
                self._event_rects.append((rect, ev))

        # Рисуем текущее время
        if self.current_date == date.today():
            now = datetime.now()
            ny = now.hour * self.HOUR_H + now.minute * self.HOUR_H // 60
            p.setPen(QPen(QColor(Colors.RED), 2))
            p.drawLine(self.TIME_W - 4, ny, w - self.PAD_R, ny)
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self.TIME_W - 8, ny - 4, 8, 8)
        p.end()

    def _group_overlapping(self, events):
        if not events:
            return []
        evs = sorted(events, key=lambda e: (e.start_dt, e.end_dt))
        groups, cur = [], [evs[0]]
        for ev in evs[1:]:
            if any(not (ev.start_dt >= g.end_dt or ev.end_dt <= g.start_dt) for g in cur):
                cur.append(ev)
            else:
                groups.append(cur)
                cur = [ev]
        groups.append(cur)
        return groups

    def resizeEvent(self, e):
        self.update()
        super().resizeEvent(e)


# ─────────────────────────────────────────────
# WEEK VIEW
# ─────────────────────────────────────────────

class WeekView(QWidget):
    event_changed = pyqtSignal()
    HOUR_H = 56
    TIME_W = 52
    DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]  # Добавлены Сб и Вс

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_date = date.today()
        self._active_ids = None
        self._build_ui()
        self.refresh()

    def set_active_ids(self, ids):
        self._active_ids = ids
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._canvas.update)
        self._timer.start(60000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._header_bar = WeekHeaderBar(self.HOUR_H, self.TIME_W, self.DAY_NAMES)
        layout.addWidget(self._header_bar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._canvas = WeekCanvas(self.db, self.HOUR_H, self.TIME_W)
        self._canvas.event_clicked.connect(self._on_event_click)
        self._canvas.slot_double_clicked.connect(self._on_slot_dblclick)
        self._canvas.event_moved.connect(self._on_event_moved)
        self._canvas.event_resized.connect(self._on_event_resized)
        self._canvas.width_changed.connect(self._header_bar.set_canvas_width)
        scroll.setWidget(self._canvas)
        layout.addWidget(scroll, 1)
        QTimer.singleShot(120, lambda: scroll.verticalScrollBar().setValue(
            max(0, 7 * self.HOUR_H - 20)
        ))

    def _on_event_click(self, ev):
        dlg = EventDialog(self, db=self.db, event=ev)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            db_update_event(self.db, dlg.result_event)
        elif result == 2:
            db_delete_event(self.db, ev.id)
        if result in (QDialog.Accepted, 2):
            self.refresh()
            self.event_changed.emit()

    def _on_event_moved(self, event, new_start_time, new_end_time):
        """Обработчик перемещения события"""
        db_update_event(self.db, event)
        self.refresh()
        self.event_changed.emit()

    def _on_event_resized(self, event, new_start_time, new_end_time):
        """Обработчик изменения размера события"""
        db_update_event(self.db, event)
        self.refresh()
        self.event_changed.emit()

    def _on_slot_dblclick(self, d, t):
        dlg = EventDialog(self, db=self.db, preset_date=d, preset_time=t)
        if dlg.exec_() == QDialog.Accepted:
            db_add_event(self.db, dlg.result_event)
            self.refresh()
            self.event_changed.emit()

    def refresh(self):
        # Находим понедельник текущей недели
        monday = self.current_date - timedelta(days=self.current_date.weekday())
        # Создаем список из 7 дней (Пн, Вт, Ср, Чт, Пт, Сб, Вс)
        days = [monday + timedelta(days=i) for i in range(7)]
        events = db_get_events_by_date_range(
            self.db,
            datetime.combine(days[0], datetime.min.time()),
            datetime.combine(days[-1], datetime.max.time()),
            active_ids=self._active_ids
        )
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
        sunday = monday + timedelta(days=6)
        months = ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        if monday.month == sunday.month:
            return f"{monday.day}–{sunday.day} {months[sunday.month-1]} {sunday.year}"
        return (f"{monday.day} {months[monday.month-1]} – "
                f"{sunday.day} {months[sunday.month-1]} {sunday.year}")


class WeekHeaderBar(QWidget):
    def __init__(self, hour_h, time_w, day_names):
        super().__init__()
        self.hour_h = hour_h
        self.time_w = time_w
        self.day_names = day_names
        self.days = []
        self._canvas_width = 0
        self.setFixedHeight(30)
        self.setStyleSheet(
            f"background:{Colors.SECONDARY_BG}; border-bottom:1px solid {Colors.SEPARATOR};"
        )

    def set_canvas_width(self, w):
        self._canvas_width = w
        self.update()
        
    def set_days(self, days):
        self.days = days
        self.update()

    def paintEvent(self, e):
        if not self.days:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self._canvas_width if self._canvas_width > 0 else self.width()
        col_w = (w - self.time_w) / 7
        today = date.today()
        
        p.fillRect(0, 0, self.width(), self.height(), QColor(Colors.SECONDARY_BG))
        
        for i, d in enumerate(self.days):
            x = int(self.time_w + i * col_w)
            # Рисуем вертикальную линию
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(x, 0, x, self.height())
            
            # Определяем цвет текста
            is_weekend = (i == 5 or i == 6)
            if d == today:
                p.setPen(QColor(Colors.RED))
            elif is_weekend:
                p.setPen(QColor(Colors.WEEKEND))
            else:
                p.setPen(QColor(Colors.SECONDARY_TEXT))
            
            p.setFont(QFont("Helvetica Neue", 10))
            # Рисуем текст по центру ячейки
            text_rect = QRect(x, 0, int(col_w), self.height())
            p.drawText(text_rect, Qt.AlignCenter, f"{self.day_names[i]} {d.day}")
        
        # Рисуем последнюю линию
        last_x = int(self.time_w + 7 * col_w)
        p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
        p.drawLine(last_x, 0, last_x, self.height())
        
        p.end()


class WeekCanvas(QWidget):
    event_clicked       = pyqtSignal(object)
    slot_double_clicked = pyqtSignal(date, QTime)
    event_moved         = pyqtSignal(object, QTime, QTime)
    event_resized       = pyqtSignal(object, QTime, QTime)
    width_changed       = pyqtSignal(int)
    RESIZE_MARGIN = 10

    def __init__(self, db, hour_h, time_w):
        super().__init__()
        self.db = db
        self.HOUR_H = hour_h
        self.TIME_W = time_w
        self.days = []
        self.events = []  # Оригинальные события
        self._event_rects = []
        self.setMinimumHeight(24 * hour_h)
        self.setMouseTracking(True)
        
        # Для перемещения
        self.dragging_event = None
        self.drag_start_y = None
        self.drag_start_x = None
        self.drag_original_start = None
        self.drag_original_end = None
        self.drag_original_day = None
        self.drag_original_start_minutes = None
        self.drag_current_day = None
        self.drag_start_col = None       # колонка, с которой начался drag (по клику)
        self.drag_event_day_offset = None  # смещение дня начала события от days[0]
        
        # Для изменения размера
        self.resizing_event = None
        self.resizing_edge = None
        self.resize_start_y = None
        self.resize_original_start = None
        self.resize_original_end = None
        
        # Выделенное событие
        self.selected_event = None
        self.hover_edge = None

    def set_data(self, days, events):
        self.days = days
        self.events = events  # Сохраняем оригинальные события
        self._event_rects = []
        self.selected_event = None
        self.hover_edge = None
        self.update()

    def _get_display_time(self, ev, day):
        """Получить время отображения события для конкретного дня"""
        if day == ev.start_dt.date():
            start_time = ev.start_dt
        else:
            start_time = datetime(day.year, day.month, day.day, 0, 0)
        
        if day == ev.end_dt.date():
            end_time = ev.end_dt
        else:
            end_time = datetime(day.year, day.month, day.day, 23, 59)
        
        return start_time, end_time

    def _get_event_at_pos(self, pos):
        """Найти событие по позиции мыши"""
        for rect, (ev, day) in self._event_rects:
            if rect.contains(pos):
                return rect, ev
        return None, None

    def _get_resize_edge(self, rect, pos):
        if abs(pos.y() - rect.y()) <= self.RESIZE_MARGIN:
            return 'top'
        if abs(pos.y() - (rect.y() + rect.height())) <= self.RESIZE_MARGIN:
            return 'bottom'
        return None

    def _get_day_and_minutes_from_pos(self, pos):
        """Получить день и минуты по позиции мыши"""
        if not self.days:
            return None, None
        
        col_w = (self.width() - self.TIME_W) / 7  # Изменено с 5 на 7
        col = int((pos.x() - self.TIME_W) / col_w)
        
        if 0 <= col < len(self.days):
            y = pos.y()
            minutes = int(y / self.HOUR_H * 60)
            minutes = max(0, min(minutes, 23 * 60 + 45))
            minutes = (minutes // 15) * 15
            return self.days[col], minutes
        return None, None
    
    def _get_col_from_x(self, x):
        """Получить индекс колонки по X координате"""
        if not self.days:
            return -1
        col_w = (self.width() - self.TIME_W) / 7
        col = int((x - self.TIME_W) / col_w)
        if 0 <= col < len(self.days):
            return col
        return -1

    def _update_event_position(self, event, new_day, new_start_minutes):
        """Обновить позицию события на новый день и время с фиксацией 15 минут"""
        duration = int((event.end_dt - event.start_dt).total_seconds()) // 60
        
        # Округляем начальное время до 15 минут
        new_start_minutes = round(new_start_minutes / 15) * 15
        
        # Нормализуем минуты (может быть больше 1439 или меньше 0)
        days_offset = new_start_minutes // (24 * 60)
        new_start_minutes = new_start_minutes % (24 * 60)
        
        if new_start_minutes < 0:
            new_start_minutes += 24 * 60
            days_offset -= 1
        
        new_hour = new_start_minutes // 60
        new_minute = new_start_minutes % 60
        
        # Вычисляем новую дату (с учетом перехода между днями)
        final_day = new_day + timedelta(days=days_offset)
        
        new_start_dt = datetime(
            final_day.year, final_day.month, final_day.day,
            new_hour, new_minute
        )
        new_end_dt = new_start_dt + timedelta(minutes=duration)
        
        event.start_dt = new_start_dt
        event.end_dt = new_end_dt
        self.update()
        return True

    def mouseMoveEvent(self, e):
        rect, ev = self._get_event_at_pos(e.pos())
        
        if rect and ev and not self.dragging_event:
            edge = self._get_resize_edge(rect, e.pos())
            if edge == 'top' or edge == 'bottom':
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        elif not self.dragging_event:
            self.setCursor(Qt.ArrowCursor)
        
        if self.resizing_event and self.resize_start_y is not None:
            delta_y = e.pos().y() - self.resize_start_y
            delta_minutes = int(delta_y / self.HOUR_H * 60)
            
            if self.resizing_edge == 'top':
                new_start = self.resize_original_start + timedelta(minutes=delta_minutes)
                rounded_minutes = round(new_start.minute / 15) * 15
                if rounded_minutes >= 60:
                    new_start = new_start + timedelta(hours=1)
                    new_start = new_start.replace(minute=0)
                else:
                    new_start = new_start.replace(minute=rounded_minutes)

                min_start = datetime(new_start.year, new_start.month, new_start.day, 0, 0)
                max_start = self.resize_original_end - timedelta(minutes=15)
                if new_start < min_start:
                    new_start = min_start
                if new_start > max_start:
                    new_start = max_start

                self.resizing_event.start_dt = new_start
                self.update()

            elif self.resizing_edge == 'bottom':
                new_end = self.resize_original_end + timedelta(minutes=delta_minutes)
                rounded_minutes = round(new_end.minute / 15) * 15
                if rounded_minutes >= 60:
                    new_end = new_end + timedelta(hours=1)
                    new_end = new_end.replace(minute=0)
                else:
                    new_end = new_end.replace(minute=rounded_minutes)

                max_end = datetime(new_end.year, new_end.month, new_end.day, 23, 59)
                min_end = self.resize_original_start + timedelta(minutes=15)
                if new_end > max_end:
                    new_end = max_end
                if new_end < min_end:
                    new_end = min_end

                self.resizing_event.end_dt = new_end
                self.update()

        elif self.dragging_event and self.drag_start_y is not None:
            current_x = e.pos().x()
            current_y = e.pos().y()
            current_col = self._get_col_from_x(current_x)

            if current_col >= 0:
                # Вычисляем целевую колонку: смещение относительно колонки клика +
                # исходный день начала события. Это исключает прыжок при клике
                # в середину многодневного события.
                col_delta = current_col - self.drag_start_col
                new_col = max(0, min(self.drag_event_day_offset + col_delta, len(self.days) - 1))
                self.drag_current_day = self.days[new_col]

                delta_y = current_y - self.drag_start_y
                delta_minutes = int(delta_y / self.HOUR_H * 60)
                new_start_minutes = self.drag_original_start_minutes + delta_minutes
                self._update_event_position(
                    self.dragging_event,
                    self.drag_current_day,
                    new_start_minutes
                )

        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            rect, ev = self._get_event_at_pos(e.pos())
            
            if rect and ev:
                edge = self._get_resize_edge(rect, e.pos())
                
                if edge:
                    self.resizing_event = ev
                    self.resizing_edge = edge
                    self.resize_start_y = e.pos().y()
                    self.resize_original_start = ev.start_dt
                    self.resize_original_end = ev.end_dt
                    self.selected_event = ev
                    self.update()
                    return
                else:
                    self.dragging_event = ev
                    self.drag_start_y = e.pos().y()
                    self.drag_start_x = e.pos().x()
                    self.drag_original_start = ev.start_dt
                    self.drag_original_end = ev.end_dt
                    self.drag_original_day = ev.start_dt.date()
                    self.drag_original_start_minutes = ev.start_dt.hour * 60 + ev.start_dt.minute
                    self.drag_current_day = ev.start_dt.date()
                    # Запоминаем колонку клика и смещение дня начала события
                    click_col = self._get_col_from_x(e.pos().x())
                    self.drag_start_col = click_col if click_col >= 0 else 0
                    self.drag_event_day_offset = (
                        (ev.start_dt.date() - self.days[0]).days if self.days else 0
                    )
                    self.selected_event = ev
                    self.update()
                    return
            
            if self.selected_event:
                self.selected_event = None
                self.update()
        
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self.dragging_event and self.drag_start_y is not None:
            if (self.dragging_event.start_dt != self.drag_original_start or 
                self.dragging_event.end_dt != self.drag_original_end):
                self.event_moved.emit(
                    self.dragging_event,
                    self.dragging_event.start_dt.time(),
                    self.dragging_event.end_dt.time()
                )
        
        if self.resizing_event and self.resize_start_y is not None:
            if (self.resizing_event.start_dt != self.resize_original_start or 
                self.resizing_event.end_dt != self.resize_original_end):
                self.event_resized.emit(
                    self.resizing_event,
                    self.resizing_event.start_dt.time(),
                    self.resizing_event.end_dt.time()
                )
        
        self.dragging_event = None
        self.drag_start_y = None
        self.drag_start_x = None
        self.drag_original_start = None
        self.drag_original_end = None
        self.drag_original_day = None
        self.drag_original_start_minutes = None
        self.drag_current_day = None
        self.drag_start_col = None
        self.drag_event_day_offset = None
        self.resizing_event = None
        self.resizing_edge = None
        self.resize_start_y = None
        self.resize_original_start = None
        self.resize_original_end = None

        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        rect, ev = self._get_event_at_pos(e.pos())
        if rect and ev:
            self.event_clicked.emit(ev)
            return
        
        day, minutes = self._get_day_and_minutes_from_pos(e.pos())
        if day and minutes is not None:
            hour = minutes // 60
            minute = minutes % 60
            self.slot_double_clicked.emit(day, QTime(hour, minute))

    def _draw_block(self, p, rect, color, ev, gsz):
        is_selected = (self.selected_event and self.selected_event.id == ev.id)
        is_dragging = (self.dragging_event and self.dragging_event.id == ev.id)
        
        if is_selected or is_dragging:
            light = QColor(color)
            light.setAlpha(80 if is_dragging else 60)
            p.setBrush(QBrush(light))
            p.setPen(QPen(color, 2))
        else:
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
        f2 = QFont("Helvetica Neue", 10)
        p.setFont(f2)
        tr = rect.adjusted(8, 3, -3, -3)
        fm = QFontMetrics(f2)
        avail = rect.width() - 11
        time_s = ev.start_dt.strftime('%H:%M')
        if rect.height() > 28:
            title = fm.elidedText(ev.title, Qt.ElideRight, avail) if gsz <= 2 \
                    else (ev.title[:10] + "..." if len(ev.title) > 10 else ev.title)
            p.drawText(tr, Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                       f"{title}\n{time_s}")
        else:
            p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft,
                       fm.elidedText(f"{ev.title} {time_s}", Qt.ElideRight, avail))

    def paintEvent(self, e):
        if not self.days:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        col_w = (w - self.TIME_W) / 7
        today = date.today()
        
        p.fillRect(0, 0, w, self.height(), QColor(Colors.BG))

        # СНАЧАЛА РИСУЕМ ПОДСВЕТКУ ТЕКУЩЕГО ДНЯ (под линиями)
        if today in self.days:
            col = self.days.index(today)
            x = int(self.TIME_W + col * col_w)
            p.fillRect(x, 0, int(col_w), self.height(), QColor(Colors.ACCENT_LIGHT))

        # ПОТОМ РИСУЕМ СЕТКУ (поверх подсветки)
        for hour in range(24):
            y = hour * self.HOUR_H
            p.setPen(QColor(Colors.SECONDARY_TEXT))
            p.setFont(QFont("Helvetica Neue", 10))
            p.drawText(0, y, self.TIME_W - 6, self.HOUR_H,
                       Qt.AlignRight | Qt.AlignTop, f"{hour:02d}:00")
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(self.TIME_W, y, w, y)
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5, Qt.DashLine))
            p.drawLine(self.TIME_W, y + self.HOUR_H // 2, w, y + self.HOUR_H // 2)

        # Рисуем вертикальные линии для каждого дня
        for i in range(8):  # 8 линий для 7 колонок
            x = int(self.TIME_W + i * col_w)
            p.setPen(QPen(QColor(Colors.SEPARATOR), 0.5))
            p.drawLine(x, 0, x, self.height())

        # Рисуем события
        self._event_rects = []
        
        for col, day in enumerate(self.days):
            # Собираем события для этого дня
            day_events = []
            for ev in self.events:
                if ev.start_dt.date() <= day <= ev.end_dt.date():
                    day_events.append(ev)
            
            if not day_events:
                continue
            
            # Вычисляем позицию для этого дня
            x = int(self.TIME_W + col * col_w) + 3
            cw = int(col_w) - 6
            
            if cw <= 0:
                continue
            
            # Сортируем и группируем пересекающиеся события
            day_events.sort(key=lambda e: (e.start_dt, e.end_dt))
            for group in self._group_overlapping(day_events):
                seg = cw // len(group)
                if seg <= 0:
                    seg = cw
                for idx, ev in enumerate(group):
                    start_time, end_time = self._get_display_time(ev, day)
                    y1 = start_time.hour * self.HOUR_H + start_time.minute * self.HOUR_H // 60
                    y2 = end_time.hour * self.HOUR_H + end_time.minute * self.HOUR_H // 60
                    if y2 <= y1:
                        y2 = y1 + self.HOUR_H // 2
                    
                    # Ограничиваем y2 в пределах видимой области
                    y2 = min(y2, self.height() - 2)
                    
                    rect = QRect(x + idx * seg, y1 + 1, seg - 2, y2 - y1 - 2)
                    if rect.width() > 0 and rect.height() > 0:
                        self._draw_block(p, rect, QColor(ev.color), ev, len(group))
                        self._event_rects.append((rect, (ev, day)))

        # Рисуем текущее время (поверх всего)
        if today in self.days:
            now = datetime.now()
            ny = now.hour * self.HOUR_H + now.minute * self.HOUR_H // 60
            col = self.days.index(today)
            lx = int(self.TIME_W + col * col_w)
            rx = int(self.TIME_W + (col + 1) * col_w)
            
            # Красная линия текущего времени
            p.setPen(QPen(QColor(Colors.RED), 2))
            p.drawLine(lx, ny, rx, ny)
            
            # Красный кружок слева
            p.setBrush(QBrush(QColor(Colors.RED)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(lx - 4, ny - 4, 8, 8)
        p.end()

    def _group_overlapping(self, events):
        if not events:
            return []
        evs = sorted(events, key=lambda e: (e.start_dt, e.end_dt))
        groups, cur = [], [evs[0]]
        for ev in evs[1:]:
            if any(not (ev.start_dt >= g.end_dt or ev.end_dt <= g.start_dt) for g in cur):
                cur.append(ev)
            else:
                groups.append(cur)
                cur = [ev]
        groups.append(cur)
        return groups

    def resizeEvent(self, e):
        self.update()
        self.width_changed.emit(self.width())
        super().resizeEvent(e)


# ─────────────────────────────────────────────
# YEAR VIEW
# ─────────────────────────────────────────────

class YearView(QWidget):
    event_changed  = pyqtSignal()
    month_selected = pyqtSignal(date)
    MONTH_NAMES = ["Январь","Февраль","Март","Апрель","Май","Июнь",
                   "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]

    def __init__(self, db):
        super().__init__()
        self.db = db; self.current_date = date.today()
        self._active_ids = None
        self._build_ui(); self.refresh()

    def set_active_ids(self, ids):
        self._active_ids = ids
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet(f"background: {Colors.BG};")
        container = QWidget(); container.setStyleSheet(f"background: {Colors.BG};")
        cl = QVBoxLayout(container); cl.setContentsMargins(0,0,0,0)
        cl.setAlignment(Qt.AlignCenter)
        self._canvas = YearCanvas(self)
        self._canvas.month_clicked.connect(self.month_selected)
        cl.addWidget(self._canvas)
        scroll.setWidget(container); layout.addWidget(scroll)

    def refresh(self):
        y = self.current_date.year
        events = db_get_events_by_date_range(
            self.db, datetime(y,1,1), datetime(y,12,31,23,59,59),
            active_ids=self._active_ids
        )
        self._canvas.set_data(y, {e.start_dt.date() for e in events}, date.today())

    def go_prev(self):
        self.current_date = self.current_date.replace(year=self.current_date.year-1, day=1)
        self.refresh()
    def go_next(self):
        self.current_date = self.current_date.replace(year=self.current_date.year+1, day=1)
        self.refresh()
    def go_today(self): self.current_date = date.today(); self.refresh()
    def header_text(self): return str(self.current_date.year)


class YearCanvas(QWidget):
    month_clicked = pyqtSignal(date)
    COLS=4; DAY_LABELS=["П","В","С","Ч","П","С","В"]
    CW=220; CH=200; GAP=26; PAD=0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.year=date.today().year; self.event_dates=set()
        self.today=date.today(); self._month_rects=[]
        self.setFixedSize(
            self.PAD*2 + self.COLS*self.CW + (self.COLS-1)*self.GAP,
            self.PAD*2 + 3*self.CH + 2*self.GAP
        )

    def set_data(self, year, event_dates, today):
        self.year=year; self.event_dates=event_dates
        self.today=today; self._month_rects=[]; self.update()

    def mousePressEvent(self, e):
        for rect, m in self._month_rects:
            if rect.contains(e.pos()):
                self.month_clicked.emit(date(self.year, m, 1)); return

    def paintEvent(self, ev):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, self.width(), self.height(), QColor(Colors.BG))
        self._month_rects = []
        for m in range(12):
            row=m//self.COLS; col=m%self.COLS
            mx=self.PAD+col*(self.CW+self.GAP); my=self.PAD+row*(self.CH+self.GAP)
            self._month_rects.append((QRect(mx,my,self.CW,self.CH), m+1))
            is_cur = (self.year==self.today.year and m+1==self.today.month)
            p.setPen(QColor(Colors.RED if is_cur else Colors.PRIMARY_TEXT))
            p.setFont(QFont("Helvetica Neue", 10, QFont.DemiBold))
            p.drawText(mx+10, my+6, self.CW-20, 22,
                       Qt.AlignLeft|Qt.AlignVCenter, YearView.MONTH_NAMES[m])
            hy=my+30; dcw=self.CW/7; dch=(self.CH-34)/7
            p.setFont(QFont("Helvetica Neue", 10))
            for di, dl in enumerate(self.DAY_LABELS):
                p.setPen(QColor(Colors.RED if di>=5 else Colors.SECONDARY_TEXT))
                p.drawText(int(mx+di*dcw), hy, int(dcw), int(dch), Qt.AlignCenter, dl)
            first=date(self.year,m+1,1)
            gs=first-timedelta(days=first.weekday())
            for di in range(42):
                dr=di//7; dc=di%7
                d=gs+timedelta(days=di)
                dx=int(mx+dc*dcw); dy=int(hy+(dr+1)*dch)
                dw=int(dcw); dh=int(dch)
                if d==self.today:
                    cs=18; cx=dx+dw//2-cs//2; cy=dy+dh//2-cs//2
                    p.setBrush(QBrush(QColor(Colors.RED))); p.setPen(Qt.NoPen)
                    p.drawEllipse(cx,cy,cs,cs)
                    p.setPen(QColor("white"))
                    p.drawText(cx,cy,cs,cs,Qt.AlignCenter,str(d.day))
                else:
                    p.setPen(QColor(
                        Colors.WEEKEND if dc>=5 and d.month==m+1
                        else Colors.PRIMARY_TEXT if d.month==m+1
                        else Colors.SEPARATOR
                    ))
                    p.drawText(dx,dy,dw,dh,Qt.AlignCenter,str(d.day))
                if d in self.event_dates and d.month==m+1 and d!=self.today:
                    cx=dx+dw//2; cy=dy+dh-1
                    p.setBrush(QBrush(QColor(Colors.ACCENT))); p.setPen(Qt.NoPen)
                    p.drawEllipse(cx-2,cy-2,4,4)
        p.end()


# ─────────────────────────────────────────────
# LIST VIEW
# ─────────────────────────────────────────────

class ElidedLabel(QLabel):
    """QLabel, который всегда обрезает текст многоточием по своей ширине.
    minimumSizeHint возвращает нулевую ширину — layout может свободно сжимать
    виджет, а обрезка происходит в paintEvent с актуальной шириной."""

    def minimumSizeHint(self):
        h = super().minimumSizeHint().height()
        return QSize(0, h)

    def sizeHint(self):
        h = super().sizeHint().height()
        return QSize(0, h)

    def paintEvent(self, e):
        p = QPainter(self)
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self.text(), Qt.ElideRight, self.width() - 16)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, elided)
        p.end()


class EventRowWidget(QWidget):
    edit_requested = pyqtSignal(object)

    def __init__(self, ev, is_past):
        super().__init__()
        self.ev = ev
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build(is_past)

    def _build(self, is_past):
        layout = QHBoxLayout(self); layout.setContentsMargins(24, 0, 0, 0)
        dot = QLabel(); dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{self.ev.color}; border-radius:5px;")
        layout.addWidget(dot, 0, alignment=Qt.AlignVCenter)
        layout.addSpacing(6)
        tl = QLabel(f"{self.ev.start_dt.strftime('%H:%M')} – {self.ev.end_dt.strftime('%H:%M')}")
        tl.setFixedWidth(85)
        tl.setStyleSheet(f"color:{Colors.SECONDARY_TEXT}; font-size:13px; background:transparent;")
        layout.addWidget(tl, 0, alignment=Qt.AlignVCenter)
        layout.addSpacing(2)
        tc = Colors.SECONDARY_TEXT if is_past else Colors.PRIMARY_TEXT
        self.title_lbl = ElidedLabel(self.ev.title)
        self.title_lbl.setStyleSheet(
            f"color:{tc}; font-size:13px; background:transparent;"
            + ("text-decoration:line-through;" if is_past else "")
        )
        self.title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.title_lbl, 1)
        self.setStyleSheet("background:transparent;")

    def enterEvent(self, e): super().enterEvent(e); self.setStyleSheet(f"background:{Colors.ACCENT_LIGHT};")
    def leaveEvent(self, e): super().leaveEvent(e); self.setStyleSheet("background:transparent;")
    def mouseDoubleClickEvent(self, e): super().mouseDoubleClickEvent(e); self.edit_requested.emit(self.ev)


class ListView(QWidget):
    event_changed = pyqtSignal()
    MONTHS   = ["января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"]
    WEEKDAYS = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

    def __init__(self, db):
        super().__init__()
        self.db=db; self.current_date=date.today(); self._first_show=True
        self._active_ids = None
        self._build_ui(); self.refresh()

    def set_active_ids(self, ids):
        self._active_ids = ids
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            QTimer.singleShot(100, self.go_today); self._first_show=False

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget(); self._content.setStyleSheet(f"background:{Colors.BG};")
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(0,0,0,0); self._vbox.setSpacing(0)
        self._vbox.addStretch()
        self.scroll.setWidget(self._content); root.addWidget(self.scroll)

    def refresh(self):
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        events = db_get_all_events(self.db, active_ids=self._active_ids)
        groups = defaultdict(list)
        for ev in events: groups[ev.start_dt.date()].append(ev)

        today = date.today(); tomorrow = today + timedelta(days=1)
        if today not in groups: groups[today] = []

        idx = 0
        for d in sorted(groups.keys()):
            evs = groups[d]
            is_past = d < today
            label = ("Сегодня" if d==today else "Завтра" if d==tomorrow
                     else f"{self.WEEKDAYS[d.weekday()]}, {d.day} {self.MONTHS[d.month-1]} {d.year}")
            self._vbox.insertWidget(idx, self._make_header(label, is_past)); idx+=1
            if d==today and not evs:
                lbl = QLabel("Нет событий на сегодня")
                lbl.setStyleSheet(
                    f"color:{Colors.SECONDARY_TEXT}; font-size:12px;"
                    f"padding:8px 24px; background:transparent;"
                )
                self._vbox.insertWidget(idx, lbl); idx+=1
            else:
                for ev in evs:
                    row = EventRowWidget(ev, is_past)
                    row.edit_requested.connect(self._on_edit)
                    self._vbox.insertWidget(idx, row); idx+=1

    def _make_header(self, label, is_past):
        w = QWidget(); w.setFixedHeight(30)
        w.setStyleSheet(f"background:{Colors.SECONDARY_BG};")
        lay = QHBoxLayout(w); lay.setContentsMargins(24,0,24,0)
        color = Colors.RED if label=="Сегодня" else Colors.SECONDARY_TEXT if is_past else Colors.PRIMARY_TEXT
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{color}; font-size:13px; font-weight:600; background:transparent;")
        lay.addWidget(lbl); lay.addStretch()
        return w

    def _on_edit(self, ev):
        dlg = EventDialog(self, db=self.db, event=ev)
        result = dlg.exec_()
        if result == QDialog.Accepted: db_update_event(self.db, dlg.result_event)
        elif result == 2:              db_delete_event(self.db, ev.id)
        if result in (QDialog.Accepted, 2):
            self.refresh(); self.event_changed.emit()

    def go_prev(self):
        self._scroll_to_adjacent_date(forward=False)

    def go_next(self):
        self._scroll_to_adjacent_date(forward=True)

    def _scroll_to_adjacent_date(self, forward: bool):
        """Прокручивает к следующей/предыдущей дате относительно текущей видимой."""
        sb = self.scroll.verticalScrollBar()
        current_y = sb.value()
        headers = []
        for i in range(self._vbox.count()):
            item = self._vbox.itemAt(i)
            if item and item.widget():
                lbl = item.widget().findChild(QLabel)
                if lbl and item.widget().height() == 30:
                    y = item.widget().mapTo(self._content, QPoint(0, 0)).y()
                    headers.append(y)
        if not headers:
            return
        if forward:
            target = next((y for y in headers if y > current_y + 5), headers[-1])
        else:
            target = next((y for y in reversed(headers) if y < current_y - 5), headers[0])
        anim = QPropertyAnimation(sb, b"value")
        anim.setDuration(300)
        anim.setStartValue(sb.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim

    def go_today(self):
        for i in range(self._vbox.count()):
            item = self._vbox.itemAt(i)
            if item and item.widget():
                lbl = item.widget().findChild(QLabel)
                if lbl and lbl.text() == "Сегодня":
                    y_pos = item.widget().mapTo(self._content, QPoint(0,0)).y()
                    sb = self.scroll.verticalScrollBar()
                    anim = QPropertyAnimation(sb, b"value")
                    anim.setDuration(500); anim.setStartValue(sb.value())
                    anim.setEndValue(y_pos); anim.setEasingCurve(QEasingCurve.OutCubic)
                    anim.start(); self._anim = anim; return

    def header_text(self): return "Список событий"


# ─────────────────────────────────────────────
# CALENDAR MODULE
# ─────────────────────────────────────────────

class CalendarModule(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._active_ids = None
        self._build_ui()
        self._seed_if_empty()

    def set_active_ids(self, ids):
        self._active_ids = ids
        for v in [self.list_view, self.day_view, self.week_view,
                  self.month_view, self.year_view]:
            v.set_active_ids(ids)

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        top = QWidget(); top.setFixedHeight(32)
        top.setStyleSheet(f"background:{Colors.WHITE};")
        tl = QHBoxLayout(top); tl.setContentsMargins(16,0,16,0)
        self.segmented = SegmentedControl(["Список","День","Неделя","Месяц","Год"])
        self.segmented.tab_changed.connect(self._switch_view)
        tl.addStretch(); tl.addWidget(self.segmented); tl.addStretch()
        root.addWidget(top)

        self.navbar = NavBar()
        self.navbar.today_clicked.connect(self._go_today)
        self.navbar.prev_clicked.connect(self._go_prev)
        self.navbar.next_clicked.connect(self._go_next)
        self.navbar.add_clicked.connect(self._add_event)
        root.addWidget(self.navbar)

        self.stack = QStackedWidget()
        self.list_view  = ListView(self.db)
        self.day_view   = DayView(self.db)
        self.week_view  = WeekView(self.db)
        self.month_view = MonthView(self.db)
        self.year_view  = YearView(self.db)

        for v in [self.list_view, self.day_view, self.week_view,
                  self.month_view, self.year_view]:
            self.stack.addWidget(v)
            v.event_changed.connect(self._on_event_changed)

        self.month_view.day_clicked.connect(self._on_day_clicked)
        self.year_view.month_selected.connect(self._on_month_selected)
        root.addWidget(self.stack, 1)

        self.stack.setCurrentIndex(3)
        self._update_title()

    def _current_view(self): return self.stack.currentWidget()

    def _switch_view(self, idx):
        self.stack.setCurrentIndex(idx); self._update_title()

    def _update_title(self):
        v = self._current_view()
        if hasattr(v, 'header_text'):
            self.navbar.set_title(v.header_text())

    def _go_today(self): self._current_view().go_today(); self._update_title()
    def _go_prev(self):  self._current_view().go_prev();  self._update_title()
    def _go_next(self):  self._current_view().go_next();  self._update_title()

    def _on_day_clicked(self, d):
        self.day_view.current_date = d; self.day_view.refresh()
        self.stack.setCurrentIndex(1); self.segmented.set_active(1)
        self._update_title()

    def _on_month_selected(self, d):
        self.month_view.current_date = d; self.month_view.refresh()
        self.stack.setCurrentIndex(3); self.segmented.set_active(3)
        self._update_title()

    def _add_event(self):
        v = self._current_view()
        preset = getattr(v, 'current_date', date.today())
        if isinstance(preset, datetime): preset = preset.date()
        dlg = EventDialog(self, db=self.db, preset_date=preset)
        if dlg.exec_() == QDialog.Accepted:
            db_add_event(self.db, dlg.result_event)
            self._on_event_changed()

    def _on_event_changed(self):
        for v in [self.list_view, self.day_view, self.week_view,
                  self.month_view, self.year_view]:
            v.set_active_ids(self._active_ids)
        self._update_title()

    def _seed_if_empty(self):
        if db_count_events(self.db) > 0: return
        today = date.today()
        now = datetime.now().replace(second=0, microsecond=0)
        d1 = now + timedelta(days=1)
        d3 = now + timedelta(days=3)
        d5 = now + timedelta(days=5)
        for ev in [
            Event("Планёрка команды",
                  datetime(today.year, today.month, today.day, 9, 0),
                  datetime(today.year, today.month, today.day, 10, 0), "Работа"),
            Event("Обед с клиентом",
                  datetime(today.year, today.month, today.day, 12, 30),
                  datetime(today.year, today.month, today.day, 14, 0), "Важное"),
            Event("Дедлайн проекта",
                  d3.replace(hour=18, minute=0),
                  d3.replace(hour=19, minute=0),
                  "Важное"),
            Event("День рождения Ани",
                  d5.replace(hour=19, minute=0),
                  d5.replace(hour=22, minute=0),
                  "Личное"),
            Event("Код-ревью",
                  d1.replace(hour=15, minute=0),
                  d1.replace(hour=16, minute=30),
                  "Работа"),
        ]:
            db_add_event(self.db, ev)