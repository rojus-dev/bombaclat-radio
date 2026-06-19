import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import os
import random

from modules.settings import (
    load_settings,
    save_settings,
    load_hotkeys,
    save_hotkeys,
    load_favorites,
    save_favorites
)

from modules.sounds import (
    get_sounds,
    import_sound_file,
    rename_sound,
    move_sound,
    delete_sound,
    set_sound_volume
)

from modules.audio import AudioEngine
from modules.hotkeys import HotkeyManager
from tkinterdnd2 import DND_FILES

# ---- palette ---------------------------------------------------------
# Neutral chrome (sidebar / panels / cards) + a small set of accent
# colors that carry meaning instead of decorating everything.

BG = "#1e1e2e"          # app background
PANEL = "#181825"       # sidebar / side panel background
SURFACE = "#11111b"     # recessed surfaces (now playing box)
CARD = "#232336"        # default sound card background
BORDER = "#313244"      # default card / divider border
TEXT = "#ffffff"
TEXT_MUTED = "#a6adc8"
TEXT_DIM = "#6c7086"

AMBER = "#f9e2af"       # favorites
AMBER_DARK = "#3a341f"
BLUE = "#89b4fa"        # currently playing / active nav
BLUE_DARK = "#1c2b40"
RED = "#f38ba8"         # stop / danger
GREEN = "#a6e3a1"       # ready / success / play button

# rotating accent ramp used for categories, so each one is visually
# distinct but nothing screams louder than favorites/playing/stop
CATEGORY_RAMP = [
    {"fg": "#f0997b", "bg": "#3a261d", "name": "coral"},
    {"fg": "#cba6f7", "bg": "#2c2540", "name": "purple"},
    {"fg": "#5dcaa5", "bg": "#173430", "name": "teal"},
    {"fg": "#f5a3c7", "bg": "#3a2030", "name": "pink"},
    {"fg": "#85b7eb", "bg": "#1c2b40", "name": "blue"},
    {"fg": "#a6e3a1", "bg": "#223a1c", "name": "green"},
    {"fg": "#fab387", "bg": "#3a2a18", "name": "orange"},
]

ICONS = {
    "all": "◆",
    "favorites": "★",
    "settings": "⚙",
    "category": "▸",
}


