import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QSplitter, QVBoxLayout, QLineEdit,
    QHBoxLayout as HBox, QGridLayout, QPushButton, QCheckBox, QListWidget, QListView,
    QSpinBox, QLabel, QGroupBox, QListWidgetItem)
from PySide6.QtCore import Qt, QSize, QEvent, QTimer, QObject   # CHANGED add QObject
from PySide6.QtGui import QPixmap
from image_cache import ensure_card_image

def _load_card_db():
    """
    Load card DB via engine.card_db (main no longer hosts this function).
    """
    from engine.card_db import load_card_db as _lcd
    return _lcd()

class DecksTabManager(QObject):   # CHANGED (inherit QObject for eventFilter)
    def __init__(self, main_win):
        # FIX: GameAppAPI isn't a QObject; avoid passing as parent
        super().__init__()   # CHANGED
        self.mw = main_win
        self.deck_builder_initialized = False
        # state copied from original
        self.deck_main = {}
        self.deck_commander = None
        self.deck_counts = {"lands":0,"creatures":0,"other":0,"total":0}

    # Public API
    def build_tab(self):
        if not self.deck_builder_initialized:
            self._init_deck_builder_state()
        root = QWidget()
        layout = QHBoxLayout(root); layout.setContentsMargins(4,4,4,4); layout.setSpacing(6)

        splitter = QSplitter()
        layout.addWidget(splitter)

        # LEFT FILTER
        filt = QWidget()
        fv = QVBoxLayout(filt); fv.setContentsMargins(0,0,0,0); fv.setSpacing(4)
        self.card_search_box = QLineEdit()
        self.card_search_box.setPlaceholderText("Search card name...")
        self.card_search_box.returnPressed.connect(self._apply_filters)
        fv.addWidget(self.card_search_box)

        color_row = HBox()
        self.color_checks = {}
        for sym, tip in zip("WUBRG", ["White","Blue","Black","Red","Green"]):
            cb = QCheckBox(sym)
            cb.setToolTip(tip)
            cb.stateChanged.connect(self._apply_filters)
            self.color_checks[sym] = cb
            color_row.addWidget(cb)
        color_row.addStretch(1)
        fv.addLayout(color_row)

        self.type_checks = {}
        type_row = QGridLayout()
        for i, t in enumerate(["Creature","Artifact","Enchantment","Instant","Sorcery","Planeswalker","Land"]):
            cb = QCheckBox(t)
            cb.stateChanged.connect(self._apply_filters)
            self.type_checks[t] = cb
            type_row.addWidget(cb, i//2, i%2)
        fv.addLayout(type_row)

        btn_filter = QPushButton("Apply Filters")
        btn_filter.clicked.connect(self._apply_filters)
        fv.addWidget(btn_filter)
        fv.addStretch(1)
        splitter.addWidget(filt)

        # RIGHT
        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(4)

        ctrl = HBox()
        self.add_qty_spin = QSpinBox(); self.add_qty_spin.setRange(1,4); self.add_qty_spin.setValue(1)
        ctrl.addWidget(QLabel("Qty")); ctrl.addWidget(self.add_qty_spin)
        self.btn_add_selected = QPushButton("Add Selected")
        self.btn_add_selected.clicked.connect(self._add_selected_card)
        ctrl.addWidget(self.btn_add_selected)
        btn_reset = QPushButton("Reset Filters")
        btn_reset.clicked.connect(self._reset_filters)
        ctrl.addWidget(btn_reset)
        ctrl.addStretch(1)
        rv.addLayout(ctrl)

        self.card_gallery = QListWidget()
        self.card_gallery.setViewMode(QListView.IconMode)
        self.card_gallery.setResizeMode(QListWidget.Adjust)
        self.card_gallery.setMovement(QListWidget.Static)
        self.card_gallery.setIconSize(QSize(144,200))
        self.card_gallery.setSpacing(8)
        self.card_gallery.itemDoubleClicked.connect(lambda _: self._add_selected_card())
        # Lazy load hooks
        self.card_gallery.installEventFilter(self)
        self.card_gallery.verticalScrollBar().valueChanged.connect(self._lazy_load_visible_images)
        if self.card_gallery.horizontalScrollBar():
            self.card_gallery.horizontalScrollBar().valueChanged.connect(self._lazy_load_visible_images)
        rv.addWidget(self.card_gallery, 3)

        lower_split = QSplitter(); lower_split.setOrientation(Qt.Horizontal)

        cmd_box = QGroupBox("Commander")
        cv = QVBoxLayout(cmd_box); cv.setContentsMargins(6,6,6,6); cv.setSpacing(4)
        self.cmd_img = QLabel(); self.cmd_img.setFixedSize(180,250)
        self.cmd_img.setStyleSheet("background:#222;border:1px solid #444;")
        self.cmd_img.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.cmd_img)
        self.cmd_name_lbl = QLabel("<none>"); self.cmd_name_lbl.setStyleSheet("color:#bbb;")
        cv.addWidget(self.cmd_name_lbl)
        b_set = QPushButton("Set From Selection"); b_set.clicked.connect(self._set_commander_from_selection)
        b_clr = QPushButton("Clear Commander"); b_clr.clicked.connect(self._clear_commander)
        cv.addWidget(b_set); cv.addWidget(b_clr); cv.addStretch(1)
        lower_split.addWidget(cmd_box)

        deck_box = QGroupBox("Deck (Main)")
        dv = QVBoxLayout(deck_box); dv.setContentsMargins(6,6,6,6); dv.setSpacing(4)
        self.deck_list_widget = QListWidget()
        self.deck_list_widget.itemDoubleClicked.connect(self._remove_entry)
        dv.addWidget(self.deck_list_widget, 1)
        sum_row = HBox()
        self.summary_lbl = QLabel(""); self.summary_lbl.setStyleSheet("font:11px 'Consolas';")
        sum_row.addWidget(self.summary_lbl, 1)
        rem = QPushButton("Remove Selected"); rem.clicked.connect(self._remove_entry)
        sum_row.addWidget(rem)
        dv.addLayout(sum_row)
        lower_split.addWidget(deck_box)
        lower_split.setStretchFactor(0,0); lower_split.setStretchFactor(1,1)
        rv.addWidget(lower_split, 2)

        splitter.addWidget(right)
        splitter.setStretchFactor(0,0); splitter.setStretchFactor(1,1)

        self._populate_gallery()
        self._refresh_lists()
        self._update_summary()
        QTimer.singleShot(0, self._lazy_load_visible_images)  # initial lazy load after layout
        return root

    def eventFilter(self, obj, ev):
        if obj is self.card_gallery and ev.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(0, self._lazy_load_visible_images)
        return super().eventFilter(obj, ev)

    def refresh(self):
        self._refresh_lists()
        self._update_summary()

    # Internal copied logic
    def _init_deck_builder_state(self):
        _load_card_db()  # ensure loaded (now from engine.card_db)
        self.deck_builder_initialized = True

    def _reset_filters(self):
        self.card_search_box.clear()
        for cb in self.color_checks.values(): cb.setChecked(False)
        for cb in self.type_checks.values(): cb.setChecked(False)
        self._apply_filters()

    def _apply_filters(self):
        self._populate_gallery()

    def _populate_gallery(self):
        if not self.deck_builder_initialized: return
        term = self.card_search_box.text().strip().lower()
        colors = {c for c,cb in self.color_checks.items() if cb.isChecked()}
        types = {t for t,cb in self.type_checks.items() if cb.isChecked()}
        by_name_lower = _load_card_db()[1]   # updated source
        items = []
        for name, card in by_name_lower.items():
            if term and term not in name: continue
            if types and not any(t in card.get('types',[]) for t in types): continue
            if colors and not (set(card.get('color_identity', [])) & colors): continue
            items.append(card)
            if len(items) >= 400: break
        self.card_gallery.clear()
        for c in items:
            li = QListWidgetItem(c['name'])
            li.setData(Qt.UserRole, c)
            li.setData(Qt.UserRole+1, False)  # mark image not loaded
            # no image fetch here (lazy)
            self.card_gallery.addItem(li)

    def _lazy_load_visible_images(self):
        """
        Fetch images only for items whose visual rect intersects the viewport.
        """
        if not self.card_gallery.count():
            return
        viewport = self.card_gallery.viewport().rect()
        for i in range(self.card_gallery.count()):
            item = self.card_gallery.item(i)
            if item.data(Qt.UserRole+1):
                continue
            rect = self.card_gallery.visualItemRect(item)
            if not rect.isValid() or not rect.intersects(viewport):
                continue
            card = item.data(Qt.UserRole)
            path = ensure_card_image(card['id'])
            if path and os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    item.setIcon(pm.scaled(144,200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            item.setData(Qt.UserRole+1, True)

    def _add_selected_card(self):
        sel = self.card_gallery.selectedItems()
        if not sel: return
        c = sel[0].data(Qt.UserRole)
        if self.deck_commander and c['id'] == self.deck_commander['id']: return
        qty = self.add_qty_spin.value()
        existing = self.deck_main.get(c['name'])
        if existing:
            if not self._is_basic_land(c) and existing[1] >= 1: return
            self.deck_main[c['name']] = (existing[0], existing[1]+qty)
        else:
            self.deck_main[c['name']] = (c, qty)
        self._refresh_lists(); self._recount(); self._update_summary()

    def _remove_entry(self, *_):
        sel = self.deck_list_widget.selectedItems()
        if not sel: return
        name = sel[0].data(Qt.UserRole)
        if name in self.deck_main:
            card, ct = self.deck_main[name]
            if ct <= 1: del self.deck_main[name]
            else: self.deck_main[name] = (card, ct-1)
        self._refresh_lists(); self._recount(); self._update_summary()

    def _refresh_lists(self):
        self.deck_list_widget.clear()
        def key(item):
            c, ct = item
            types = c.get('types',[])
            if 'Land' in types: grp=0
            elif 'Creature' in types: grp=1
            else: grp=2
            return (grp, c['name'])
        for name,(c,ct) in sorted(self.deck_main.items(), key=key):
            li = QListWidgetItem(f"{ct}x {c['name']}")
            li.setData(Qt.UserRole, name)
            self.deck_list_widget.addItem(li)
        if self.deck_commander:
            path = ensure_card_image(self.deck_commander['id'])
            # removed any .jpg assumptions
            if path and os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    self.cmd_img.setPixmap(pm.scaled(180,250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.cmd_name_lbl.setText(self.deck_commander['name'])
        else:
            self.cmd_img.clear()
            self.cmd_name_lbl.setText("<none>")

    def _recount(self):
        lands = creatures = other = total = 0
        for c,ct in (v for v in self.deck_main.values()):
            total += ct
            types = c.get('types',[])
            if 'Land' in types: lands += ct
            elif 'Creature' in types: creatures += ct
            else: other += ct
        self.deck_counts.update({"lands":lands,"creatures":creatures,"other":other,"total":total})

    def _update_summary(self):
        main_target = 99
        have = self.deck_counts['total']
        valid = have == main_target and self.deck_commander is not None
        col = "#5cb85c" if valid else "#d9534f"
        self.summary_lbl.setText(
            f"Lands:{self.deck_counts['lands']}  Creatures:{self.deck_counts['creatures']}  "
            f"Other:{self.deck_counts['other']}  Total:{have}/99  {'OK' if valid else 'Incomplete'}"
        )
        self.summary_lbl.setStyleSheet(f"font:11px 'Consolas'; color:{col};")

    def _is_basic_land(self, card):
        return 'Land' in card.get('types', []) and card['name'] in ('Plains','Island','Swamp','Mountain','Forest','Wastes')

    def _set_commander_from_selection(self):
        sel = self.card_gallery.selectedItems()
        if not sel: return
        c = sel[0].data(Qt.UserRole)
        if 'Creature' not in c.get('types', []): return
        self.deck_commander = c
        if c['name'] in self.deck_main: del self.deck_main[c['name']]
        self._recount(); self._refresh_lists(); self._update_summary()

    def _clear_commander(self):
        self.deck_commander = None
        self._refresh_lists()
        self._update_summary()
