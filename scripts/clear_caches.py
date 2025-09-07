import os, shutil

CACHE_PATHS = [
    "image_cache",
    "cache",
    "data/cache",
    "__pycache__",
]

def clear():
    for path in CACHE_PATHS:
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                print(f"Removed dir: {path}")
            except Exception as ex:
                print(f"Failed {path}: {ex}")
        elif os.path.isfile(path):
            try:
                os.remove(path)
                print(f"Removed file: {path}")
            except Exception as ex:
                print(f"Failed file {path}: {ex}")

if __name__ == "__main__":
    clear()
