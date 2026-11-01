"""Centralized Cactu dark theme: brand, semantic colors and widget states."""

from video_converter.ui.branding import branding_directory

BACKGROUND = "#11171c"
SURFACE = "#1a2228"
SURFACE_ELEVATED = "#242f37"
BORDER = "#475760"
TEXT_PRIMARY = "#edf2f4"
TEXT_SECONDARY = "#b3bfc7"
TEXT_MUTED = "#8d9ba4"
TEXT_ON_ACCENT = "#0d1c12"
ACCENT = "#5FAF6F"
ACCENT_HOVER = "#6DBC7C"
ACCENT_PRESSED = "#4B9159"
ACCENT_SUBTLE = "rgba(95, 175, 111, 0.12)"
ACCENT_BORDER = "rgba(95, 175, 111, 0.35)"
ACCENT_FOCUS = "rgba(95, 175, 111, 0.75)"
SELECTION_SURFACE = "#263b30"
SUCCESS = "#58c7a0"
WARNING = "#edba59"
ERROR = "#ec7378"
INFO = "#89b7d2"
DISABLED_SURFACE = "#1c252b"
DISABLED_TEXT = "#7d8a93"
HOVER_SURFACE = "#303e47"
PRESSED_SURFACE = "#1d282f"
PROGRESS_TRACK = "#303c44"
WARNING_SURFACE = "#342b1c"
WARNING_BORDER = "#806332"
ERROR_SURFACE = "#3c252a"
ERROR_HOVER = "#523037"
ERROR_PRESSED = "#301e23"

CHECK_ICON = (branding_directory() / "check.svg").as_posix().replace('"', '\\"')

