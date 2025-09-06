# Deprecated: JSON deck dialog replaced by embedded Decks tab editor using .txt only.
# Keep minimal fallback allowing export to custom_deck.txt for legacy callers.
import os, sys, json
from PySide6.QtWidgets import (QDialog, QApplication, QVBoxLayout, QLabel, QPushButton, QListWidget,
                               QListWidgetItem, QLineEdit, QMessageBox, QHBoxLayout)
from PySide6.QtCore import Qt

def write_txt(path, commander_id, card_ids, db_by_id):
    # Convert IDs to names
    commander_name = db_by_id[commander_id]['name'] if commander_id in db_by_id else commander_id
    names = [db_by_id[c]['name'] for c in card_ids if c in db_by_id and db_by_id[c]['name'] != commander_name]
    counts = {}
    for n in names:
        counts[n] = counts.get(n,0)+1
    lines = [f"Commander: {commander_name}"] + [f"{ct} {n}" for n, ct in sorted(counts.items())]
    with open(path,'w',encoding='utf-8') as f:
        f.write("\n".join(lines)+"\n")
    print(f"[DECK][TXT] Wrote {path}")

class MinimalTxtExporter(QDialog):
    def __init__(self, card_db_path):
        super().__init__()
        self.setWindowTitle("Deck Export (TXT) - Deprecated")
        with open(card_db_path,'r',encoding='utf-8') as f:
            self.db = json.load(f)
        self.by_id = {c.get('id'):c for c in self.db if isinstance(c,dict) and c.get('id')}
        self.ids = list(self.by_id.keys())[:200]
        self.commander = None
        self.search = QLineEdit(); self.search.setPlaceholderText("Type to filter...")
        self.search.textChanged.connect(self._refresh)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._toggle)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._set_commander)
        self.status = QLabel("Choose cards; right-click sets commander.")
        self.save_btn = QPushButton("Export -> data/decks/custom_deck.txt")
        self.save_btn.clicked.connect(self._save)
        lay = QVBoxLayout()
        lay.addWidget(self.search); lay.addWidget(self.list); lay.addWidget(self.status); lay.addWidget(self.save_btn)
        self.setLayout(lay)
        self._refresh()

    def _refresh(self):
        q = self.search.text().lower()
        self.list.clear()
        for cid,c in list(self.by_id.items())[:2000]:
            if q and q not in c['name'].lower(): continue
            it = QListWidgetItem(c['name'] + (" [CMD]" if self.commander==cid else ""))
            it.setData(Qt.UserRole, cid)
            self.list.addItem(it)

    def _toggle(self, item):
        cid = item.data(Qt.UserRole)
        if cid in self.ids:
            self.ids.remove(cid)
        else:
            self.ids.append(cid)
        self.status.setText(f"{len(self.ids)} selected.")

    def _set_commander(self, pos):
        it = self.list.itemAt(pos)
        if not it: return
        self.commander = it.data(Qt.UserRole)
        self._refresh()

    def _save(self):
        if not self.commander:
            QMessageBox.warning(self,"Export","Set commander.")
            return
        out = os.path.join('data','decks','custom_deck.txt')
        write_txt(out, self.commander, self.ids, self.by_id)
        QMessageBox.information(self,"Exported", out)

def run_dialog():
    app = QApplication.instance() or QApplication(sys.argv)
    card_db_path = os.path.join('data','cards','card_db_full.json')
    if not os.path.exists(card_db_path):
        card_db_path = os.path.join('data','cards','card_db.json')
    dlg = MinimalTxtExporter(card_db_path)
    dlg.resize(500,600)
    dlg.exec()

if __name__ == '__main__':
    run_dialog()
