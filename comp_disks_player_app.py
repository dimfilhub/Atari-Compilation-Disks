"""Tkinter user interface: disk browser, search, settings and emulator start."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from disk_library import DiskLibrary, TEAMS
from emulator_launcher import EmulatorLauncher
from hatari_defaults import DEFAULT_HATARI_CONFIG
from settings_store import (
    APP_NAME, APP_VERSION, DEFAULT_JOYSTICK_KEYS, FOLDER_NAMES, JOYSTICK_ACTIONS, SettingsStore, settings_file_path,
)


FOLDER_LABELS = (("floppies", "Floppies:"), ("hatari", "Hatari:"), ("tos", "TOS image:"))
KEY_NAMES = {
    "space": "Space", "control_l": "Left Ctrl", "control_r": "Right Ctrl",
    "shift_l": "Left Shift", "shift_r": "Right Shift", "alt_l": "Left Alt", "alt_r": "Right Alt",
    "return": "Return", "tab": "Tab", "backspace": "Backspace", "up": "Up", "down": "Down",
    "left": "Left", "right": "Right", "insert": "Insert", "delete": "Delete", "home": "Home",
    "end": "End", "prior": "PageUp", "next": "PageDown",
}
FONT = ("Helvetica", 10)
SEARCH_DELAY_MS = 200
BACKGROUND_COLOR = "#b6f5b6"
CREDIT_TEXT = (
    "Atari ST Compilation Disk Browser and Player (new enhanced version)\n"
    "@Dimfil 2026\n"
    "Thanks to members of all groups who made all this possible!"
)


def application_directory():
    """Return the folder holding the app (the executable's folder when frozen), used to find `data`."""
    if getattr(sys, "frozen", False):
        folder = Path(sys.executable).resolve().parent
        if sys.platform == "darwin" and folder.parent.name == "Contents":
            return folder.parents[2]  # the folder that contains the .app bundle
        return folder
    return Path(__file__).resolve().parent


class CompilationDisksPlayer(tk.Tk):
    """Main window: browse and search compilation disks and start them in Hatari."""
    def __init__(self):
        """Load settings, set up the library and launcher, and build the window."""
        super().__init__()
        self.app_directory = application_directory()
        self.default_data_directory = self.app_directory / "data"
        self.default_folders = {
            "floppies": self.default_data_directory / "floppies",
            "hatari": self.default_data_directory / "hatari",
            "tos": self.default_data_directory / "roms" / "tos.img",
        }
        self._create_default_folders()
        self.catalogue_path = Path(getattr(sys, "_MEIPASS", self.app_directory)) / "CompDisks.json"
        self.settings = SettingsStore(settings_file_path())
        self.controller_choice = tk.StringVar(self)
        self.search_text = tk.StringVar(self)
        self.search_after_id = None
        self.custom_folders = {name: "" for name in FOLDER_NAMES}
        self.joystick_keys = dict(DEFAULT_JOYSTICK_KEYS)
        self._load_settings()
        self._use_folders(self._configured_folders())

        self._configure_window()
        self._build_interface()
        self._build_menu()
        self._populate_tree()

    def _create_default_folders(self):
        """Create the default `data` folders (floppies, hatari, roms) and the default Hatari config if missing."""
        for directory in (
            self.default_folders["floppies"],
            self.default_folders["hatari"],
            self.default_folders["tos"].parent,
        ):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        config_path = self.default_folders["hatari"] / "atari_keys"
        if not config_path.exists():
            try:
                config_path.write_text(DEFAULT_HATARI_CONFIG, encoding="utf-8", newline="\n")
            except OSError:
                pass

    def _configure_window(self):
        """Set the title, icon, position and close handler."""
        if sys.platform == "darwin":
            self.tk.call("tk", "appname", APP_NAME)
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.resizable(False, False)
        if sys.platform == "win32":
            icon_path = Path(getattr(sys, "_MEIPASS", self.app_directory)) / "atari.ico"
            if icon_path.is_file():
                self.iconbitmap(str(icon_path))
        self.geometry("+50+50")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_interface(self):
        """Apply styling and lay out the disk list, controls, search, results and credits."""
        # The native macOS theme follows system dark mode; clam has fixed light colours.
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TEntry", fieldbackground="white", foreground="blue")
        style.configure("TFrame", background=BACKGROUND_COLOR)
        style.configure("TLabelframe", background=BACKGROUND_COLOR)
        style.configure("TLabelframe.Label", background=BACKGROUND_COLOR, foreground="black")
        style.configure("TRadiobutton", background=BACKGROUND_COLOR, foreground="black")
        style.configure("TLabel", background=BACKGROUND_COLOR, foreground="black")
        style.configure("TButton", background="#e0e0e0", foreground="black")
        self.configure(background=BACKGROUND_COLOR)
        top = tk.Frame(self, padx=5, pady=5, bg=BACKGROUND_COLOR)
        top.pack(fill="x")
        disk_frame = tk.Frame(top, padx=5, pady=5, relief="groove", bd=5)
        disk_frame.pack(side="left", fill="both", expand=True)
        control_frame = tk.Frame(top, padx=5, pady=5, bg=BACKGROUND_COLOR, relief="groove", bd=5)
        control_frame.pack(side="left", fill="both", expand=True)

        self._build_disk_tree(disk_frame)
        self._build_controls(control_frame)
        self._build_search()
        self._build_results()
        self._build_credits()

    def _build_menu(self):
        """Create the Game, Options and Help menus and the Ctrl+F / Ctrl+S shortcuts."""
        menu_bar = tk.Menu(self, name="menubar")
        if sys.platform == "darwin":
            application_menu = tk.Menu(menu_bar, name="apple", tearoff=False)
            menu_bar.add_cascade(label=APP_NAME, menu=application_menu)

        game_menu = tk.Menu(menu_bar, tearoff=False)
        game_menu.add_command(label="Search for Game", command=self._clear_and_focus_search, accelerator="Ctrl+F")
        game_menu.add_command(
            label="Start Selected Disk", command=self._play_selected_disk, accelerator="Ctrl+S",
        )
        game_menu.add_separator()
        game_menu.add_command(label="Quit", command=self._close)
        menu_bar.add_cascade(label="Game", menu=game_menu)

        options_menu = tk.Menu(menu_bar, tearoff=False)
        controller_menu = tk.Menu(options_menu, tearoff=False)
        for label, value in (("Keyboard", "keyboard"), ("Joystick", "joystick")):
            controller_menu.add_radiobutton(
                label=label, variable=self.controller_choice, value=value,
            )
        options_menu.add_cascade(label="Controller", menu=controller_menu)

        options_menu.add_separator()
        options_menu.add_command(label="Settings...", command=self._open_settings)
        menu_bar.add_cascade(label="Options", menu=options_menu)

        help_menu = tk.Menu(menu_bar, name="help", tearoff=False)
        help_menu.add_command(label="About...", command=self._open_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menu_bar)
        self.bind_all("<Control-f>", lambda _event: self._clear_and_focus_search())
        self.bind_all("<Control-s>", lambda _event: self._play_selected_disk())

    def _open_about(self):
        """Show the modal About dialog."""
        window = tk.Toplevel(self)
        window.title(f"About {APP_NAME}")
        window.transient(self)
        window.resizable(False, False)
        window.grab_set()

        background = BACKGROUND_COLOR
        window.configure(background=background)
        tk.Label(
            window, text=APP_NAME, background=background, foreground="black",
            font=(FONT[0], FONT[1] + 2, "bold"),
        ).pack(padx=20, pady=(15, 5))
        tk.Label(
            window, text=f"Version {APP_VERSION}", background=background, foreground="black", font=FONT,
        ).pack(padx=20)
        tk.Label(
            window, text=CREDIT_TEXT, background=background, foreground="black", font=FONT, justify="center",
        ).pack(padx=20, pady=5)
        ttk.Button(window, text="OK", command=window.destroy).pack(pady=(5, 15))
        window.bind("<Return>", lambda _event: window.destroy())
        window.bind("<Escape>", lambda _event: window.destroy())

    def _open_settings(self):
        """Open the modal Settings dialog (folders and keyboard-joystick keys) and save on confirmation."""
        window = tk.Toplevel(self)
        window.title("Settings")
        window.configure(background=BACKGROUND_COLOR)
        window.transient(self)
        window.resizable(False, False)
        window.grab_set()

        controller_frame = ttk.LabelFrame(window, text="Controller", padding=10)
        controller_frame.pack(fill="x", padx=10, pady=10)
        controller_var = tk.StringVar(window, value=self.controller_choice.get())
        for label, value in (("Keyboard", "keyboard"), ("Joystick", "joystick")):
            ttk.Radiobutton(
                controller_frame, text=label, variable=controller_var, value=value,
            ).pack(side="left", padx=(0, 15))

        folder_frame = ttk.LabelFrame(window, text="Folders", padding=10)
        folder_frame.pack(fill="x", padx=10, pady=(0, 10))
        configured = self._configured_folders()
        folder_vars = {}
        for row, (name, label) in enumerate(FOLDER_LABELS):
            folder_vars[name] = tk.StringVar(window, value=str(configured[name]))
            ttk.Label(folder_frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(folder_frame, textvariable=folder_vars[name], width=50).grid(
                row=row, column=1, sticky="ew", padx=5, pady=2,
            )
            ttk.Button(
                folder_frame, text="Browse...",
                command=lambda n=name: browse(n),
            ).grid(row=row, column=2, pady=2)
            ttk.Button(
                folder_frame, text="Default",
                command=lambda n=name: folder_vars[n].set(str(self.default_folders[n])),
            ).grid(row=row, column=3, padx=(5, 0), pady=2)
        folder_frame.columnconfigure(1, weight=1)

        def browse(name):
            """Pick a folder (or the TOS file for "tos") and store it in the matching entry."""
            current = Path(folder_vars[name].get())
            if name == "tos":
                chosen = filedialog.askopenfilename(
                    parent=window, title="Select TOS image", initialdir=current.parent,
                    filetypes=(("TOS images", "*.img *.rom *.bin"), ("All files", "*.*")),
                )
            else:
                chosen = filedialog.askdirectory(
                    parent=window, title=f"Select {name} folder",
                    initialdir=current, mustexist=False,
                )
            if chosen:
                folder_vars[name].set(str(Path(chosen)))

        key_frame = ttk.LabelFrame(window, text="Keyboard joystick keys (Hatari)", padding=10)
        key_frame.pack(fill="x", padx=10, pady=(0, 10), before=folder_frame)
        key_vars = {}
        capturing = {}

        def stop_capture():
            """Cancel an in-progress key capture and restore its button label."""
            if capturing:
                window.unbind("<KeyPress>", capturing.pop("binding"))
                capturing.pop("button").configure(text="Set...")

        def capture(action, button):
            """Wait for the next key press and assign it to the joystick `action`."""
            stop_capture()
            button.configure(text="Press a key")
            window.focus_set()

            def on_key(event):
                """Store the pressed key if it can be mapped to a Hatari key name."""
                name = self._sdl_key_name(event)
                if name:
                    key_vars[action].set(name)
                stop_capture()
                return "break"

            capturing["button"] = button
            capturing["binding"] = window.bind("<KeyPress>", on_key)

        for row, (action, label) in enumerate(JOYSTICK_ACTIONS):
            key_vars[action] = tk.StringVar(window, value=self.joystick_keys[action])
            ttk.Label(key_frame, text=label + ":").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(key_frame, textvariable=key_vars[action], width=14, state="readonly").grid(
                row=row, column=1, padx=5, pady=2,
            )
            button = ttk.Button(key_frame, text="Set...")
            button.configure(command=lambda a=action, b=button: capture(a, b))
            button.grid(row=row, column=2, pady=2)
        ttk.Button(
            key_frame, text="Defaults",
            command=lambda: [var.set(DEFAULT_JOYSTICK_KEYS[a]) for a, var in key_vars.items()],
        ).grid(row=len(JOYSTICK_ACTIONS), column=0, columnspan=3, sticky="e", pady=(5, 0))

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side="right")

        def save_settings():
            """Validate folders, optionally create them, apply and persist the settings, then close the dialog."""
            new_folders = {
                name: Path(var.get().strip() or self.default_folders[name]).expanduser()
                for name, var in folder_vars.items()
            }
            missing = [f"{name}: {path}" for name, path in new_folders.items() if name != "tos" and not path.is_dir()]
            if missing and messagebox.askyesno(
                "Create folders?",
                "These folders do not exist:\n\n" + "\n".join(missing) + "\n\nCreate them?",
                parent=window,
            ):
                try:
                    for name, path in new_folders.items():
                        if name != "tos":
                            path.mkdir(parents=True, exist_ok=True)
                except OSError as error:
                    messagebox.showerror("Could not create folder", str(error), parent=window)
                    return
            previous = dict(self.custom_folders)
            self.custom_folders = {
                name: "" if path == self.default_folders[name] else str(path)
                for name, path in new_folders.items()
            }
            previous_keys = dict(self.joystick_keys)
            previous_controller = self.controller_choice.get()
            self.controller_choice.set(controller_var.get())
            self.joystick_keys = {action: var.get() for action, var in key_vars.items()}
            try:
                self._use_folders(new_folders)
                self._reload_disks()
                self.settings.save_keys(self.joystick_keys)
                self.settings.save(
                    self.controller_choice.get(), self.custom_folders,
                )
            except OSError as error:
                self.custom_folders = previous
                self.joystick_keys = previous_keys
                self.controller_choice.set(previous_controller)
                messagebox.showerror("Could not save settings", str(error), parent=window)
                return
            window.destroy()

        ttk.Button(buttons, text="Save", command=save_settings).pack(side="right", padx=(0, 5))
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def _build_disk_tree(self, parent):
        """Build the team/disk tree; double-click or Enter starts the selected disk."""
        style = ttk.Style(self)
        style.configure("my.Treeview", rowheight=25, background="white", fieldbackground="white")
        style.map("my.Treeview", background=[("selected", "#0078d7")], foreground=[("selected", "white")])
        style.configure("my.Treeview.Heading", foreground="blue", font=FONT)
        self.disk_tree = ttk.Treeview(parent, height=15, style="my.Treeview")
        self.disk_tree["columns"] = ("Disk", "Games")
        self.disk_tree.column("#0", width=150, minwidth=150, stretch=True)
        self.disk_tree.column("Disk", width=250, minwidth=250, stretch=True)
        self.disk_tree.column("Games", width=800, minwidth=800, stretch=True)
        self.disk_tree.heading("#0", text="Team")
        self.disk_tree.heading("Disk", text="Disk")
        self.disk_tree.heading("Games", text="Games")
        self.disk_tree.tag_configure("team", background="white", font=FONT)
        self.disk_tree.tag_configure("game", background="white", font=FONT)

        vertical = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.disk_tree.yview)
        horizontal = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.disk_tree.xview)
        self.disk_tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.disk_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.disk_tree.bind("<Double-1>", self._play_selected_disk)
        self.disk_tree.bind("<Return>", self._play_selected_disk)

    def _build_controls(self, parent):
        """Build the Start Disk, Search for Disk, Settings and Quit buttons."""
        style = ttk.Style(self)
        style.configure("my.TButton", foreground="blue", font=FONT)
        style.configure("quit.TButton", foreground="red", font=FONT)

        ttk.Button(
            parent, text="Start Disk", width=20, style="my.TButton",
            command=self._play_selected_disk,
        ).pack(side="top", pady=10)
        ttk.Button(
            parent, text="Search for Disk", width=20, style="my.TButton",
            command=self._clear_and_focus_search, takefocus=False,
        ).pack(side="top", pady=10)
        ttk.Button(
            parent, text="Settings", width=20, style="my.TButton",
            command=self._open_settings, takefocus=False,
        ).pack(side="top", pady=10)
        ttk.Button(
            parent, text="Quit", width=20, style="quit.TButton",
            command=self._close,
        ).pack(side="bottom", pady=10)

    def _build_search(self):
        """Build the search bar, which searches as you type."""
        frame = tk.Frame(self, padx=5, pady=5, bg=BACKGROUND_COLOR)
        frame.pack(fill="x")
        tk.Label(
            frame, text="Search in library for: ", background=BACKGROUND_COLOR, font=FONT,
        ).pack(side="left")
        self.search_entry = ttk.Entry(
            frame, textvariable=self.search_text, justify="center",
            foreground="blue", font=FONT,
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", self._search_games)
        self.search_text.trace_add("write", self._schedule_search)

    def _build_results(self):
        """Build the (initially hidden) search results tree."""
        self.results_frame = tk.Frame(self, padx=5, pady=5, relief="groove", bd=5)
        self.results_tree = ttk.Treeview(
            self.results_frame, height=10, style="my.Treeview", columns=("Disk", "Games"),
        )
        self.results_tree.column("#0", width=260, minwidth=200, stretch=False)
        self.results_tree.column("Disk", width=250, minwidth=250, stretch=False)
        self.results_tree.column("Games", width=800, minwidth=800, stretch=True)
        self.results_tree.heading("#0", text="Result")
        self.results_tree.heading("Disk", text="Disk")
        self.results_tree.heading("Games", text="Games")
        self.results_tree.tag_configure("header", background="white", font=FONT)
        self.results_tree.tag_configure("catalogue", background="white", font=FONT)
        self.results_tree.tag_configure(
            "collection", background="white", foreground="blue", font=FONT,
        )

        vertical = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        horizontal = ttk.Scrollbar(self.results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.results_frame.rowconfigure(0, weight=1)
        self.results_frame.columnconfigure(0, weight=1)
        self.results_tree.bind("<<TreeviewSelect>>", self._select_result)
        self.results_tree.bind("<Double-1>", self._play_result)
        self.results_tree.bind("<Return>", self._play_result)
        self.results_tree.bind("<Motion>", self._result_cursor)

    def _build_credits(self):
        """Show the credits text at the bottom of the window."""
        tk.Label(
            self, text=CREDIT_TEXT, background=BACKGROUND_COLOR, font=FONT,
        ).pack(fill="x", expand=True)

    def _load_settings(self):
        """Load the saved controller, folders and joystick keys into the window state."""
        controller, folders = self.settings.load()
        self.controller_choice.set(controller)
        self.custom_folders = folders
        self.joystick_keys = self.settings.load_keys()

    @staticmethod
    def _sdl_key_name(event):
        """Translate a Tk key event to a Hatari/SDL key name, or None if unsupported."""
        keysym = event.keysym
        if keysym.casefold() in KEY_NAMES:
            return KEY_NAMES[keysym.casefold()]
        if keysym.startswith("KP_") and keysym[3:].isdigit():
            return f"Keypad {keysym[3:]}"
        if len(keysym) == 1 and keysym.isalnum():
            return keysym.upper()
        if len(keysym) > 1 and keysym[0] == "F" and keysym[1:].isdigit():
            return keysym
        return None

    def _configured_folders(self):
        """Return the folder for each setting, falling back to the defaults under `data`."""
        return {
            name: Path(self.custom_folders[name]).expanduser() if self.custom_folders[name]
            else self.default_folders[name]
            for name in FOLDER_NAMES
        }

    def _use_folders(self, folders):
        """Make `folders` current by recreating the disk library and emulator launcher."""
        self.folders = dict(folders)
        self.library = DiskLibrary(folders["floppies"], self.catalogue_path)
        self.emulator_launcher = EmulatorLauncher(
            folders["hatari"], folders["tos"],
        )
        self.emulator_launcher.joystick_keys = dict(self.joystick_keys)

    def _reload_disks(self):
        """Clear both trees and rebuild the disk list from the current folders."""
        self.disk_tree.delete(*self.disk_tree.get_children())
        self.results_tree.delete(*self.results_tree.get_children())
        self.results_frame.pack_forget()
        self._populate_tree()

    def _populate_tree(self):
        """Fill the tree with teams and the disks found in the floppies folder."""
        team_nodes = {}
        self.disk_tree_items = {}
        available = self.library.available_disks()
        for folder, display_name, prefix in TEAMS:
            if any(disk_name.startswith(prefix) for disk_name in available):
                team_nodes[prefix] = self.disk_tree.insert(
                    "", "end", text=display_name, values=("", ""),
                    open=False, tags=("team",),
                )
        for disk_name, games in available.items():
            parent = team_nodes[disk_name[:3]]
            self.disk_tree_items[disk_name] = self.disk_tree.insert(
                parent, "end", values=(disk_name, games), tags=("game",),
            )

    def _play_selected_disk(self, _event=None):
        """Start the disk selected in the tree, or show an error if none is selected."""
        selected_items = self.disk_tree.selection()
        disk_name = None
        if selected_items:
            values = self.disk_tree.item(selected_items[0]).get("values", [])
            if values and values[0]:
                disk_name = values[0]
        if not disk_name:
            messagebox.showerror("No game selected", "Select a disk before starting the emulator.")
            return

        self._play_disk(disk_name)

    def _play_disk(self, disk_name):
        """Check the disk and TOS image exist, then run the emulator, reporting any error."""
        floppy_path = self.library.disk_path(disk_name)
        if floppy_path is None:
            messagebox.showerror("No game selected", "The selected item is not a disk.")
            return
        if not floppy_path.is_file():
            messagebox.showerror("Disk not found", f"The disk image could not be found:\n{floppy_path}")
            return
        if not self.folders["tos"].is_file():
            messagebox.showerror(
                "TOS image not found",
                f"Select a TOS image in Options > Settings.\n{self.folders['tos']}",
            )
            return
        try:
            self.emulator_launcher.launch(
                self.controller_choice.get(), floppy_path,
            )
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Error loading game", str(error))

    def _schedule_search(self, *_args):
        """Debounce typing: (re)schedule a search after a short delay."""
        if self.search_after_id is not None:
            self.after_cancel(self.search_after_id)
        self.search_after_id = self.after(SEARCH_DELAY_MS, self._search_as_you_type)

    def _search_as_you_type(self):
        """Run the scheduled search, or hide the results when the query is empty."""
        self.search_after_id = None
        if self.search_text.get().strip():
            self._search_games()
        else:
            self.results_frame.pack_forget()

    def _search_games(self, _event=None):
        """Search the catalogue and show matches, split into owned disks and all catalogue disks."""
        if self.search_after_id is not None:
            self.after_cancel(self.search_after_id)
            self.search_after_id = None
        query = self.search_text.get().strip()
        self.results_frame.pack(fill="x", expand=True)
        self.results_tree.delete(*self.results_tree.get_children())
        self.disk_tree.selection_remove(self.disk_tree.selection())
        if not query:
            self.results_tree.insert(
                "", "end", text="Enter a game title to search the disk catalogue.", tags=("header",),
            )
            return

        collection, catalogue = self.library.search(query)
        if not collection:
            self.results_tree.insert(
                "", "end", text=f'"{query}" was not found in your collection!', tags=("header",),
            )
        else:
            node = self.results_tree.insert(
                "", "end", text="Found in your collection", open=True, tags=("header",),
            )
            self._insert_search_results(node, collection, "collection")

        node = self.results_tree.insert(
            "", "end", text="Search results in following Compilation Disks",
            open=True, tags=("header",),
        )
        self._insert_search_results(node, catalogue, "catalogue")
        if not catalogue:
            self.results_tree.insert(node, "end", text="No matching disks found.", tags=("catalogue",))

    def _insert_search_results(self, parent, results, tag):
        """Add result rows under `parent`; only owned disks in the collection are clickable."""
        for disk_name, games in results:
            clickable = tag == "collection" and disk_name in self.disk_tree_items
            self.results_tree.insert(
                parent, "end", values=(disk_name, games),
                tags=(tag,) if clickable or tag != "collection" else ("catalogue",),
            )

    def _result_disk(self, item):
        """Disk name of a clickable (found in collection) result row, else None."""
        if not item or "collection" not in self.results_tree.item(item, "tags"):
            return None
        values = self.results_tree.item(item, "values")
        return values[0] if values else None

    def _result_cursor(self, event):
        """Show a hand cursor over clickable result rows."""
        item = self.results_tree.identify_row(event.y)
        self.results_tree.configure(cursor="hand2" if self._result_disk(item) else "")

    def _select_result(self, _event=None):
        """Select the matching disk in the main tree when a result row is clicked."""
        selected = self.results_tree.selection()
        disk_name = self._result_disk(selected[0]) if selected else None
        if disk_name:
            self._select_disk(disk_name)

    def _play_result(self, _event=None):
        """Start the disk of the activated result row."""
        selected = self.results_tree.selection()
        disk_name = self._result_disk(selected[0]) if selected else None
        if disk_name:
            self._play_search_result(disk_name)

    def _play_search_result(self, disk_name):
        """Select `disk_name` in the main tree and start it."""
        self._select_disk(disk_name)
        self._play_disk(disk_name)

    def _select_disk(self, disk_name):
        """Select, focus and scroll to the disk in the main tree."""
        if disk_name in self.disk_tree_items:
            item = self.disk_tree_items[disk_name]
            self.disk_tree.selection_set(item)
            self.disk_tree.focus(item)
            self.disk_tree.see(item)

    def _clear_and_focus_search(self):
        """Empty the search box and move keyboard focus to it."""
        self.search_text.set("")
        self._focus_search()

    def _focus_search(self):
        """Move keyboard focus to the search box."""
        self.search_entry.focus_set()

    def _close(self):
        """Delete temporary floppy images, save settings and close the window."""
        for image in (self.default_data_directory / "floppy.st", self.default_data_directory / "floppy.msa"):
            if image.exists():
                image.unlink()
        self.settings.save(
            self.controller_choice.get(), self.custom_folders,
        )
        self.destroy()


def main():
    """Enable DPI awareness on Windows and run the application."""
    if sys.platform == "win32":
        try:
            from ctypes import windll
            # noinspection PyUnresolvedReferences
            windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, ImportError, OSError):
            pass
    CompilationDisksPlayer().mainloop()
