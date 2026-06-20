import json
import os

APP_NAME = "BombaclatSoundboard"
APP_DATA_FOLDER = os.path.join(os.getenv("APPDATA", os.getcwd()), APP_NAME)

os.makedirs(APP_DATA_FOLDER, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_DATA_FOLDER, "settings.json")
HOTKEY_FILE = os.path.join(APP_DATA_FOLDER, "hotkeys.json")
FAVORITES_FILE = os.path.join(APP_DATA_FOLDER, "favorites.json")
VOLUMES_FILE = os.path.join(APP_DATA_FOLDER, "sound_volumes.json")
PLAY_COUNTS_FILE = os.path.join(APP_DATA_FOLDER, "play_counts.json")

DEFAULT_SETTINGS = {
    "startup_volume": 80,
    "default_category": "memes",
    "auto_refresh": True,
    "output_device": "",
    "window_geometry": "1100x760",
    "stop_hotkey": "f9"
}

def load_json(path, default):
    if not os.path.exists(path):
        return default.copy() if isinstance(default, dict) else default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return default.copy() if isinstance(default, dict) else default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def load_settings():
    data = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    return merged

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def load_hotkeys():
    return load_json(HOTKEY_FILE, {})

def save_hotkeys(hotkeys):
    save_json(HOTKEY_FILE, hotkeys)

def load_favorites():
    data = load_json(FAVORITES_FILE, {"favorites": []})
    return data.get("favorites", [])

def save_favorites(favorites):
    save_json(FAVORITES_FILE, {"favorites": favorites})

def load_sound_volumes():
    return load_json(VOLUMES_FILE, {})

def save_sound_volumes(volumes):
    save_json(VOLUMES_FILE, volumes)

def get_app_data_folder():
    return APP_DATA_FOLDER

def load_play_counts():
    return load_json(PLAY_COUNTS_FILE, {})

def save_play_counts(counts):
    save_json(PLAY_COUNTS_FILE, counts)

def increment_play_count(sound_file):
    counts = load_play_counts()
    counts[sound_file] = counts.get(sound_file, 0) + 1
    save_play_counts(counts)

def get_top_play_counts(limit=5):
    counts = load_play_counts()
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]