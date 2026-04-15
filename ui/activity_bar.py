from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from core.styles import Colors


class ActivityBar(QWidget):
    """Узкая панель слева с иконками-секциями (аналог VS Code Activity Bar).
    При клике на иконку открывается/закрывается соответствующая панель."""

    section_toggled = pyqtSignal(str, bool)  # (section_id, is_open)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(49)   # 48px + 1px разделитель
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    # ── Построение UI ──────────────────────────────────────

    def _build_ui(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background: {Colors.ACTIVITY_BAR};")
        self._inner.setFixedWidth(48)

        self._vbox = QVBoxLayout(self._inner)
        self._vbox.setContentsMargins(4, 8, 4, 8)
        self._vbox.setSpacing(4)
        self._vbox.setAlignment(Qt.AlignTop)

        # Начальная секция — календари
        self.add_section("calendars", "☰", "Мои календари", checked=True)

        self._vbox.addStretch()

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: #C8C8C8; border: none;")

        h.addWidget(self._inner)
        h.addWidget(line)

    # ── Публичный API ───────────────────────────────────────

    def add_section(self, section_id: str, icon: str, tooltip: str, checked=False):
        """Добавляет новую иконку-секцию в панель."""
        btn = QPushButton(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setCheckable(True)
        btn.setChecked(checked)
        self._apply_style(btn, checked)
        btn.toggled.connect(lambda state, sid=section_id, b=btn: self._on_toggled(sid, b, state))
        self._buttons[section_id] = btn
        # Вставляем перед stretch-ом (последний элемент)
        insert_pos = max(0, self._vbox.count() - 1)
        self._vbox.insertWidget(insert_pos, btn)

    def set_section_open(self, section_id: str, is_open: bool):
        """Синхронизирует визуальное состояние кнопки извне (без эмита сигнала)."""
        btn = self._buttons.get(section_id)
        if btn:
            btn.blockSignals(True)
            btn.setChecked(is_open)
            self._apply_style(btn, is_open)
            btn.blockSignals(False)

    # ── Внутренняя логика ───────────────────────────────────

    def _on_toggled(self, section_id: str, btn: QPushButton, checked: bool):
        self._apply_style(btn, checked)
        # Если открываем новую секцию — снимаем отметку с остальных
        if checked:
            for sid, b in self._buttons.items():
                if sid != section_id and b.isChecked():
                    b.blockSignals(True)
                    b.setChecked(False)
                    self._apply_style(b, False)
                    b.blockSignals(False)
        self.section_toggled.emit(section_id, checked)

    def _apply_style(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.WHITE};
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    color: {Colors.ACCENT};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    color: {Colors.PRIMARY_TEXT};
                }}
                QPushButton:hover {{
                    background: rgba(0, 0, 0, 0.08);
                }}
            """)
