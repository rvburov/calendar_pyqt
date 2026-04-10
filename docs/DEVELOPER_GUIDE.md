# Руководство разработчика

Документация для разработчиков, желающих модифицировать, расширять или поддерживать приложение-календарь.

## 📋 Содержание

1. [Архитектура приложения](#архитектура-приложения)
2. [Модели данных](#модели-данных)
3. [Работа с базой данных](#работа-с-базой-данных)
4. [Создание представлений](#создание-представлений)
5. [Система категорий](#система-категорий)
6. [Стилизация](#стилизация)
7. [Добавление функциональности](#добавление-функциональности)
8. [Тестирование](#тестирование)
9. [Сборка и дистрибуция](#сборка-и-дистрибуция)

## 🏗️ Архитектура приложения

### Общая структура

```
┌─────────────────────────────────────────────────────┐
│                    MainWindow                       │
│  ┌──────────┬────────────────────────────────────┐  │
│  │Activity  │         Top Bar (Segmented)        │  │
│  │  Bar     ├────────────────────────────────────┤  │
│  │          │            NavBar                  │  │
│  │          ├────────────────────────────────────┤  │
│  │          │         Section Stack              │  │
│  │          │  ┌──────────────────────────────┐  │  │
│  │          │  │   Calendar Stack (5 views)   │  │  │
│  │          │  └──────────────────────────────┘  │  │
│  │          │  ┌──────────────────────────────┐  │  │
│  │          │  │   Tasks Placeholder          │  │  │
│  │          │  └──────────────────────────────┘  │  │
│  └──────────┴────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Ответственность |
|-----------|-----------------|
| `DatabaseManager` | Все операции с SQLite |
| `CategoryManager` | Управление категориями |
| `EventDialog` | Создание/редактирование событий |
| `*View` классы | Отображение данных (5 вариантов) |
| `ActivityBar` | Переключение между секциями |
| `NavBar` | Навигация и действия |
| `SegmentedControl` | Переключение режимов просмотра |

## 📊 Модели данных

### Event

```python
@dataclass
class Event:
    title: str                     # Название (обязательно)
    start_dt: datetime             # Начало
    end_dt: datetime               # Конец
    category: str = "Личное"       # Имя категории
    description: str = ""          # Описание
    id: Optional[int] = None       # ID в БД
    category_id: Optional[int] = None  # ID категории
    _db: Optional[object] = None   # Ссылка на БД для цвета
```

**Важно**: Поле `_db` необходимо для динамического получения цвета категории. Всегда передавайте его при создании события из БД.

### Category

```python
class Category:
    def __init__(self, name: str, color: str, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.color = color
```

## 🗄️ Работа с базой данных

### DatabaseManager API

```python
# Инициализация
db = DatabaseManager()  # Автоматически создаёт папку AppData или локальную

# CRUD операции
event = db.add_event(event_obj)           # Добавить
db.update_event(event_obj)                # Обновить
db.delete_event(event_id)                 # Удалить
events = db.get_events_by_date_range(start, end)  # Получить диапазон
events = db.get_all_events()              # Все события

# Вспомогательные
count = db.count()                        # Количество
```

### Кастомный путь к БД

По умолчанию:
- **.exe версия**: `%APPDATA%/MyCalendar/calendar.db`
- **.py версия**: Папка со скриптом

Для изменения пути измените в `DatabaseManager.__init__`:

```python
db_path = os.path.join("your/custom/path", "calendar.db")
```

### Схема БД

```sql
-- События
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_dt    TEXT NOT NULL,  -- ISO формат: "2024-01-15T09:00:00"
    end_dt      TEXT NOT NULL,
    category    INTEGER DEFAULT 1
);

-- Категории
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    color       TEXT NOT NULL      -- HEX: "#007AFF"
);
```

## 🎨 Создание представлений

### Базовый шаблон View

Каждое представление должно наследовать `QWidget` и реализовывать:

```python
class MyView(QWidget):
    event_changed = pyqtSignal()  # Сигнал об изменении данных
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_date = date.today()  # Текущая дата для навигации
        self._build_ui()
        
    def refresh(self):
        """Обновить отображение данных"""
        pass
        
    def go_prev(self):
        """Перейти на предыдущий период"""
        pass
        
    def go_next(self):
        """Перейти на следующий период"""
        pass
        
    def go_today(self):
        """Перейти к сегодняшнему дню"""
        pass
        
    def header_text(self) -> str:
        """Текст для отображения в NavBar"""
        return "Название представления"
```

### Добавление нового View в MainWindow

```python
# 1. Создайте экземпляр
self.my_view = MyView(self.db)
self.my_view.event_changed.connect(self._on_event_changed)

# 2. Добавьте в stack (порядок: 0-Список, 1-День, 2-Неделя, 3-Месяц, 4-Год)
self.stack.addWidget(self.my_view)

# 3. Обновите SegmentedControl
self.segmented = SegmentedControl(["Список", "День", "Неделя", "Месяц", "Год", "МойРежим"])
```

## 🏷️ Система категорий

### CategoryManager API

```python
# Получение менеджера (доступ через db)
cat_mgr = db.category_manager

# CRUD
cat = cat_mgr.add_category("Спорт", "#FF6B6B")     # Добавить
cat_mgr.update_category(cat_id, "Фитнес", "#FF0000")  # Обновить
cat_mgr.delete_category(cat_id)                   # Удалить (с переназначением)

# Получение
all_cats = cat_mgr.get_all_categories()           # Список всех
cat = cat_mgr.get_category_by_id(5)               # По ID
cat = cat_mgr.get_category_by_name("Работа")      # По имени
```

### Добавление цветовой маркировки в UI

```python
# Для QComboBox с иконками
pixmap = QPixmap(16, 16)
pixmap.fill(QColor(cat.color))
icon = QIcon(pixmap)
combo.addItem(icon, cat.name)

# Для отрисовки в кастомных виджетах
color = QColor(event.color)
light = QColor(color)
light.setAlpha(40)  # Прозрачность для фона
```

## 🎨 Стилизация

### Цветовая схема (класс Colors)

```python
class Colors:
    BG            = "#FFFFFF"      # Основной фон
    SECONDARY_BG  = "#F2F2F7"      # Фон второстепенных элементов
    SEPARATOR     = "#E5E5EA"      # Линии-разделители
    PRIMARY_TEXT  = "#1C1C1E"      # Основной текст
    SECONDARY_TEXT= "#8E8E93"      # Второстепенный текст
    ACCENT        = "#007AFF"      # Акцентный цвет (синий)
    ACCENT_LIGHT  = "#E5F0FF"      # Светлый акцент
    TODAY_TEXT    = "#FFFFFF"      # Текст на сегодняшнем дне
    WEEKEND       = "#8E8E93"      # Цвет выходных
    RED           = "#FF3B30"      # Красный (важное/удаление)
    GREEN         = "#34C759"      # Зелёный (личное)
    HOVER         = "#E5E5EA"      # При наведении
    WHITE         = "#FFFFFF"      # Белый
    ACTIVITY_BAR  = "#EBEBEB"      # Фон Activity Bar
```

### Кастомные стили

```python
# Для QPushButton
btn.setStyleSheet(f"""
    QPushButton {{
        background: {Colors.ACCENT};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background: #0063CC;
    }}
""")
```

### Глобальный стиль

Переменная `APP_STYLE` применяется ко всему приложению. Модифицируйте для смены темы.

## 🔧 Добавление функциональности

### Пример: Добавление напоминаний

1. **Расширить модель Event**:
```python
@dataclass
class Event:
    # ... существующие поля
    reminder_minutes: int = 0  # За сколько минут напомнить
```

2. **Обновить БД**:
```python
def _create_table(self):
    self.conn.execute("""
        ALTER TABLE events ADD COLUMN reminder_minutes INTEGER DEFAULT 0
    """)
```

3. **Добавить в EventDialog**:
```python
# В _build_ui
self.reminder_spin = QSpinBox()
self.reminder_spin.setRange(0, 1440)
self.reminder_spin.setSuffix(" минут")
```

4. **Создать таймер напоминаний**:
```python
class ReminderManager(QObject):
    def check_reminders(self):
        now = datetime.now()
        for event in self.db.get_all_events():
            delta = (event.start_dt - now).total_seconds() / 60
            if 0 < delta <= event.reminder_minutes:
                self.show_notification(event)
```

### Пример: Экспорт в iCal

```python
def export_to_ical(events: List[Event], filename: str):
    """Экспорт событий в формат iCalendar"""
    cal = Calendar()
    for event in events:
        vevent = Event()
        vevent.add('summary', event.title)
        vevent.add('dtstart', event.start_dt)
        vevent.add('dtend', event.end_dt)
        vevent.add('description', event.description)
        cal.add_component(vevent)
    
    with open(filename, 'w') as f:
        f.write(cal.serialize())
```

## 🧪 Тестирование

### Модульные тесты

```python
import unittest
from datetime import datetime
from your_app import DatabaseManager, Event

class TestCalendarApp(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager()
        # Используем временную БД для тестов
        self.db.conn = sqlite3.connect(":memory:")
        self.db._create_table()
    
    def test_add_event(self):
        event = Event("Тест", datetime.now(), datetime.now(), "Личное")
        saved = self.db.add_event(event)
        self.assertIsNotNone(saved.id)
    
    def test_get_events_by_date(self):
        # Тестовый код
        pass

if __name__ == '__main__':
    unittest.main()
```

### Ручное тестирование

Чеклист:
- [ ] Создание события во всех режимах
- [ ] Редактирование события
- [ ] Удаление события
- [ ] Навигация (сегодня/назад/вперёд)
- [ ] Переключение между режимами
- [ ] Управление категориями
- [ ] Корректное отображение overlapping событий
- [ ] Сохранение данных после перезапуска

## 📦 Сборка и дистрибуция

### PyInstaller (Windows)

```bash
# Установка
pip install pyinstaller

# Базовая сборка
pyinstaller --onefile --windowed calendar_app.py

# С иконкой и дополнительными файлами
pyinstaller --onefile --windowed `
    --icon=icon_windows/icon.ico `
    --add-data "icon_windows;icon_windows" `
    --name "CalendarApp" `
    calendar_app.py
```

### Файл спецификации PyInstaller

```python
# calendar_app.spec
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(['calendar_app.py'],
             pathex=[],
             binaries=[],
             datas=[('icon_windows', 'icon_windows')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False)

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.datas,
          [],
          name='CalendarApp',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='icon_windows/icon.ico')
```

### Сборка для macOS

```bash
pyinstaller --onefile --windowed --icon=icon.icns calendar_app.py
```

### Сборка для Linux

```bash
pyinstaller --onefile calendar_app.py
```

## 🐛 Отладка

### Включение подробного логирования

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('calendar_debug.log'),
        logging.StreamHandler()
    ]
)

# В нужных местах
logging.debug(f"Событие создано: {event.title}")
```

### Отладка отрисовки

```python
# Временно добавьте границы для виджетов
widget.setStyleSheet("border: 1px solid red;")
```

## 📚 Полезные ресурсы

- [PyQt5 Документация](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [SQLite Python](https://docs.python.org/3/library/sqlite3.html)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [Qt Style Sheets Reference](https://doc.qt.io/qt-5/stylesheet-reference.html)

## ❓ Частые проблемы

### Проблема: События не отображаются
**Решение**: Проверьте `event._db = self` при создании из БД.

### Проблема: Ошибка при удалении категории
**Решение**: Убедитесь, что есть категория "Личное" для переназначения.

### Проблема: Неправильное отображение overlapping событий
**Решение**: Проверьте функцию `_group_overlapping_events` - она должна правильно определять пересечения.

### Проблема: Приложение не сохраняет данные
**Решение**: Проверьте права на запись в папку с БД (особенно в Program Files).

## 🤝 Контрибьютинг

1. Следуйте PEP 8
2. Добавляйте type hints
3. Документируйте новые методы
4. Пишите тесты для новых функций
5. Обновляйте эту документацию
```