STYLESHEET = f"""
QWidget {{ background: {BACKGROUND}; color: {TEXT_PRIMARY}; font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }}
QLabel, QRadioButton, QCheckBox {{ background: transparent; }}
QMainWindow, QDialog {{ background: {BACKGROUND}; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#warning {{ background: {WARNING_SURFACE}; border: 1px solid {WARNING_BORDER}; border-radius: 9px; }}
QLabel#title {{ font-size: 25px; font-weight: 700; color: {TEXT_PRIMARY}; }}
QLabel#section {{ font-size: 17px; font-weight: 700; }}
QLabel#muted {{ color: {TEXT_SECONDARY}; }}
QLabel#warningText {{ color: {WARNING}; font-weight: 600; }}
QLabel#successText {{ color: {SUCCESS}; }}
QLabel#errorText {{ color: {ERROR}; font-weight: 600; }}
QLabel#brandText {{ color: {ACCENT}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {SURFACE_ELEVATED}; border: 1px solid {BORDER}; border-radius: 7px; padding: 7px 10px; min-height: 20px; selection-background-color: {SELECTION_SURFACE}; selection-color: {TEXT_PRIMARY}; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {ACCENT_BORDER}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT_FOCUS}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {DISABLED_SURFACE}; color: {DISABLED_TEXT}; border-color: {PROGRESS_TRACK}; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; color: {TEXT_PRIMARY}; selection-background-color: {SELECTION_SURFACE}; selection-color: {TEXT_PRIMARY}; border: 1px solid {ACCENT_BORDER}; }}
QComboBox QAbstractItemView::item:selected {{ background: {SELECTION_SURFACE}; }}
QWidget#loudnessPanel {{ background: transparent; }}
QPushButton {{ background: {SURFACE_ELEVATED}; border: 1px solid {BORDER}; border-radius: 8px; padding: 9px 16px; font-weight: 600; }}
QPushButton:hover {{ border-color: {ACCENT}; background: {HOVER_SURFACE}; }}
QPushButton:pressed {{ background: {PRESSED_SURFACE}; border-color: {ACCENT_PRESSED}; }}
QPushButton:focus {{ border-color: {ACCENT_FOCUS}; }}
QPushButton#primary {{ background: {ACCENT}; color: {TEXT_ON_ACCENT}; border-color: {ACCENT}; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background: {ACCENT_PRESSED}; border-color: {ACCENT_PRESSED}; }}
QPushButton#primary:focus {{ border: 2px solid {TEXT_PRIMARY}; padding: 8px 15px; }}
QPushButton#danger {{ background: {ERROR_SURFACE}; border-color: {ERROR}; color: {TEXT_PRIMARY}; }}
QPushButton#danger:hover {{ background: {ERROR_HOVER}; border-color: {ERROR}; }}
QPushButton#danger:pressed {{ background: {ERROR_PRESSED}; }}
QPushButton#danger:focus {{ border: 2px solid {ERROR}; padding: 8px 15px; }}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#danger:disabled {{ color: {DISABLED_TEXT}; background: {DISABLED_SURFACE}; border: 1px solid {PROGRESS_TRACK}; padding: 9px 16px; }}
QProgressBar {{ background: {PROGRESS_TRACK}; border: 0; border-radius: 7px; min-height: 14px; text-align: right; padding-right: 6px; color: {TEXT_PRIMARY}; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 7px; }}
QRadioButton, QCheckBox {{ spacing: 8px; }}
QRadioButton::indicator, QCheckBox::indicator {{ width: 16px; height: 16px; background: {SURFACE_ELEVATED}; border: 1px solid {TEXT_MUTED}; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QCheckBox::indicator:checked {{ image: url("{CHECK_ICON}"); }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QRadioButton::indicator:checked {{ width: 10px; height: 10px; border: 4px solid {SURFACE_ELEVATED}; background: {ACCENT}; }}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border-color: {ACCENT_HOVER}; }}
QRadioButton:focus, QCheckBox:focus {{ outline: 1px solid {ACCENT_FOCUS}; }}
QRadioButton:disabled, QCheckBox:disabled {{ color: {DISABLED_TEXT}; }}
QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {{ background: {DISABLED_SURFACE}; border-color: {PROGRESS_TRACK}; }}
QRadioButton::indicator:checked:disabled, QCheckBox::indicator:checked:disabled {{ background: {TEXT_MUTED}; border-color: {PROGRESS_TRACK}; }}
QRadioButton::indicator:checked:disabled {{ border: 4px solid {DISABLED_SURFACE}; }}
QSlider::groove:horizontal {{ height: 5px; background: {PROGRESS_TRACK}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; border: 2px solid {SURFACE}; width: 13px; margin: -6px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}
QSlider::handle:horizontal:pressed {{ background: {ACCENT_PRESSED}; }}
QSlider:focus {{ border: 1px solid {ACCENT_FOCUS}; border-radius: 6px; }}
QSlider::sub-page:horizontal:disabled, QSlider::handle:horizontal:disabled {{ background: {DISABLED_TEXT}; }}
QScrollArea {{ border: 0; }}
QListView {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 3px; outline: none; }}
QListView::item {{ padding: 7px; border: 1px solid transparent; border-radius: 6px; }}
QListView::item:selected {{ background: {ACCENT_SUBTLE}; border-color: {ACCENT}; color: {TEXT_PRIMARY}; }}
QListView::item:hover:!selected {{ background: {HOVER_SURFACE}; border-color: {ACCENT_BORDER}; }}
QListView:focus {{ border-color: {ACCENT_FOCUS}; }}
QListView[dropTarget="true"] {{ border: 2px solid {ACCENT}; background: {ACCENT_SUBTLE}; }}
QScrollBar:vertical {{ background: {BACKGROUND}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QToolTip {{ color: {TEXT_PRIMARY}; background: {SURFACE_ELEVATED}; border: 1px solid {BORDER}; }}
"""


def apply_theme(app) -> None:
    from PySide6.QtGui import QColor, QPalette
    palette = app.palette()
    for role, color in ((QPalette.ColorRole.Link, ACCENT), (QPalette.ColorRole.LinkVisited, ACCENT_PRESSED),
                        (QPalette.ColorRole.Highlight, SELECTION_SURFACE),
                        (QPalette.ColorRole.HighlightedText, TEXT_PRIMARY)):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
