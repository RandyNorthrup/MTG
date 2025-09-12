import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter

class ScaledBackground(QWidget):
    def __init__(self, img_path: str):
        super().__init__()
        self._pix = QPixmap(img_path)

    def paintEvent(self, ev):
        if self._pix.isNull():
            return
        qp = QPainter(self)
        qp.drawPixmap(self.rect(), self._pix)

def build_home_tab(ctx):
    """
    Returns the home tab widget with the centered semi‑transparent Settings button.
    ctx: GameAppAPI (preferred) or MainWindow legacy.
    """
    img = os.path.join('data', 'images', 'home_bg.png')
    if os.path.exists(img):
        home = ScaledBackground(img)
    else:
        home = QWidget()
    v = QVBoxLayout(home); v.setContentsMargins(0,0,0,0)
    v.addStretch(1)
    btn = QPushButton("Settings")
    btn.setFixedSize(200, 56)
    btn.setStyleSheet(
        "QPushButton {background:rgba(0,0,0,102); color:#fff; "
        "border:1px solid #666; border-radius:6px; font-size:18px;}"
        "QPushButton:hover {background:rgba(40,40,40,140);}"
        "QPushButton:pressed {background:rgba(80,80,80,160);}"
    )

    def _open_settings():
        if hasattr(ctx, "open_settings") and callable(ctx.open_settings):
            ctx.open_settings()
        else:
            # Error: open_settings called with invalid context (debug print removed)
            pass

    btn.clicked.connect(_open_settings)
    wrap = QHBoxLayout()
    wrap.addStretch(1); wrap.addWidget(btn, alignment=Qt.AlignCenter); wrap.addStretch(1)
    v.addLayout(wrap)
    v.addStretch(2)
    # Expose for legacy external references (attach to underlying window if present)
    target = getattr(ctx, 'w', ctx)
    setattr(target, 'btn_settings', btn)
    return home
