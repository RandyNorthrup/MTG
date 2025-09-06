import os, sys, json
from PySide6.QtWidgets import (
    QDialog, QApplication, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from deckbuilder.deckbuilder_logic import validate_deck_from_ids
from engine.deck_rules import validate_commander_deck


class DeckBuilderDialog(QDialog):
    def __init__(self, card_db_path, banlist_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Commander Deck Builder (Qt)")
        with open(card_db_path,'r',encoding='utf-8') as f:
            self.db = json.load(f)
        self.by_id = {c.get('id'): c for c in self.db if isinstance(c, dict) and c.get('id')}
        self.banned = set()
        if os.path.exists(banlist_path):
            with open(banlist_path,'r',encoding='utf-8') as f:
                for line in f:
                    line=line.strip()
                    if line and not line.startswith('#'):
                        self.banned.add(line)
        self.deck = {'name':'Custom Commander Deck','commander':None,'cards':[]}

        # Widgets
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or type...")
        self.search.textChanged.connect(self._apply_filter)

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._add_card)
        self.results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self._set_commander_from_results)

        self.deck_list = QListWidget()
        self.deck_list.itemDoubleClicked.connect(self._remove_card)
        self.deck_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.deck_list.customContextMenuRequested.connect(self._set_commander_from_deck)

        self.status = QLabel("Ready")
        self.validate_label = QLabel("Validation: —")
        self.save_btn = QPushButton("Save (data/decks/custom_deck.json)")
        self.save_btn.clicked.connect(self._save)

        left = QVBoxLayout()
        left.addWidget(QLabel("Results (dbl‑click add / right‑click commander)"))
        left.addWidget(self.search)
        left.addWidget(self.results)

        right = QVBoxLayout()
        right.addWidget(QLabel("Deck (dbl‑click remove / right‑click commander)"))
        right.addWidget(self.deck_list)
        right.addWidget(self.validate_label)
        right.addWidget(self.save_btn)

        main = QHBoxLayout()
        main.addLayout(left,1)
        main.addLayout(right,1)

        root = QVBoxLayout()
        root.addLayout(main)
        root.addWidget(self.status)
        self.setLayout(root)

        self._apply_filter()

    # ---- Filtering / Display ----
    def _apply_filter(self):
        q = self.search.text().lower().strip()
        self.results.clear()
        if not q:
            pool = self.db[:400]
        else:
            pool = [c for c in self.db
                    if q in c.get('name','').lower()
                    or q in "/".join(c.get('types',[])).lower()][:400]
        for c in pool:
            name = c.get('name','?')
            item = QListWidgetItem(name + (" [BANNED]" if name in self.banned else ""))
            item.setData(Qt.UserRole, c.get('id'))
            self.results.addItem(item)
        self._update_validation()

    def _refresh_deck_list(self):
        self.deck_list.clear()
        for cid in self.deck['cards']:
            nm = self.by_id.get(cid,{}).get('name', cid)
            it = QListWidgetItem(nm)
            it.setData(Qt.UserRole, cid)
            self.deck_list.addItem(it)

    # ---- Actions ----
    def _add_card(self, item: QListWidgetItem):
        cid = item.data(Qt.UserRole)
        card = self.by_id.get(cid)
        if not card: return
        name = card['name']
        if name in self.banned:
            self.status.setText(f"[BAN] {name}")
            return
        # Allow duplicates only for basics (heuristic name startswith)
        basic = name.lower().startswith(('plains','island','swamp','mountain','forest'))
        if basic or cid not in self.deck['cards']:
            self.deck['cards'].append(cid)
            self.status.setText(f"[Add] {name}")
        else:
            self.status.setText(f"[Singleton] {name}")
        self._refresh_deck_list()
        self._update_validation()

    def _remove_card(self, item: QListWidgetItem):
        cid = item.data(Qt.UserRole)
        if cid in self.deck['cards']:
            self.deck['cards'].remove(cid)
            self.status.setText(f"[Remove] {self.by_id.get(cid,{}).get('name',cid)}")
            self._refresh_deck_list()
            self._update_validation()

    def _set_commander_from_results(self, pos):
        item = self.results.itemAt(pos)
        if not item: return
        cid = item.data(Qt.UserRole)
        if cid in self.by_id:
            self.deck['commander'] = cid
            self.status.setText(f"[Commander] {self.by_id[cid]['name']}")
            self._update_validation()

    def _set_commander_from_deck(self, pos):
        item = self.deck_list.itemAt(pos)
        if not item: return
        cid = item.data(Qt.UserRole)
        if cid in self.by_id:
            self.deck['commander'] = cid
            self.status.setText(f"[Commander] {self.by_id[cid]['name']}")
            self._update_validation()

    # ---- Validation / Save ----
    def _update_validation(self):
        cmd = self.deck['commander']
        if not cmd:
            self.validate_label.setText("Validation: Missing commander")
            return
        basic_ok, basic_issues = validate_deck_from_ids(cmd, self.deck['cards'])
        adv_ok, adv_issues = validate_commander_deck(
            commander_id=cmd,
            card_ids=self.deck['cards'],
            card_db=self.db,
            banned=self.banned
        )
        if basic_ok and adv_ok:
            self.validate_label.setText("Validation: OK")
        else:
            merged = list(dict.fromkeys(basic_issues + adv_issues))[:3]
            self.validate_label.setText("Validation: " + "; ".join(merged))

    def _save(self):
        cmd = self.deck.get('commander')
        if not cmd:
            QMessageBox.warning(self,"Save","No commander set.")
            return
        basic_ok, basic_issues = validate_deck_from_ids(cmd, self.deck['cards'])
        adv_ok, adv_issues = validate_commander_deck(cmd, self.deck['cards'], self.db, self.banned)
        if not (basic_ok and adv_ok):
            QMessageBox.warning(self,"Invalid Deck","\n".join(basic_issues + adv_issues))
            return
        out = os.path.join('data','decks','custom_deck.json')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out,'w',encoding='utf-8') as f:
            json.dump(self.deck,f,ensure_ascii=False,indent=2)
        self.status.setText(f"[Saved] {out}")

def run_dialog():
    app = QApplication.instance() or QApplication(sys.argv)
    card_db_path = os.path.join('data','cards','card_db_full.json')
    if not os.path.exists(card_db_path):
        card_db_path = os.path.join('data','cards','card_db.json')
    banlist_path = os.path.join('data','commander_banlist.txt')
    dlg = DeckBuilderDialog(card_db_path, banlist_path)
    dlg.resize(1000,600)
    dlg.exec()

if __name__ == '__main__':
    run_dialog()
    if not os.path.exists(card_db_path):
        print('[INFO] card_db_full.json not found. Use tools/scryfall_filter.py to generate it from Scryfall bulk.')
        sys.exit(0)
    DeckBuilder(card_db_path, banlist_path).run()
    DeckBuilder(card_db_path, banlist_path).run()
