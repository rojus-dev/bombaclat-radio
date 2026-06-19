import keyboard

NUMPAD_SCAN_CODES = {
    "num 1": 79,
    "num 2": 80,
    "num 3": 81,
    "num 4": 75,
    "num 5": 76,
    "num 6": 77,
    "num 7": 71,
    "num 8": 72,
    "num 9": 73,
    "num 0": 82,
}

class HotkeyManager:
    def __init__(self):
        self.conflicts = []

    def register(self, sounds, play_callback, random_callback, stop_callback, stop_hotkey="f9"):
        keyboard.unhook_all()
        self.conflicts.clear()

        used = {}

        for sound in sounds:
            hotkey = sound["hotkey"].lower().strip()

            if hotkey in used:
                self.conflicts.append(hotkey)
                continue

            used[hotkey] = sound["name"]

            try:
                if hotkey in NUMPAD_SCAN_CODES:
                    keyboard.on_press_key(
                        NUMPAD_SCAN_CODES[hotkey],
                        lambda e, s=sound: play_callback(s),
                        suppress=False
                    )
                else:
                    keyboard.add_hotkey(
                        hotkey,
                        lambda s=sound: play_callback(s)
                    )

            except Exception as e:
                print(f"Could not register {hotkey}: {e}")

        keyboard.add_hotkey("f8", random_callback)

        stop_hotkey = stop_hotkey.lower().strip()
        if stop_hotkey in NUMPAD_SCAN_CODES:
            keyboard.on_press_key(
                NUMPAD_SCAN_CODES[stop_hotkey],
                lambda e: stop_callback(),
                suppress=False
            )
        else:
            keyboard.add_hotkey(stop_hotkey, stop_callback)

        return self.conflicts