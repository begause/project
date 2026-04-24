import sys
import json
import os
from datetime import datetime, date
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QGroupBox, QFormLayout,
    QStatusBar, QSplitter
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QIcon


class Expense:
    def __init__(self, amount, category, date_str):
        self.amount = float(amount)
        self.category = category
        self.date = date_str

    def to_dict(self):
        return {
            'amount': self.amount,
            'category': self.category,
            'date': self.date
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['amount'], data['category'], data['date'])


class ExpenseTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.expenses = []
        self.data_file = "expenses.json"
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("Expense Tracker - Трекер расходов")
        self.setGeometry(100, 100, 1100, 650)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#delete_btn {
                background-color: #f44336;
            }
            QPushButton#delete_btn:hover {
                background-color: #da190b;
            }
            QTableWidget {
                gridline-color: #d3d3d3;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                border: 1px solid #ddd;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        input_group = QGroupBox("Добавить новый расход")
        input_layout = QFormLayout()

        amount_layout = QHBoxLayout()
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Введите сумму")
        self.amount_input.setMaximumWidth(200)
        amount_layout.addWidget(self.amount_input)
        amount_layout.addStretch()
        input_layout.addRow("Сумма (₽):", amount_layout)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Еда", "Транспорт", "Развлечения", "Покупки", "Здоровье", "Образование", "Жильё", "Другое"])
        self.category_combo.setMaximumWidth(200)
        input_layout.addRow("Категория:", self.category_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMaximumWidth(200)
        input_layout.addRow("Дата:", self.date_edit)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить расход")
        self.add_button.clicked.connect(self.add_expense)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addStretch()
        input_layout.addRow("", buttons_layout)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        filters_group = QGroupBox("Фильтры")
        filters_layout = QHBoxLayout()

        filters_layout.addWidget(QLabel("Категория:"))
        self.filter_category = QComboBox()
        self.filter_category.addItem("Все категории")
        for i in range(self.category_combo.count()):
            self.filter_category.addItem(self.category_combo.itemText(i))
        self.filter_category.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.filter_category)

        filters_layout.addWidget(QLabel("Период с:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setDate(QDate(2024, 1, 1))
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_from.dateChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.filter_date_from)

        filters_layout.addWidget(QLabel("по:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setDate(QDate.currentDate())
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_to.dateChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.filter_date_to)

        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        filters_layout.addWidget(self.reset_filters_btn)

        filters_layout.addStretch()

        filters_group.setLayout(filters_layout)
        main_layout.addWidget(filters_group)

        table_layout = QHBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Сумма (₽)", "Категория", "Дата", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        table_layout.addWidget(self.table)
        main_layout.addLayout(table_layout)

        total_layout = QHBoxLayout()
        self.total_label = QLabel("Итого за период: 0.00 ₽")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2e7d32;")
        total_layout.addWidget(self.total_label)
        total_layout.addStretch()

        self.clear_all_btn = QPushButton("Очистить все данные")
        self.clear_all_btn.setObjectName("delete_btn")
        self.clear_all_btn.clicked.connect(self.clear_all_data)
        total_layout.addWidget(self.clear_all_btn)

        main_layout.addLayout(total_layout)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готов к работе | Файл данных: " + self.data_file)

    def validate_input(self):
        amount_text = self.amount_input.text().strip()
        if not amount_text:
            QMessageBox.warning(self, "Ошибка", "Введите сумму расхода!")
            return False
        
        try:
            amount = float(amount_text)
            if amount <= 0:
                QMessageBox.warning(self, "Ошибка", "Сумма должна быть положительным числом!")
                return False
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть числом!")
            return False
        
        return True

    def add_expense(self):
        if not self.validate_input():
            return
        
        amount = float(self.amount_input.text().strip())
        category = self.category_combo.currentText()
        date = self.date_edit.date().toString("yyyy-MM-dd")

        expense = Expense(amount, category, date)
        self.expenses.append(expense)
        self.save_data()
        self.apply_filters()
        self.amount_input.clear()
        self.statusBar.showMessage(f"Расход добавлен: {amount:.2f} ₽ | {category} | {date}")

    def delete_expense(self, index):
        confirmation = QMessageBox.question(
            self, "Подтверждение", 
            "Вы уверены, что хотите удалить этот расход?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmation == QMessageBox.Yes:
            del self.expenses[index]
            self.save_data()
            self.apply_filters()
            self.statusBar.showMessage("Расход удален")

    def apply_filters(self):
        filtered_expenses = self.get_filtered_expenses()
        self.update_table(filtered_expenses)
        self.update_total(filtered_expenses)

    def get_filtered_expenses(self):
        category_filter = self.filter_category.currentText()
        date_from = self.filter_date_from.date().toString("yyyy-MM-dd")
        date_to = self.filter_date_to.date().toString("yyyy-MM-dd")
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()

        filtered = []
        for expense in self.expenses:
            expense_date = datetime.strptime(expense.date, "%Y-%m-%d").date()
            
            if date_from_obj <= expense_date <= date_to_obj:
                if category_filter == "Все категории" or expense.category == category_filter:
                    filtered.append(expense)
        
        return sorted(filtered, key=lambda x: x.date, reverse=True)

    def update_table(self, expenses):
        self.table.setRowCount(len(expenses))
        for i, expense in enumerate(expenses):
            amount_item = QTableWidgetItem(f"{expense.amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 0, amount_item)
            
            category_item = QTableWidgetItem(expense.category)
            category_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, category_item)
            
            date_item = QTableWidgetItem(expense.date)
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, date_item)
            
            delete_btn = QPushButton("❌")
            delete_btn.setObjectName("delete_btn")
            delete_btn.setFixedWidth(40)
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_expense_index(idx))
            self.table.setCellWidget(i, 3, delete_btn)

    def delete_expense_index(self, index):
        filtered_expenses = self.get_filtered_expenses()
        if index < len(filtered_expenses):
            expense_to_delete = filtered_expenses[index]
            try:
                original_index = self.expenses.index(expense_to_delete)
                self.delete_expense(original_index)
            except ValueError:
                self.apply_filters()

    def update_total(self, expenses):
        total = sum(expense.amount for expense in expenses)
        self.total_label.setText(f"Итого за период: {total:.2f} ₽")

    def reset_filters(self):
        self.filter_category.setCurrentText("Все категории")
        self.filter_date_from.setDate(QDate(2024, 1, 1))
        self.filter_date_to.setDate(QDate.currentDate())
        self.apply_filters()

    def clear_all_data(self):
        confirmation = QMessageBox.question(
            self, "Подтверждение",
            "Вы действительно хотите удалить ВСЕ данные?\nЭто действие нельзя отменить!",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmation == QMessageBox.Yes:
            self.expenses = []
            self.save_data()
            self.apply_filters()
            self.statusBar.showMessage("Все данные удалены")

    def save_data(self):
        data = [expense.to_dict() for expense in self.expenses]
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.expenses = [Expense.from_dict(item) for item in data]
                self.apply_filters()
            except (json.JSONDecodeError, KeyError):
                self.expenses = []
                self.statusBar.showMessage("Ошибка загрузки файла данных")
        else:
            self.expenses = []

    def closeEvent(self, event):
        self.save_data()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    tracker = ExpenseTracker()
    tracker.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
