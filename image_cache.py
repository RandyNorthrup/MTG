import os, threading, urllib.request

IMAGE_DIR = os.path.join('data','images','cards')
os.makedirs(IMAGE_DIR, exist_ok=True)

_download_lock = threading.Lock()
_inflight: set[str] = set()

def card_image_path(card_id: str) -> str:
    return os.path.join(IMAGE_DIR, f"{card_id}.jpg")

def ensure_card_image(card_id: str, version: str = "normal") -> str | None:
    """
    Returns local path if image exists or was downloaded successfully, else None.
    Non-blocking if another thread already downloading.
    """
    if not card_id:
        return None
    path = card_image_path(card_id)
    if os.path.exists(path):
        return path

    url = f"https://api.scryfall.com/cards/{card_id}?format=image&version={version}"

    def _dl():
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = resp.read()
            with open(path, 'wb') as f:
                f.write(data)
        except Exception:
            pass
        finally:
            with _download_lock:
                _inflight.discard(card_id)

    with _download_lock:
        if card_id in _inflight:
            return None
        _inflight.add(card_id)
        threading.Thread(target=_dl, daemon=True).start()
    return None
