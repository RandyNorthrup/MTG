import os
import shutil
import threading
import time
import urllib.request
import tempfile
from typing import Dict, Tuple, Optional

_lock = threading.RLock()
_meta: Dict[str, Tuple[str, float]] = {}   # card_id -> (path, last_access_epoch)
_qt_timer = None

SESSION_DIR = os.path.join(tempfile.gettempdir(), "mtg_img_session")

# -------- Tunables (env overridable) --------
MAX_CACHE_IMAGES = int(os.environ.get("MTG_IMG_CACHE_MAX", "400"))
CACHE_TTL_SEC    = int(os.environ.get("MTG_IMG_CACHE_TTL", "14400"))   # 4h metadata retention
EVICT_BATCH      = int(os.environ.get("MTG_IMG_CACHE_BATCH", "30"))
CLEAN_INTERVAL   = int(os.environ.get("MTG_IMG_CLEAN_INTERVAL", "600"))
REQ_TIMEOUT      = int(os.environ.get("MTG_IMG_HTTP_TIMEOUT", "12"))

# -------- Directories --------
LEGACY_DIR  = os.path.join("data", "img_cache")             # persistent store

os.makedirs(LEGACY_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)

# -------- Helpers --------
def _now() -> float:
    return time.time()

def _safe_remove(path: str):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass

def _is_valid_image(path: str) -> bool:
    """
    Check if image exists, is large enough, and can be loaded by QPixmap if possible.
    """
    try:
        if not os.path.isfile(path):
            return False
        if os.path.getsize(path) < 512:
            return False
        try:
            from PySide6.QtWidgets import QApplication  # type: ignore
            if QApplication.instance() is not None:
                from PySide6.QtGui import QPixmap  # type: ignore
                pm = QPixmap(path)
                if pm.isNull():
                    return False
        except Exception:
            pass
        return True
    except Exception:
        return False

def _legacy_candidate(card_id: str) -> Optional[str]:
    for ext in (".jpg", ".png"):
        p = os.path.join(LEGACY_DIR, card_id + ext)
        if os.path.exists(p):
            return p
    return None

def _evict():
    cutoff = _now() - CACHE_TTL_SEC
    expired = [cid for cid, (_, ts) in _meta.items() if ts < cutoff]
    for cid in expired:
        _meta.pop(cid, None)
    if len(_meta) <= MAX_CACHE_IMAGES:
        return
    victims = sorted(_meta.items(), key=lambda kv: kv[1][1])[:EVICT_BATCH]
    for cid, _ in victims:
        _meta.pop(cid, None)

def _download_scryfall(card_id: str, dest: str) -> bool:
    if os.environ.get("MTG_NO_IMAGE_DL"):
        return False
    url = f"https://api.scryfall.com/cards/{card_id}?format=image&version=normal"
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MTGClient/1.0"})
        with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        if _is_valid_image(tmp):
            if os.path.exists(dest):
                _safe_remove(dest)
            os.replace(tmp, dest)
            return True
    except Exception:
        pass
    _safe_remove(tmp)
    return False

# -------- Public API --------
def ensure_card_image(card_id: str) -> Optional[str]:
    """
    Return path to a valid image (downloaded once). None if unavailable.
    """
    if not card_id:
        return None

    legacy = _legacy_candidate(card_id)
    if legacy:
        if _is_valid_image(legacy):
            with _lock:
                _meta[card_id] = (legacy, _now())
                _evict()
            return legacy
        _safe_remove(legacy)

    target = os.path.join(LEGACY_DIR, f"{card_id}.jpg")
    if _download_scryfall(card_id, target):
        with _lock:
            _meta[card_id] = (target, _now())
            _evict()
        return target
    return None

def cleanup_cache(force: bool = False):
    """
    Evict stale metadata. If force=True, also clear session dir.
    """
    with _lock:
        if force:
            _meta.clear()
            for fn in os.listdir(SESSION_DIR):
                _safe_remove(os.path.join(SESSION_DIR, fn))
            return
        _evict()

def repair_cache():
    """
    Remove corrupt or undersized images.
    """
    removed = 0
    for root in (LEGACY_DIR, SESSION_DIR):
        if not os.path.isdir(root):
            continue
        for fn in os.listdir(root):
            if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            fp = os.path.join(root, fn)
            if not _is_valid_image(fp):
                _safe_remove(fp)
                removed += 1
    if removed:
        print(f"[IMG-CACHE] Pruned {removed} corrupt image file(s).")

def init_image_cache(qt_parent=None, interval_sec: int = CLEAN_INTERVAL):
    """
    Optionally start a Qt timer for periodic cache cleanup.
    """
    global _qt_timer
    if _qt_timer:
        return _qt_timer
    try:
        from PySide6.QtCore import QTimer  # type: ignore
    except Exception:
        return None
    _qt_timer = QTimer(qt_parent)
    _qt_timer.setInterval(int(interval_sec * 1000))
    _qt_timer.timeout.connect(cleanup_cache)
    _qt_timer.start()
    return _qt_timer

def teardown_cache():
    """
    Clear ephemeral metadata and session folder (persistent images remain).
    """
    try:
        cleanup_cache(force=True)
        shutil.rmtree(SESSION_DIR, ignore_errors=True)
    except Exception:
        pass
        cleanup_cache(force=True)
        shutil.rmtree(SESSION_DIR, ignore_errors=True)
    except Exception:
        pass
        pass
