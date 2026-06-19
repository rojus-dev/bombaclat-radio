import keyboard

print("Press keys... ESC to quit")

while True:
    event = keyboard.read_event()

    if event.event_type == keyboard.KEY_DOWN:
        print(
            f"name='{event.name}' "
            f"scan_code={event.scan_code}"
        )

        if event.name == "esc":
            break