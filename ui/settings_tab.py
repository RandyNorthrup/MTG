import os
from PySide6.QtCore import Qt   # ADDED
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFileDialog, QMessageBox)

class SettingsTabManager:
    def __init__(self, main_win):
        self.mw = main_win
        self._tab = None
        self._tab_index = None
        self._selected_image = None

    def open(self):
        if self._tab is None:
            self._tab = self._build()
            self._tab_index = self.mw.tabs.addTab(self._tab, "Settings")
        self.mw.tabs.setCurrentIndex(self._tab_index)

    def _build(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(12,12,12,12); v.setSpacing(12)
        header = QLabel("Settings")
        header.setStyleSheet("font-size:22px;font-weight:bold;")
        v.addWidget(header, 0)

        row = QHBoxLayout()
        btn = QPushButton("Choose Background PNG...")
        btn.clicked.connect(self._choose_image)
        row.addWidget(btn); row.addStretch(1)
        v.addLayout(row)

        self.img_lbl = QLabel("No image selected")
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.setMinimumSize(400,300)
        self.img_lbl.setStyleSheet("QLabel {background:#111;border:1px solid #444;color:#888;}")
        self.img_lbl.setScaledContents(True)
        v.addWidget(self.img_lbl, 1)

        hint = QLabel("Select a PNG (<= 3 MB). Image auto-scales to available space.")
        hint.setStyleSheet("color:#888;font-size:11px;")
        v.addWidget(hint)
        return w

    def _choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self.mw, "Select PNG Image", "", "PNG Images (*.png)")
        if not path: return
        try:
            if not path.lower().endswith(".png"):
                QMessageBox.warning(self.mw, "Invalid", "File must be .png")
                return
            if os.path.getsize(path) > 3*1024*1024:
                QMessageBox.warning(self.mw, "Too Large", "Image exceeds 3 MB.")
                return
            from PySide6.QtGui import QPixmap
            pm = QPixmap(path)
            if pm.isNull():
                QMessageBox.warning(self.mw, "Error", "Could not load image.")
                return
            self._selected_image = path
            self.img_lbl.setPixmap(pm)
            self.img_lbl.setStyleSheet("QLabel {background:#000;border:1px solid #222;}")
        except Exception as ex:
            QMessageBox.critical(self.mw, "Error", str(ex))
