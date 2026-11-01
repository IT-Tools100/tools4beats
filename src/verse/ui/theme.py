"""Тема оформления: спокойный светлый интерфейс в духе macOS.

Принципы (см. skills/skill-(apple-design).md, разделы 12, 15, 16):
* иерархия через сдержанный контраст, а не через цветные блоки;
* один акцентный цвет, один тон поверхностей, тонкие границы;
* системный шрифт, крупные заголовки, мелкие подписи — спокойным серым;
* у текстовых меток нет собственного фона.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

# Палитра
BG = "#F5F5F7"          # фон окна
SURFACE = "#FFFFFF"     # карточки, таблицы, поля
SIDEBAR = "#EFEFF4"     # боковая панель
BORDER = "#E5E5EA"      # тонкая граница
TEXT = "#1D1D1F"        # основной текст
TEXT_MUTED = "#6E6E73"  # подписи
TEXT_FAINT = "#8E8E93"  # самый тихий текст
ACCENT = "#007AFF"      # системный синий
DANGER = "#FF3B30"
SUCCESS = "#34C759"

_ASSETS = Path(__file__).resolve().parent / "assets"
CHEVRON = (_ASSETS / "chevron-down.svg").as_posix()

STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QWidget#Content {{
    background: {BG};
}}

/* ---------- Боковая панель ---------- */
#Sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {BORDER};
}}
#Brand {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 700;
}}
#SidebarVersion {{
    color: {TEXT_FAINT};
    font-size: 11px;
}}
#SidebarNav {{
    background: transparent;
    border: none;
    outline: 0;
    font-size: 13px;
}}
#SidebarNav::item {{
    color: #3A3A3C;
    padding: 7px 12px;
    margin: 1px 10px;
    border-radius: 8px;
}}
#SidebarNav::item:hover {{
    background: rgba(0, 0, 0, 0.05);
}}
#SidebarNav::item:selected {{
    background: {ACCENT};
    color: #FFFFFF;
}}

/* ---------- Заголовки и подписи ---------- */
#PageTitle {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT};
}}
#SectionTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT};
}}
#Hint {{
    color: {TEXT_FAINT};
    font-size: 12px;
}}
#Banner {{
    background: #EEF6FF;
    border: 1px solid #CFE3FF;
    border-radius: 10px;
    padding: 8px 12px;
    color: #0B5AA8;
    font-size: 12px;
}}

/* ---------- Карточки ---------- */
#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
#CardTitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
}}
#CardValue {{
    color: {TEXT};
    font-size: 26px;
    font-weight: 600;
}}

/* ---------- Кнопки ---------- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid #D2D2D7;
    border-radius: 8px;
    padding: 6px 14px;
    color: {TEXT};
    min-height: 18px;
}}
QPushButton:hover {{
    background: #FAFAFC;
}}
QPushButton:pressed {{
    background: #EFEFF4;
}}
QPushButton:disabled {{
    color: #B4B4B9;
    border-color: {BORDER};
    background: #FBFBFC;
}}
QPushButton[primary="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #FFFFFF;
    font-weight: 500;
}}
QPushButton[primary="true"]:hover {{
    background: #0A6FE0;
    border-color: #0A6FE0;
}}
QPushButton[primary="true"]:pressed {{
    background: #0062CC;
    border-color: #0062CC;
}}
QPushButton[primary="true"]:disabled {{
    background: #B7D9FF;
    border-color: #B7D9FF;
    color: #FFFFFF;
}}
QPushButton[danger="true"] {{
    color: {DANGER};
    border-color: #FFD1CE;
}}
QPushButton[danger="true"]:hover {{
    background: #FFF4F3;
}}

/* ---------- Поля ввода ---------- */
QLineEdit, QComboBox, QPlainTextEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {{
    background: {SURFACE};
    border: 1px solid #D2D2D7;
    border-radius: 8px;
    padding: 5px 9px;
    color: {TEXT};
    selection-background-color: #B3D7FF;
    selection-color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus,
QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled {{
    color: {TEXT_FAINT};
    background: #FAFAFC;
}}
QComboBox {{
    padding-right: 26px;
}}
QComboBox::drop-down {{
    border: none;
    background: transparent;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QComboBox::down-arrow {{
    image: url("{CHEVRON}");
    width: 10px;
    height: 6px;
}}
QDateTimeEdit::drop-down {{
    border: none;
    background: transparent;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QDateTimeEdit::down-arrow {{
    image: url("{CHEVRON}");
    width: 10px;
    height: 6px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0;
    height: 0;
    border: none;
    background: transparent;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
    outline: 0;
}}

/* ---------- Таблицы ---------- */
QTableView, QTableWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #E8F1FF;
    selection-color: {TEXT};
    alternate-background-color: #FBFBFD;
}}
QTableView::item, QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QHeaderView::section {{
    background: #FAFAFC;
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QTableCornerButton::section {{
    background: #FAFAFC;
    border: none;
}}

/* ---------- Вкладки ---------- */
QTabWidget::pane {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 7px 14px;
    margin-right: 2px;
    border-radius: 7px;
}}
QTabBar::tab:hover {{
    color: {TEXT};
}}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {TEXT};
    font-weight: 600;
}}

/* ---------- Группы ---------- */
QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 10px;
    padding: 34px 16px 14px 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: padding;
    subcontrol-position: top left;
    left: 16px;
    top: 12px;
    padding: 0;
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 600;
}}

/* ---------- Списки и области прокрутки ---------- */
QListWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 4px;
    outline: 0;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background: #E8F1FF;
    color: {TEXT};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ---------- Полосы прокрутки ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(0, 0, 0, 0.16);
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(0, 0, 0, 0.28);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: rgba(0, 0, 0, 0.16);
    border-radius: 5px;
    min-width: 32px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---------- Прочее ---------- */
QStatusBar {{
    background: {SIDEBAR};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QStatusBar::item {{
    border: none;
}}
QToolTip {{
    background: #2C2C2E;
    color: #FFFFFF;
    border: none;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
}}
QSplitter::handle {{
    background: {BORDER};
}}
"""


def add_card_shadow(widget: QWidget) -> None:
    """Мягкая тень: отделяет поверхность от фона, не добавляя «коробки»."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(18)
    effect.setOffset(0, 2)
    effect.setColor(QColor(0, 0, 0, 20))
    widget.setGraphicsEffect(effect)