class SoundboardApp:
    def __init__(self, root_class=tk.Tk):
        self.settings = load_settings()
        self.audio = AudioEngine(self.settings)
        self.hotkeys = HotkeyManager()
        self.card_widgets = {}
        self.category_colors = {}
        self.active_filter = "all"  # "all" | "favorites" | category name

        self.root = root_class()
        self.root.title("Soundboard")
        self.root.geometry(self.settings.get("window_geometry", "1100x760"))
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()
        self.setup_drag_and_drop()
        self.refresh_app()
        self.update_now_playing()

    def run(self):
        self.root.mainloop()

    def on_close(self):
        self.settings["window_geometry"] = self.root.geometry()
        save_settings(self.settings)
        self.audio.stop_all()
        self.root.destroy()

    # ---- color helpers -------------------------------------------------

    def color_for_category(self, category):
        if category not in self.category_colors:
            index = len(self.category_colors) % len(CATEGORY_RAMP)
            self.category_colors[category] = CATEGORY_RAMP[index]
        return self.category_colors[category]

    # ---- layout ----------------------------------------------------------

    def build_ui(self):
        root_area = tk.Frame(self.root, bg=BG)
        root_area.pack(fill="both", expand=True)

        self.build_sidebar(root_area)

        self.center_area = tk.Frame(root_area, bg=BG)
        self.center_area.pack(side="left", fill="both", expand=True)

        self.sounds_page = tk.Frame(self.center_area, bg=BG)
        self.sounds_page.pack(fill="both", expand=True)

        self.build_toolbar(self.sounds_page)
        self.build_sound_list(self.sounds_page)
        self.build_footer(self.sounds_page)

        self.settings_page = tk.Frame(self.center_area, bg=BG)
        self.build_settings_page(self.settings_page)

        self.build_right_panel(root_area)

    def build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=PANEL, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="Soundboard",
            font=("Segoe UI", 14, "bold"),
            bg=PANEL,
            fg=TEXT
        ).pack(anchor="w", padx=16, pady=(18, 14))

        self.nav_frame = tk.Frame(sidebar, bg=PANEL)
        self.nav_frame.pack(fill="x")

        self.nav_buttons = {}
        self.add_nav_item("all", "All sounds", ICONS["all"], BLUE)
        self.add_nav_item("favorites", "Favorites", ICONS["favorites"], AMBER)

        self.category_nav_frame = tk.Frame(sidebar, bg=PANEL)
        self.category_nav_frame.pack(fill="x", pady=(10, 0))

        tk.Frame(sidebar, bg=PANEL).pack(fill="both", expand=True)  # spacer

        settings_row = tk.Frame(sidebar, bg=PANEL)
        settings_row.pack(fill="x", side="bottom", pady=14)

        self.add_nav_row(
            settings_row, "⚙ Settings", TEXT_MUTED, self.open_settings
        )

    def add_nav_item(self, key, label, icon, accent):
        row = tk.Frame(self.nav_frame, bg=PANEL, cursor="hand2")
        row.pack(fill="x", padx=8, pady=2)

        text_label = tk.Label(
            row,
            text=f"{icon}  {label}",
            font=("Segoe UI", 11),
            bg=PANEL,
            fg=TEXT_MUTED,
            anchor="w",
            padx=10,
            pady=7
        )
        text_label.pack(fill="x")

        for widget in (row, text_label):
            widget.bind("<Button-1>", lambda e, k=key: self.set_filter(k))

        self.nav_buttons[key] = {"row": row, "label": text_label, "accent": accent}

    def add_nav_row(self, parent, label, color, command):
        row_label = tk.Label(
            parent,
            text=label,
            font=("Segoe UI", 11),
            bg=PANEL,
            fg=color,
            anchor="w",
            padx=18,
            pady=6,
            cursor="hand2"
        )
        row_label.pack(fill="x")
        row_label.bind("<Button-1>", lambda e: command())

    def rebuild_category_nav(self, categories):
        for widget in self.category_nav_frame.winfo_children():
            widget.destroy()

        for key in list(self.nav_buttons.keys()):
            if key not in ("all", "favorites"):
                del self.nav_buttons[key]

        for category in categories:
            color = self.color_for_category(category)
            row = tk.Frame(self.category_nav_frame, bg=PANEL, cursor="hand2")
            row.pack(fill="x", padx=8, pady=2)

            text_label = tk.Label(
                row,
                text=f"{ICONS['category']}  {category}",
                font=("Segoe UI", 11),
                bg=PANEL,
                fg=TEXT_MUTED,
                anchor="w",
                padx=10,
                pady=7
            )
            text_label.pack(fill="x")

            for widget in (row, text_label):
                widget.bind("<Button-1>", lambda e, c=category: self.set_filter(c))

            self.nav_buttons[category] = {"row": row, "label": text_label, "accent": color["fg"]}

        self.refresh_nav_highlight()

    def set_filter(self, key):
        self.active_filter = key
        if hasattr(self, "settings_page"):
            self.settings_page.pack_forget()
        if hasattr(self, "sounds_page") and not self.sounds_page.winfo_ismapped():
            self.sounds_page.pack(fill="both", expand=True)
        self.refresh_nav_highlight()
        self.refresh_buttons(self.search_var.get())

    def refresh_nav_highlight(self):
        for key, widgets in self.nav_buttons.items():
            active = key == self.active_filter
            bg = widgets["accent"] if active else PANEL
            fg = "#11111b" if active else TEXT_MUTED

            # use a tinted bg rather than the raw accent so text stays readable
            if active:
                widgets["row"].config(bg=self._tint(widgets["accent"]))
                widgets["label"].config(bg=self._tint(widgets["accent"]), fg=widgets["accent"], font=("Segoe UI", 11, "bold"))
            else:
                widgets["row"].config(bg=PANEL)
                widgets["label"].config(bg=PANEL, fg=TEXT_MUTED, font=("Segoe UI", 11))

    def _tint(self, hex_color):
        # darken an accent color for use as a subtle selected-row background
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * 0.18), int(g * 0.18), int(b * 0.18)
        return f"#{r:02x}{g:02x}{b:02x}"

    def build_toolbar(self, parent):
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(16, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_buttons(self.search_var.get()))

        search_entry = tk.Entry(
            toolbar,
            textvariable=self.search_var,
            font=("Segoe UI", 12),
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat"
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

        self.make_button(toolbar, "Import", "#74c7ec", self.import_sound)
        self.make_button(toolbar, "Random", "#cba6f7", self.play_random_sound)
        self.make_button(toolbar, "Stop", RED, self.stop_all)
        self.make_button(toolbar, "Refresh", GREEN, self.refresh_app)

    def make_button(self, parent, text, color, command):
        tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=color,
            fg="#11111b",
            relief="flat",
            padx=14,
            pady=8,
            command=command
        ).pack(side="left", padx=3)

    def build_sound_list(self, parent):
        list_area = tk.Frame(parent, bg=BG)
        list_area.pack(fill="both", expand=True, padx=16)

        self.canvas = tk.Canvas(list_area, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_area, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.scrollable_frame = tk.Frame(self.canvas, bg=BG)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def build_footer(self, parent):
        footer = tk.Frame(parent, bg=BG)
        footer.pack(fill="x", padx=16, pady=10)

        tk.Label(
            footer,
            text="Volume",
            font=("Segoe UI", 10),
            bg=BG,
            fg=TEXT_MUTED
        ).pack(side="left")

        self.volume_slider = tk.Scale(
            footer,
            from_=0,
            to=100,
            orient="horizontal",
            length=200,
            command=self.set_volume,
            bg=BG,
            fg=TEXT,
            troughcolor=CARD,
            highlightthickness=0,
            showvalue=False
        )
        self.volume_slider.set(self.settings.get("startup_volume", 80))
        self.volume_slider.pack(side="left", padx=10)

        self.volume_text = tk.Label(
            footer,
            text=f"{self.settings.get('startup_volume', 80)}%",
            font=("Segoe UI", 10),
            bg=BG,
            fg=TEXT_MUTED,
            width=4
        )
        self.volume_text.pack(side="left")

        self.status_label = tk.Label(
            footer,
            text="Ready",
            font=("Segoe UI", 10),
            bg=BG,
            fg=GREEN
        )
        self.status_label.pack(side="right")

    def build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=PANEL, width=220)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="NOW PLAYING",
            font=("Segoe UI", 10, "bold"),
            bg=PANEL,
            fg=TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(18, 8))

        self.now_playing_frame = tk.Frame(panel, bg=PANEL)
        self.now_playing_frame.pack(fill="x", padx=16)

        self.now_playing_empty = tk.Label(
            self.now_playing_frame,
            text="Nothing playing",
            font=("Segoe UI", 10),
            bg=PANEL,
            fg=TEXT_DIM,
            anchor="w"
        )
        self.now_playing_empty.pack(fill="x", pady=4)

        tk.Frame(panel, bg=BORDER, height=1).pack(fill="x", padx=16, pady=16)

        tk.Label(
            panel,
            text="STATS",
            font=("Segoe UI", 10, "bold"),
            bg=PANEL,
            fg=TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.stats_label = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 10),
            bg=PANEL,
            fg=TEXT,
            justify="left",
            anchor="w",
            wraplength=190
        )
        self.stats_label.pack(fill="x", padx=16)

    # ---- drag and drop -----------------------------------------------

    def setup_drag_and_drop(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_drop)

    def handle_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        imported = 0

        for file_path in files:
            if not file_path.lower().endswith((".mp3", ".wav", ".ogg")):
                continue

            category = self.settings.get("default_category", "memes")
            import_sound_file(file_path, category)
            imported += 1

        if imported > 0:
            self.status_label.config(text=f"Imported {imported} sound(s)", fg=GREEN)
            self.refresh_app()
        else:
            self.status_label.config(text="No supported audio files dropped", fg=RED)

    # ---- volume / playback --------------------------------------------

    def set_volume(self, value):
        self.audio.set_volume(value)
        self.settings["startup_volume"] = int(float(value))
        save_settings(self.settings)
        self.volume_text.config(text=f"{int(float(value))}%")

    def play_sound(self, sound):
        try:
            self.audio.play_sound(
                sound["path"],
                sound["name"],
                sound["file"],
                sound.get("volume", 100)
            )
            self.status_label.config(text=f"Playing: {sound['name']}", fg=GREEN)
            self.flash_card(sound["file"])
        except Exception as e:
            self.status_label.config(text=f"Audio error: {e}", fg=RED)

    def play_random_sound(self):
        sounds = get_sounds()

        if not sounds:
            return

        sound = random.choice(sounds)
        self.play_sound(sound)

    def stop_all(self):
        self.audio.stop_all()
        self.status_label.config(text="Stopped all sounds", fg="#fab387")

    def update_now_playing(self):
        self.audio.cleanup_finished()

        for widget in self.now_playing_frame.winfo_children():
            widget.destroy()

        if self.audio.now_playing:
            for player in self.audio.now_playing:
                row = tk.Frame(self.now_playing_frame, bg=SURFACE)
                row.pack(fill="x", pady=3)
                tk.Label(
                    row,
                    text=f"▶ {player.name}",
                    font=("Segoe UI", 10, "bold"),
                    bg=SURFACE,
                    fg=BLUE,
                    anchor="w",
                    padx=10,
                    pady=8
                ).pack(fill="x")
        else:
            self.now_playing_empty = tk.Label(
                self.now_playing_frame,
                text="Nothing playing",
                font=("Segoe UI", 10),
                bg=PANEL,
                fg=TEXT_DIM,
                anchor="w"
            )
            self.now_playing_empty.pack(fill="x", pady=4)

        self.root.after(500, self.update_now_playing)

    def flash_card(self, file_id):
        if file_id not in self.card_widgets:
            return

        original = self.card_widgets[file_id]["bg"]

        for widget in self.card_widgets[file_id]["widgets"]:
            widget.config(bg="#2f5d3a")

        self.root.after(700, lambda: self.reset_card_color(file_id, original))

    def reset_card_color(self, file_id, original):
        if file_id not in self.card_widgets:
            return

        for widget in self.card_widgets[file_id]["widgets"]:
            widget.config(bg=original)

    def toggle_favorite(self, sound):
        favorites = load_favorites()

        if sound["file"] in favorites:
            favorites.remove(sound["file"])
        else:
            favorites.append(sound["file"])

        save_favorites(favorites)
        self.refresh_app()

    def import_sound(self):
        file_path = filedialog.askopenfilename(
            title="Choose sound",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg")]
        )

        if not file_path:
            return

        category = simpledialog.askstring(
            "Category",
            "Category name:",
            initialvalue=self.settings.get("default_category", "memes")
        ) or "memes"

        target_path = import_sound_file(file_path, category)

        self.status_label.config(text=f"Imported: {os.path.basename(target_path)}", fg=GREEN)

        if self.settings.get("auto_refresh", True):
            self.refresh_app()

    def open_context_menu(self, event, sound):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Rename", command=lambda: self.rename_sound_ui(sound))
        menu.add_command(label="Move Category", command=lambda: self.move_sound_ui(sound))
        menu.add_command(label="Delete", command=lambda: self.delete_sound_ui(sound))
        menu.tk_popup(event.x_root, event.y_root)

    def rename_sound_ui(self, sound):
        new_name = simpledialog.askstring("Rename", "New sound name:", initialvalue=sound["name"])

        if new_name:
            rename_sound(sound, new_name)
            self.refresh_app()

    def move_sound_ui(self, sound):
        new_category = simpledialog.askstring("Move Category", "New category:", initialvalue=sound["category"])

        if new_category:
            move_sound(sound, new_category)
            self.refresh_app()

    def delete_sound_ui(self, sound):
        if messagebox.askyesno("Delete", f"Delete {sound['name']}?"):
            delete_sound(sound)
            self.refresh_app()

    # ---- sound cards -----------------------------------------------------

    def clear_sound_cards(self):
        self.card_widgets.clear()

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def create_header(self, text, color=TEXT_MUTED):
        tk.Label(
            self.scrollable_frame,
            text=text,
            bg=BG,
            fg=color,
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(16, 6))

    def create_sound_card(self, sound, is_favorite):
        is_playing = any(p.file_id == sound["file"] for p in self.audio.now_playing)
        category_color = self.color_for_category(sound["category"])

        if is_playing:
            card_bg = BLUE_DARK
            border_color = BLUE
            border_width = 2
        elif is_favorite:
            card_bg = AMBER_DARK
            border_color = AMBER
            border_width = 1
        else:
            card_bg = category_color["bg"]
            border_color = BORDER
            border_width = 1

        card = tk.Frame(
            self.scrollable_frame,
            bg=card_bg,
            highlightbackground=border_color,
            highlightcolor=border_color,
            highlightthickness=border_width
        )
        card.pack(fill="x", pady=5)

        left = tk.Frame(card, bg=card_bg)
        left.pack(side="left", fill="both", expand=True, padx=14, pady=11)

        name_text = sound["name"]
        if is_playing:
            name_text = f"▶ {name_text}"

        name_label = tk.Label(
            left,
            text=name_text,
            bg=card_bg,
            fg=BLUE if is_playing else TEXT,
            font=("Segoe UI", 13, "bold"),
            anchor="w"
        )
        name_label.pack(fill="x")

        info_label = tk.Label(
            left,
            text=(
                f"{sound['category']}   ·   "
                f"{sound['hotkey'].upper()}   ·   "
                f"{sound['duration']}   ·   "
                f"{sound.get('volume', 100)}%"
            ),
            bg=card_bg,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9),
            anchor="w"
        )
        info_label.pack(fill="x", pady=(4, 0))

        right = tk.Frame(card, bg=card_bg)
        right.pack(side="right", padx=10, pady=10)

        tk.Button(
            right,
            text="▶",
            font=("Segoe UI", 12, "bold"),
            bg=GREEN,
            fg="#11111b",
            relief="flat",
            width=3,
            command=lambda s=sound: self.play_sound(s)
        ).grid(row=0, column=0, padx=3)

        tk.Button(
            right,
            text="★" if is_favorite else "☆",
            font=("Segoe UI", 12, "bold"),
            bg=AMBER if is_favorite else BORDER,
            fg="#11111b" if is_favorite else TEXT,
            relief="flat",
            width=3,
            command=lambda s=sound: self.toggle_favorite(s)
        ).grid(row=0, column=1, padx=3)

        tk.Button(
            right,
            text="Edit",
            font=("Segoe UI", 9, "bold"),
            bg=BLUE,
            fg="#11111b",
            relief="flat",
            width=5,
            command=lambda s=sound: self.open_hotkey_editor(s)
        ).grid(row=0, column=2, padx=3)

        tk.Button(
            right,
            text="Vol",
            font=("Segoe UI", 9, "bold"),
            bg="#fab387",
            fg="#11111b",
            relief="flat",
            width=4,
            command=lambda s=sound: self.open_volume_editor(s)
        ).grid(row=0, column=3, padx=3)

        for widget in [card, left, name_label, info_label]:
            widget.bind("<Button-1>", lambda e, s=sound: self.play_sound(s))
            widget.bind("<Button-3>", lambda e, s=sound: self.open_context_menu(e, s))

        self.card_widgets[sound["file"]] = {
            "widgets": [card, left, name_label, info_label],
            "bg": card_bg
        }

    def refresh_buttons(self, filter_text=""):
        self.clear_sound_cards()

        sounds = get_sounds()
        favorites = load_favorites()
        filter_text = filter_text.lower().strip()

        categories = sorted(set(sound["category"] for sound in sounds))
        for category in categories:
            self.color_for_category(category)

        filtered = [
            sound for sound in sounds
            if filter_text in sound["name"].lower()
            or filter_text in sound["category"].lower()
            or filter_text in sound["hotkey"].lower()
        ]

        if self.active_filter == "favorites":
            filtered = [s for s in filtered if s["file"] in favorites]
        elif self.active_filter != "all":
            filtered = [s for s in filtered if s["category"] == self.active_filter]

        if not filtered:
            tk.Label(
                self.scrollable_frame,
                text="No sounds found.",
                bg=BG,
                fg=RED,
                font=("Segoe UI", 12)
            ).pack(pady=20)
            return

        # only show the pinned favorites strip on the "all" view, so
        # favorites/category filters don't show duplicated headers
        if self.active_filter == "all":
            favorite_sounds = [sound for sound in filtered if sound["file"] in favorites]

            if favorite_sounds:
                self.create_header("★ FAVORITES", AMBER)
                for sound in favorite_sounds:
                    self.create_sound_card(sound, True)

            current_category = None

            for sound in filtered:
                if sound["category"] != current_category:
                    current_category = sound["category"]
                    color = self.color_for_category(current_category)
                    self.create_header(current_category.upper(), color["fg"])

                self.create_sound_card(sound, sound["file"] in favorites)
        else:
            for sound in filtered:
                self.create_sound_card(sound, sound["file"] in favorites)

    def update_stats(self):
        sounds = get_sounds()
        favorites = load_favorites()
        categories = sorted(set(sound["category"] for sound in sounds))
        device = self.settings.get("output_device", "Default") or "Default"

        self.stats_label.config(
            text=f"Sounds: {len(sounds)}\nFavorites: {len(favorites)}\nCategories: {len(categories)}\n\nOutput:\n{device[:24]}"
        )

    def refresh_app(self):
        sounds = get_sounds()
        categories = sorted(set(sound["category"] for sound in sounds))
        self.rebuild_category_nav(categories)

        self.refresh_buttons(self.search_var.get())

        conflicts = self.hotkeys.register(
            sounds=sounds,
            play_callback=self.play_sound,
            random_callback=self.play_random_sound,
            stop_callback=self.stop_all,
            stop_hotkey=self.settings.get("stop_hotkey", "f9")
        )

        self.update_stats()

        if conflicts:
            self.status_label.config(text=f"Hotkey conflict: {', '.join(conflicts)}", fg=RED)

    # ---- dialogs -------------------------------------------------------

    def open_hotkey_editor(self, sound):
        editor = tk.Toplevel(self.root)
        editor.title("Edit Hotkey")
        editor.geometry("360x190")
        editor.configure(bg=BG)
        editor.resizable(False, False)

        tk.Label(
            editor,
            text=f"Sound: {sound['name']}",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=12)

        tk.Label(
            editor,
            text="Example: num 1, f1, ctrl+shift+a",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9)
        ).pack()

        hotkey_entry = tk.Entry(
            editor,
            font=("Segoe UI", 12),
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            justify="center"
        )
        hotkey_entry.insert(0, sound["hotkey"])
        hotkey_entry.pack(pady=12, ipadx=10, ipady=6)

        def save_new_hotkey():
            new_hotkey = hotkey_entry.get().strip().lower()

            if not new_hotkey:
                return

            hotkeys = load_hotkeys()
            hotkeys[sound["file"]] = new_hotkey
            save_hotkeys(hotkeys)

            editor.destroy()
            self.refresh_app()

        tk.Button(
            editor,
            text="Save Hotkey",
            font=("Segoe UI", 11, "bold"),
            bg=BLUE,
            fg="#11111b",
            relief="flat",
            command=save_new_hotkey
        ).pack(ipadx=20, ipady=6)

    def open_volume_editor(self, sound):
        editor = tk.Toplevel(self.root)
        editor.title("Sound Volume")
        editor.geometry("340x190")
        editor.configure(bg=BG)
        editor.resizable(False, False)

        tk.Label(
            editor,
            text=f"Volume: {sound['name']}",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=12)

        volume_var = tk.IntVar(value=sound.get("volume", 100))

        volume_label = tk.Label(
            editor,
            text=f"{volume_var.get()}%",
            bg=BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11)
        )
        volume_label.pack()

        def update_label(value):
            volume_label.config(text=f"{int(float(value))}%")

        slider = tk.Scale(
            editor,
            from_=0,
            to=100,
            orient="horizontal",
            variable=volume_var,
            command=update_label,
            bg=BG,
            fg=TEXT,
            troughcolor=CARD,
            highlightthickness=0,
            length=250
        )
        slider.pack(pady=10)

        def save_volume():
            set_sound_volume(sound["file"], volume_var.get())
            editor.destroy()
            self.refresh_app()
            self.status_label.config(text=f"Volume saved: {sound['name']}", fg=GREEN)

        tk.Button(
            editor,
            text="Save Volume",
            font=("Segoe UI", 11, "bold"),
            bg=GREEN,
            fg="#11111b",
            relief="flat",
            command=save_volume
        ).pack(ipadx=20, ipady=6)

    def build_settings_page(self, parent):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(outer, text="Settings", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(outer, text="Configure audio routing, imports, and global controls.", bg=BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 20))

        form = tk.Frame(outer, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="x", anchor="n")
        content = tk.Frame(form, bg=CARD)
        content.pack(fill="x", padx=20, pady=18)

        tk.Label(content, text="Output Device", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.settings_output_var = tk.StringVar(value=self.settings.get("output_device", ""))
        self.settings_device_box = ttk.Combobox(content, textvariable=self.settings_output_var, values=[""] + self.audio.get_output_devices(), state="readonly")
        self.settings_device_box.pack(fill="x", pady=(6, 4))
        tk.Label(content, text="Blank = Windows default output", bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 16))

        tk.Label(content, text="Startup Volume", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.settings_startup_volume_var = tk.IntVar(value=self.settings.get("startup_volume", 80))
        self.settings_volume_text = tk.Label(content, text=f"{self.settings_startup_volume_var.get()}%", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 10))
        self.settings_volume_text.pack(anchor="w", pady=(4, 0))

        def update_settings_volume_label(value):
            self.settings_volume_text.config(text=f"{int(float(value))}%")

        self.settings_volume_slider = tk.Scale(content, from_=0, to=100, orient="horizontal", variable=self.settings_startup_volume_var, command=update_settings_volume_label, bg=CARD, fg=TEXT, troughcolor=BG, highlightthickness=0, showvalue=False)
        self.settings_volume_slider.pack(fill="x", pady=(0, 16))

        tk.Label(content, text="Default Import Category", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.settings_category_var = tk.StringVar(value=self.settings.get("default_category", "memes"))
        tk.Entry(content, textvariable=self.settings_category_var, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", ipady=7, pady=(6, 16))

        tk.Label(content, text="Stop Hotkey", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.settings_stop_hotkey_var = tk.StringVar(value=self.settings.get("stop_hotkey", "f9"))
        tk.Entry(content, textvariable=self.settings_stop_hotkey_var, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", ipady=7, pady=(6, 4))
        tk.Label(content, text="Examples: f9, f12, num 0, ctrl+shift+s", bg=CARD, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 16))

        self.settings_auto_refresh_var = tk.BooleanVar(value=self.settings.get("auto_refresh", True))
        tk.Checkbutton(content, text="Auto refresh after import", variable=self.settings_auto_refresh_var, bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD, activeforeground=TEXT).pack(anchor="w", pady=(0, 18))

        button_row = tk.Frame(content, bg=CARD)
        button_row.pack(fill="x")
        tk.Button(button_row, text="Save Settings", font=("Segoe UI", 10, "bold"), bg=GREEN, fg="#11111b", relief="flat", padx=18, pady=9, command=self.save_settings_page).pack(side="left")
        self.settings_status_label = tk.Label(button_row, text="", bg=CARD, fg=GREEN, font=("Segoe UI", 10))
        self.settings_status_label.pack(side="left", padx=12)

    def refresh_settings_values(self):
        if not hasattr(self, "settings_device_box"):
            return
        self.settings_device_box.config(values=[""] + self.audio.get_output_devices())
        self.settings_output_var.set(self.settings.get("output_device", ""))
        self.settings_startup_volume_var.set(self.settings.get("startup_volume", 80))
        self.settings_volume_text.config(text=f"{self.settings.get('startup_volume', 80)}%")
        self.settings_category_var.set(self.settings.get("default_category", "memes"))
        self.settings_stop_hotkey_var.set(self.settings.get("stop_hotkey", "f9"))
        self.settings_auto_refresh_var.set(self.settings.get("auto_refresh", True))

    def save_settings_page(self):
        self.settings["output_device"] = self.settings_output_var.get()
        self.settings["startup_volume"] = self.settings_startup_volume_var.get()
        self.settings["default_category"] = self.settings_category_var.get().strip() or "memes"
        self.settings["stop_hotkey"] = self.settings_stop_hotkey_var.get().strip().lower() or "f9"
        self.settings["auto_refresh"] = self.settings_auto_refresh_var.get()
        save_settings(self.settings)
        self.audio.set_volume(self.settings["startup_volume"])
        self.volume_slider.set(self.settings["startup_volume"])
        self.volume_text.config(text=f"{self.settings['startup_volume']}%")
        self.refresh_app()
        self.settings_status_label.config(text="Saved")
        self.status_label.config(text="Settings saved", fg=GREEN)

    def open_settings(self):
        self.active_filter = "settings"
        self.refresh_nav_highlight()
        self.sounds_page.pack_forget()
        self.settings_page.pack(fill="both", expand=True)
        self.refresh_settings_values()
