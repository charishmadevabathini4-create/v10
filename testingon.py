import sys
import sqlite3

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox
)
from PySide6.QtCore import Qt


DB_PATH = "Preliminary_data.db"


class DatabaseViewer(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Preliminary Psychological Database")
        self.resize(1500, 800)

        # Main layout
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Psychological Pattern Database")
        title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)

        # Top controls
        control_layout = QHBoxLayout()

        self.table_selector = QComboBox()

        self.load_button = QPushButton("Load Database")
        self.load_button.clicked.connect(self.load_database)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_tables)

        control_layout.addWidget(QLabel("Select Table:"))
        control_layout.addWidget(self.table_selector)
        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.refresh_button)

        layout.addLayout(control_layout)

        # Database table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

        # Status
        self.status_label = QLabel("Database not loaded")

        layout.addWidget(self.status_label)

        # Load available tables
        self.load_tables()

    # --------------------------------------------------
    # GET TABLE NAMES
    # --------------------------------------------------

    def load_tables(self):

        try:

            connection = sqlite3.connect(DB_PATH)
            cursor = connection.cursor()

            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)

            tables = cursor.fetchall()

            connection.close()

            self.table_selector.clear()

            for table in tables:
                self.table_selector.addItem(table[0])

            if tables:
                self.status_label.setText(
                    f"{len(tables)} database tables found"
                )

        except sqlite3.Error as error:

            QMessageBox.critical(
                self,
                "Database Error",
                str(error)
            )

    # --------------------------------------------------
    # LOAD SELECTED TABLE
    # --------------------------------------------------

    def load_database(self):

        selected_table = self.table_selector.currentText()

        if not selected_table:
            return

        try:

            connection = sqlite3.connect(DB_PATH)
            cursor = connection.cursor()

            # Get column information
            cursor.execute(
                f'PRAGMA table_info("{selected_table}")'
            )

            columns = cursor.fetchall()

            column_names = [
                column[1]
                for column in columns
            ]

            # Read records
            cursor.execute(
                f'SELECT * FROM "{selected_table}"'
            )

            rows = cursor.fetchall()

            connection.close()

            # Configure table
            self.table.setSortingEnabled(False)

            self.table.clear()

            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(column_names))

            self.table.setHorizontalHeaderLabels(
                column_names
            )

            # Insert data
            for row_index, row in enumerate(rows):

                for column_index, value in enumerate(row):

                    if value is None:
                        value = ""

                    item = QTableWidgetItem(
                        str(value)
                    )

                    self.table.setItem(
                        row_index,
                        column_index,
                        item
                    )

            self.table.resizeColumnsToContents()

            self.table.setSortingEnabled(True)

            self.status_label.setText(
                f"Table: {selected_table} | "
                f"Records: {len(rows)} | "
                f"Columns: {len(column_names)}"
            )

        except sqlite3.Error as error:

            QMessageBox.critical(
                self,
                "Database Error",
                str(error)
            )


# ------------------------------------------------------
# MAIN PROGRAM
# ------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = DatabaseViewer()

    window.show()

    sys.exit(app.exec())