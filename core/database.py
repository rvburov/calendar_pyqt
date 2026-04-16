import sys
import os
import sqlite3
from typing import Optional, List


class Category:
    def __init__(self, name: str, color: str, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.color = color


class CategoryManager:
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
        ("#FF6B6B", "Коралловый"),
    ]

    def __init__(self, db_conn, db_exists: bool = False):
        self.conn = db_conn
        self._create_table()
        
        # Создаем стандартные календари только если база данных только что создана
        if not db_exists:
            self._create_default_categories()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def _create_default_categories(self):
        """Создает стандартные календари при первом запуске"""
        default_categories = [
            ("Работа", "#007AFF"),
            ("Личное", "#34C759"),
            ("Важное", "#FF3B30")
        ]
        
        for name, color in default_categories:
            self.add_category(name, color)
        
        print("Созданы стандартные календари при первом запуске")

    def add_category(self, name: str, color: str) -> Optional["Category"]:
        try:
            cur = self.conn.execute(
                "INSERT INTO categories (name, color) VALUES (?,?)", (name, color)
            )
            self.conn.commit()
            return Category(name, color, cur.lastrowid)
        except sqlite3.IntegrityError:
            return None

    def update_category(self, cat_id: int, name: str, color: str) -> bool:
        try:
            self.conn.execute(
                "UPDATE categories SET name=?, color=? WHERE id=?", (name, color, cat_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_category(self, cat_id: int):
        personal = self.conn.execute(
            "SELECT id FROM categories WHERE name='Личное'"
        ).fetchone()
        if personal:
            self.conn.execute(
                "UPDATE events SET category=? WHERE category=?", (personal[0], cat_id)
            )
        self.conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.conn.commit()

    def get_all_categories(self) -> List["Category"]:
        cur = self.conn.execute("SELECT id, name, color FROM categories ORDER BY name")
        return [Category(name, color, id) for id, name, color in cur.fetchall()]

    def get_category_by_id(self, cat_id: int) -> Optional["Category"]:
        row = self.conn.execute(
            "SELECT id, name, color FROM categories WHERE id=?", (cat_id,)
        ).fetchone()
        return Category(row[1], row[2], row[0]) if row else None

    def get_category_by_name(self, name: str) -> Optional["Category"]:
        row = self.conn.execute(
            "SELECT id, name, color FROM categories WHERE name=?", (name,)
        ).fetchone()
        return Category(row[1], row[2], row[0]) if row else None


class DatabaseManager:
    def __init__(self):
        if getattr(sys, "frozen", False):
            app_data = os.path.join(
                os.environ.get("APPDATA", os.path.expanduser("~")), "MyPlanner"
            )
        else:
            app_data = os.path.dirname(os.path.abspath(__file__))

        os.makedirs(app_data, exist_ok=True)
        
        # Проверяем, существует ли файл базы данных
        db_path = os.path.join(app_data, "calendar.db")
        db_exists = os.path.exists(db_path)
        
        # Подключаемся к базе данных
        self.conn = sqlite3.connect(db_path)
        
        # Создаем таблицы
        self._create_events_table()
        
        # Создаем менеджер категорий с флагом существования БД
        self.category_manager = CategoryManager(self.conn, db_exists)

    def _create_events_table(self):
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

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None