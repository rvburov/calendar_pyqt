import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from core.database import DatabaseManager
from core.styles import APP_STYLE
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    font = QFont("Helvetica Neue", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    db = DatabaseManager()
    window = MainWindow(db)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()