import json
import os

CACHE_FILE = "servers_cache.json"

def save_to_cache(data):
    """Salvează un dicționar Python în fișierul JSON."""
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_from_cache():
    """Încarcă datele. Dacă fișierul nu există, returnează un dicționar gol."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}