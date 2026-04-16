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
        self._current_selected_id = None  # Для отслеживания выбранного календаря

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
        
        # Добавляем обработку кликов
        self._list.itemClicked.connect(self._on_item_click)
        self._list.itemDoubleClicked.connect(self._on_item_double_click)
        
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

        # Чекбокс
        checkbox = CalendarCheckBox(cat.color, checked)
        checkbox.toggled.connect(
            lambda state, cid=cat.id: self._on_toggle(cid, state)
        )
        layout.addWidget(checkbox)

        # Название календаря (кликабельно)
        lbl = QLabel(cat.name)
        lbl.setStyleSheet(
            f"color: {Colors.PRIMARY_TEXT}; font-size: 13px; background: transparent;"
        )
        lbl.setCursor(Qt.PointingHandCursor)
        layout.addWidget(lbl, 1)
        
        # Сохраняем данные в виджете
        w.setProperty("category_id", cat.id)
        w.setProperty("category_name", cat.name)
        w.setProperty("category_color", cat.color)
        w.setProperty("checkbox", checkbox)
        w.setProperty("label", lbl)
        
        return w

    def _on_toggle(self, cat_id: int, checked: bool):
        """Переключение видимости календаря"""
        if checked:
            self._active_ids.add(cat_id)
        else:
            self._active_ids.discard(cat_id)
        self.visibility_changed.emit()

    # ── Обработчики кликов ────────────────────

    def _on_item_click(self, item):
        """Одиночный клик - подсветка (галка не меняется)"""
        widget = self._list.itemWidget(item)
        if widget:
            cat_id = widget.property("category_id")
            
            # Снимаем подсветку со всех элементов
            for i in range(self._list.count()):
                other_item = self._list.item(i)
                other_widget = self._list.itemWidget(other_item)
                if other_widget:
                    other_widget.setStyleSheet("background: transparent;")
            
            # Подсвечиваем текущий элемент
            widget.setStyleSheet(f"background: {Colors.ACCENT_LIGHT}; border-radius: 4px;")
            self._current_selected_id = cat_id

    def _on_item_double_click(self, item):
        """Двойной клик - открыть окно редактирования (галка не меняется)"""
        widget = self._list.itemWidget(item)
        if widget:
            cat_id = widget.property("category_id")
            if cat_id:
                cat = self.db.category_manager.get_category_by_id(cat_id)
                if cat:
                    self._edit_calendar_with_delete(cat)

    def _edit_calendar_with_delete(self, cat):
        """Диалог редактирования с кнопкой удаления и выбором календаря для переноса"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Изменить календарь")
        dialog.setFixedWidth(350)
        dialog.setModal(True)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {Colors.BG}; border-radius: 12px; }}
            QLabel {{ color: {Colors.SECONDARY_TEXT}; font-size: 13px; font-weight: 600; }}
            QLineEdit, QComboBox {{
                background: {Colors.SECONDARY_BG}; border: 1px solid {Colors.SEPARATOR};
                border-radius: 6px; padding: 6px; font-size: 13px; color: {Colors.PRIMARY_TEXT};
            }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {Colors.ACCENT}; }}
            QPushButton {{
                border: none; border-radius: 6px; padding: 6px 16px; 
                font-size: 13px; font-weight: 600;
            }}
            QPushButton#save_btn {{
                background: {Colors.ACCENT}; color: white;
            }}
            QPushButton#save_btn:hover {{ background: #0063CC; }}
            QPushButton#delete_btn {{
                background: {Colors.RED}; color: white;
            }}
            QPushButton#delete_btn:hover {{ background: #CC0000; }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Поле названия
        layout.addWidget(QLabel("Название"))
        name_edit = QLineEdit(cat.name)
        name_edit.setPlaceholderText("Название календаря")
        layout.addWidget(name_edit)
        
        # Поле цвета
        layout.addWidget(QLabel("Цвет"))
        color_combo = QComboBox()
        for code, name in CategoryManager.PREDEFINED_COLORS:
            px = QPixmap(16, 16)
            px.fill(QColor(code))
            color_combo.addItem(QIcon(px), name, code)
        
        # Выбираем текущий цвет
        for i in range(color_combo.count()):
            if color_combo.itemData(i) == cat.color:
                color_combo.setCurrentIndex(i)
                break
        layout.addWidget(color_combo)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        delete_btn = QPushButton("Удалить")
        delete_btn.setObjectName("delete_btn")
        delete_btn.setFixedSize(100, 32)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("save_btn")
        save_btn.setFixedSize(100, 32)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # Обработчики
        def on_save():
            new_name = name_edit.text().strip()
            if not new_name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название календаря")
                return
            new_color = color_combo.currentData()
            if self.db.category_manager.update_category(cat.id, new_name, new_color):
                dialog.accept()
                self.refresh()
                self.calendars_changed.emit()
            else:
                QMessageBox.warning(dialog, "Ошибка", "Календарь с таким названием уже существует")
        
        def on_delete():
            # Получаем все календари кроме удаляемого
            other_calendars = [c for c in self.db.category_manager.get_all_categories() if c.id != cat.id]
            
            if not other_calendars:
                # Если нет других календарей, показываем предупреждение с выбором
                reply = QMessageBox.question(
                    dialog,
                    "Подтверждение удаления",
                    f'Нет других календарей для переноса событий.\n\nВсе события календаря "{cat.name}" будут УДАЛЕНЫ безвозвратно.\n\nВы уверены, что хотите удалить календарь?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Получаем все события этого календаря
                    from modules.calendar import db_get_all_events
                    events = db_get_all_events(self.db)
                    cat_events = [e for e in events if e.category_id == cat.id]
                    event_count = len(cat_events)
                    
                    # Удаляем события этого календаря
                    self.db.conn.execute("DELETE FROM events WHERE category = ?", (cat.id,))
                    
                    # Удаляем календарь
                    self.db.conn.execute("DELETE FROM categories WHERE id = ?", (cat.id,))
                    self.db.conn.commit()
                    
                    # Обновляем активные ID
                    self._active_ids.discard(cat.id)
                    
                    dialog.accept()
                    
                    # Обновляем интерфейс
                    self.refresh()
                    self.calendars_changed.emit()
                    
                    # Показываем сообщение об успешном удалении
                    QMessageBox.information(
                        self, 
                        "Календарь удален", 
                        f'Календарь "{cat.name}" удален.\n{event_count} событий удалены безвозвратно.'
                    )
                return
            
            # Если есть другие календари, показываем диалог выбора
            transfer_dialog = QDialog(dialog)
            transfer_dialog.setWindowTitle("Перенос событий")
            transfer_dialog.setFixedWidth(350)
            transfer_dialog.setModal(True)
            transfer_dialog.setStyleSheet(f"""
                QDialog {{ background: {Colors.BG}; border-radius: 12px; }}
                QLabel {{ color: {Colors.SECONDARY_TEXT}; font-size: 13px; font-weight: 600; }}
                QComboBox {{
                    background: {Colors.SECONDARY_BG}; border: 1px solid {Colors.SEPARATOR};
                    border-radius: 6px; padding: 6px; font-size: 13px; color: {Colors.PRIMARY_TEXT};
                }}
                QPushButton {{
                    border: none; border-radius: 6px; padding: 6px 16px; 
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton#cancel_btn {{
                    background: {Colors.SECONDARY_BG}; color: {Colors.PRIMARY_TEXT};
                }}
                QPushButton#cancel_btn:hover {{ background: {Colors.SEPARATOR}; }}
                QPushButton#confirm_btn {{
                    background: {Colors.ACCENT}; color: white;
                }}
                QPushButton#confirm_btn:hover {{ background: #0063CC; }}
            """)
            
            transfer_layout = QVBoxLayout(transfer_dialog)
            transfer_layout.setSpacing(12)
            transfer_layout.setContentsMargins(20, 20, 20, 20)
            
            # Информация о количестве событий
            from modules.calendar import db_get_all_events
            events = db_get_all_events(self.db)
            cat_events = [e for e in events if e.category_id == cat.id]
            event_count = len(cat_events)
            
            info_label = QLabel(f'Календарь "{cat.name}" содержит {event_count} событий.')
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #666; font-weight: normal; font-size: 12px;")
            transfer_layout.addWidget(info_label)
            
            transfer_layout.addWidget(QLabel("Перенести события в:"))
            
            # Выпадающий список календарей
            target_combo = QComboBox()
            for c in other_calendars:
                px = QPixmap(16, 16)
                px.fill(QColor(c.color))
                target_combo.addItem(QIcon(px), c.name, c.id)
            transfer_layout.addWidget(target_combo)
            
            # Кнопки
            transfer_btn_layout = QHBoxLayout()
            transfer_btn_layout.addStretch()
            
            cancel_transfer_btn = QPushButton("Отмена")
            cancel_transfer_btn.setObjectName("cancel_btn")
            cancel_transfer_btn.setFixedSize(100, 32)
            transfer_btn_layout.addWidget(cancel_transfer_btn)
            
            confirm_delete_btn = QPushButton("Удалить")
            confirm_delete_btn.setObjectName("confirm_btn")
            confirm_delete_btn.setFixedSize(100, 32)
            transfer_btn_layout.addWidget(confirm_delete_btn)
            
            transfer_layout.addLayout(transfer_btn_layout)
            
            def do_delete():
                target_id = target_combo.currentData()
                target_name = target_combo.currentText()
                
                # Переносим события
                self.db.conn.execute(
                    "UPDATE events SET category = ? WHERE category = ?",
                    (target_id, cat.id)
                )
                self.db.conn.commit()
                
                # Удаляем календарь
                self.db.conn.execute("DELETE FROM categories WHERE id = ?", (cat.id,))
                self.db.conn.commit()
                
                # Обновляем активные ID
                self._active_ids.discard(cat.id)
                self._active_ids.add(target_id)
                
                transfer_dialog.accept()
                dialog.accept()
                
                # Обновляем интерфейс
                self.refresh()
                self.calendars_changed.emit()
                
                # Показываем сообщение об успешном удалении
                QMessageBox.information(
                    self, 
                    "Календарь удален", 
                    f'Календарь "{cat.name}" удален.\n{event_count} событий перенесены в "{target_name}".'
                )
            
            confirm_delete_btn.clicked.connect(do_delete)
            cancel_transfer_btn.clicked.connect(transfer_dialog.reject)
            
            transfer_dialog.exec_()
        
        save_btn.clicked.connect(on_save)
        delete_btn.clicked.connect(on_delete)
        
        dialog.exec_()

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