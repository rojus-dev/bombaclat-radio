import os
import shutil
import soundfile as sf

from modules.settings import (
    load_hotkeys,
    load_favorites,
    save_hotkeys,
    save_favorites,
    load_sound_volumes,
    save_sound_volumes
)

SOUNDS_FOLDER = "sounds"
SUPPORTED_FILES = (".mp3", ".wav", ".ogg")

def format_duration(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"

def get_duration(path):
    try:
        info = sf.info(path)
        return format_duration(info.duration)
    except:
        return "?:??"

def unique_path(path):
    if not os.path.exists(path):
        return path

    folder = os.path.dirname(path)
    name, ext = os.path.splitext(os.path.basename(path))
    counter = 2

    while True:
        new_path = os.path.join(folder, f"{name}_{counter}{ext}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def get_sounds():
    hotkeys = load_hotkeys()
    volumes = load_sound_volumes()
    sounds = []
    counter = 1

    os.makedirs(SOUNDS_FOLDER, exist_ok=True)

    for root_dir, dirs, files in os.walk(SOUNDS_FOLDER):
        dirs.sort()
        files.sort()

        for file in files:
            if not file.lower().endswith(SUPPORTED_FILES):
                continue

            path = os.path.join(root_dir, file)
            rel_folder = os.path.relpath(root_dir, SOUNDS_FOLDER)
            category = "Uncategorized" if rel_folder == "." else rel_folder
            key_id = os.path.relpath(path, SOUNDS_FOLDER).replace("\\", "/")

            sounds.append({
                "file": key_id,
                "name": os.path.splitext(file)[0],
                "path": path,
                "category": category,
                "hotkey": hotkeys.get(key_id, f"num {counter}"),
                "duration": get_duration(path),
                "volume": volumes.get(key_id, 100)
            })

            counter += 1

    return sounds

def update_references(old_id, new_id):
    hotkeys = load_hotkeys()
    favorites = load_favorites()
    volumes = load_sound_volumes()

    if old_id in hotkeys:
        hotkeys[new_id] = hotkeys.pop(old_id)
        save_hotkeys(hotkeys)

    if old_id in favorites:
        favorites.remove(old_id)
        favorites.append(new_id)
        save_favorites(favorites)

    if old_id in volumes:
        volumes[new_id] = volumes.pop(old_id)
        save_sound_volumes(volumes)

def import_sound_file(file_path, category):
    target_folder = os.path.join(SOUNDS_FOLDER, category)
    os.makedirs(target_folder, exist_ok=True)

    target_path = unique_path(os.path.join(target_folder, os.path.basename(file_path)))
    shutil.copy2(file_path, target_path)
    return target_path

def rename_sound(sound, new_name):
    folder = os.path.dirname(sound["path"])
    ext = os.path.splitext(sound["path"])[1]
    new_path = unique_path(os.path.join(folder, new_name + ext))

    old_id = sound["file"]
    os.rename(sound["path"], new_path)

    new_id = os.path.relpath(new_path, SOUNDS_FOLDER).replace("\\", "/")
    update_references(old_id, new_id)

def move_sound(sound, new_category):
    target_folder = os.path.join(SOUNDS_FOLDER, new_category)
    os.makedirs(target_folder, exist_ok=True)

    new_path = unique_path(os.path.join(target_folder, os.path.basename(sound["path"])))

    old_id = sound["file"]
    shutil.move(sound["path"], new_path)

    new_id = os.path.relpath(new_path, SOUNDS_FOLDER).replace("\\", "/")
    update_references(old_id, new_id)

def delete_sound(sound):
    favorites = load_favorites()
    hotkeys = load_hotkeys()
    volumes = load_sound_volumes()

    if sound["file"] in favorites:
        favorites.remove(sound["file"])
        save_favorites(favorites)

    if sound["file"] in hotkeys:
        del hotkeys[sound["file"]]
        save_hotkeys(hotkeys)

    if sound["file"] in volumes:
        del volumes[sound["file"]]
        save_sound_volumes(volumes)

    os.remove(sound["path"])

def set_sound_volume(sound_file, volume):
    volumes = load_sound_volumes()
    volumes[sound_file] = int(volume)
    save_sound_volumes(volumes)
