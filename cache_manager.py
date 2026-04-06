import json
import os

# this script is saving the last servers used => when restarting the app you have the last credentials already filled

CACHE_FILE = "servers_cache.json"

def save_to_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_from_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}