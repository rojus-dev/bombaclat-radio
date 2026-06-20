import keyboard

NUMPAD_KEYS = {
    "num 0": ("0", 82),
    "num 1": ("1", 79),
    "num 2": ("2", 80),
    "num 3": ("3", 81),
    "num 4": ("4", 75),
    "num 5": ("5", 76),
    "num 6": ("6", 77),
    "num 7": ("7", 71),
    "num 8": ("8", 72),
    "num 9": ("9", 73),
}

class HotkeyManager:
    def __init__(self):
        self.conflicts = []

    def is_numpad_event(self, event, hotkey):
        wanted_name, wanted_scan = NUMPAD_KEYS[hotkey]

        return (
            event.event_type == keyboard.KEY_DOWN
            and event.scan_code == wanted_scan
            and event.name == wanted_name
            and getattr(event, "is_keypad", False)
        )

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
                if hotkey in NUMPAD_KEYS:
                    keyboard.hook(
                        lambda event, s=sound, h=hotkey:
                            play_callback(s) if self.is_numpad_event(event, h) else None
                    )
                else:
                    keyboard.add_hotkey(
                        hotkey,
                        lambda s=sound: play_callback(s)
                    )

            except Exception as e:
                print(f"Could not register {hotkey}: {e}")

        keyboard.add_hotkey("f8", random_callback)
        keyboard.add_hotkey(stop_hotkey, stop_callback)

        return self.conflicts