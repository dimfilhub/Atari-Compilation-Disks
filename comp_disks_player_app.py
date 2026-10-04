import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from disk_library import DiskLibrary, TEAMS
from emulator_launcher import EmulatorLauncher
from settings_store import APP_NAME, SettingsStore, settings_file_path


FONT = ("Atari ST 8x16 System Font", 10)


def application_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class CompilationDisksPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.app_directory = application_directory()
        self.data_directory = self.app_directory / "data"
        self.library = DiskLibrary(
            self.data_directory,
            Path(getattr(sys, "_MEIPASS", self.app_directory)) / "CompDisks.json",
        )
        self.settings = SettingsStore(settings_file_path())
        self.emulator_launcher = EmulatorLauncher(self.data_directory)
        self.controller_choice = tk.StringVar(self)
        self.emulator_choice = tk.StringVar(self)
        self.search_text = tk.StringVar(self)

        self._configure_window()
        self._build_interface()
        self._build_menu()
        self._load_settings()
        self._populate_tree()

    def _configure_window(self):
        if sys.platform == "darwin":
            self.tk.call("tk", "appname", APP_NAME)
        self.title(APP_NAME)
        self.resizable(False, False)
        if sys.platform == "win32":
            icon_path = self.app_directory / "atari.ico"
            if icon_path.is_file():
                self.iconbitmap(str(icon_path))
        self.geometry("+50+50")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_interface(self):
        # The native macOS theme follows system dark mode; clam has fixed light colours.
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TEntry", fieldbackground="white", foreground="blue")
        style.configure("TFrame", background="#ececec")
        style.configure("TLabelframe", background="#ececec")
        style.configure("TLabelframe.Label", background="#ececec", foreground="black")
        style.configure("TRadiobutton", background="#ececec", foreground="black")
        style.configure("TButton", background="#e0e0e0", foreground="black")
        self.configure(background="green yellow")
        top = tk.Frame(self, padx=5, pady=5, bg="green yellow")
        top.pack(fill="x")
        disk_frame = tk.Frame(top, padx=5, pady=5, relief="groove", bd=5)
        disk_frame.pack(side="left", fill="both", expand=True)
        control_frame = tk.Frame(top, padx=5, pady=5, bg="lime green", relief="groove", bd=5)
        control_frame.pack(side="left", fill="both", expand=True)

        self._build_disk_tree(disk_frame)
        self._build_controls(control_frame)
        self._build_search()
        self._build_results()
        self._build_credits()

    def _build_menu(self):
        menu_bar = tk.Menu(self, name="menubar")
        if sys.platform == "darwin":
            application_menu = tk.Menu(menu_bar, name="apple", tearoff=False)
            menu_bar.add_cascade(label=APP_NAME, menu=application_menu)

        game_menu = tk.Menu(menu_bar, tearoff=False)
        game_menu.add_command(label="Search for Game", command=self._focus_search, accelerator="Ctrl+F")
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

        emulator_menu = tk.Menu(options_menu, tearoff=False)
        for label, value in self._available_emulators():
            emulator_menu.add_radiobutton(
                label=label, variable=self.emulator_choice, value=value,
            )
        options_menu.add_cascade(label="Emulator", menu=emulator_menu)
        options_menu.add_separator()
        options_menu.add_command(label="Settings...", command=self._open_settings)
        menu_bar.add_cascade(label="Options", menu=options_menu)

        self.configure(menu=menu_bar)
        self.bind_all("<Control-f>", lambda _event: self._focus_search())
        self.bind_all("<Control-s>", lambda _event: self._play_selected_disk())

    def _open_settings(self):
        window = tk.Toplevel(self)
        window.title("Settings")
        window.transient(self)
        window.resizable(False, False)
        window.grab_set()

        default_emulator = tk.StringVar(window, value=self.emulator_choice.get())
        frame = ttk.LabelFrame(window, text="Default emulator", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        for label, value in self._available_emulators():
            ttk.Radiobutton(
                frame, text=label, variable=default_emulator, value=value,
            ).pack(anchor="w", pady=2)

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side="right")

        def save_settings():
            try:
                self.settings.save(self.controller_choice.get(), default_emulator.get())
            except OSError as error:
                messagebox.showerror("Could not save settings", str(error), parent=window)
                return
            self.emulator_choice.set(default_emulator.get())
            window.destroy()

        ttk.Button(buttons, text="Save", command=save_settings).pack(side="right", padx=(0, 5))
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    @staticmethod
    def _available_emulators():
        emulators = [("Hatari", "hatari")]
        if sys.platform == "win32":
            emulators.extend((
                ("Steem SSE (Scanlines)", "steemscan"),
                ("Steem SSE (No Scanlines)", "steemnoscan"),
            ))
        return emulators

    def _build_disk_tree(self, parent):
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
        style = ttk.Style(self)
        style.configure("my.TButton", foreground="blue", font=FONT)
        style.configure("quit.TButton", foreground="red", font=FONT)
        style.configure("my.TRadiobutton", background="lime green", font=FONT)

        controller_frame = tk.Frame(parent, padx=5, pady=5, bg="lime green", relief="groove", bd=5)
        emulator_frame = tk.Frame(parent, padx=5, pady=5, bg="lime green", relief="groove", bd=5)
        controller_frame.pack(fill="both", expand=True)
        emulator_frame.pack(fill="both", expand=True)
        tk.Label(
            controller_frame, text="Select Controller:", background="lime green",
            font=("Atari ST 8x16 System Font", 10, "bold underline"),
        ).pack(side="top", fill="x", pady=10)
        for label, value in (("Keyboard", "keyboard"), ("Joystick", "joystick")):
            ttk.Radiobutton(
                controller_frame, text=label, variable=self.controller_choice,
                value=value, style="my.TRadiobutton",
            ).pack(side="left", fill="x", expand=True)

        tk.Label(
            emulator_frame, text="Select Emulator:", background="lime green",
            font=("Atari ST 8x16 System Font", 10, "bold underline"),
        ).pack(side="top", fill="x", pady=10)
        emulators = [("Hatari", "hatari")]
        if sys.platform == "win32":
            emulators.extend((
                ("Steem SSE (Scanlines)", "steemscan"),
                ("Steem SSE (No Scanlines)", "steemnoscan"),
            ))
        for label, value in emulators:
            ttk.Radiobutton(
                emulator_frame, text=label, variable=self.emulator_choice,
                value=value, style="my.TRadiobutton",
            ).pack(side="top", fill="x")

        ttk.Button(
            parent, text="Start Disk", width=20, style="my.TButton",
            command=self._play_selected_disk,
        ).pack(side="top", pady=10)
        ttk.Button(
            parent, text="Quit", width=20, style="quit.TButton",
            command=self._close,
        ).pack(side="bottom", pady=10)

    def _build_search(self):
        frame = tk.Frame(self, padx=5, pady=5, bg="green yellow")
        frame.pack(fill="x")
        tk.Label(
            frame, text="Search in library for: ", background="green yellow", font=FONT,
        ).pack(side="left")
        self.search_entry = ttk.Entry(
            frame, textvariable=self.search_text, justify="center",
            foreground="blue", font=FONT,
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            frame, text="Search", width=20, style="my.TButton",
            command=self._search_games,
        ).pack(side="right", padx=15)
        self.search_entry.bind("<Return>", self._search_games)

    def _build_results(self):
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
        credit_lines = (
            "Atari ST Compilation Disk Browser and Player\n"
            "@Dimfil 2021\n"
            "Thanks to members of all groups who made all this possible!"
        )
        tk.Label(
            self, text=credit_lines, background="green yellow", font=FONT,
        ).pack(fill="x", expand=True)

    def _load_settings(self):
        controller, emulator = self.settings.load()
        self.controller_choice.set(controller)
        self.emulator_choice.set(emulator)

    def _populate_tree(self):
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
        floppy_path = self.library.disk_path(disk_name)
        if floppy_path is None:
            messagebox.showerror("No game selected", "The selected item is not a disk.")
            return
        if not floppy_path.is_file():
            messagebox.showerror("Disk not found", f"The disk image could not be found:\n{floppy_path}")
            return
        try:
            self.emulator_launcher.launch(
                self.emulator_choice.get(), self.controller_choice.get(), floppy_path,
            )
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Error loading game", str(error))

    def _search_games(self, _event=None):
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
        item = self.results_tree.identify_row(event.y)
        self.results_tree.configure(cursor="hand2" if self._result_disk(item) else "")

    def _select_result(self, _event=None):
        selected = self.results_tree.selection()
        disk_name = self._result_disk(selected[0]) if selected else None
        if disk_name:
            self._select_disk(disk_name)

    def _play_result(self, _event=None):
        selected = self.results_tree.selection()
        disk_name = self._result_disk(selected[0]) if selected else None
        if disk_name:
            self._play_search_result(disk_name)

    def _play_search_result(self, disk_name):
        self._select_disk(disk_name)
        self._play_disk(disk_name)

    def _select_disk(self, disk_name):
        if disk_name in self.disk_tree_items:
            item = self.disk_tree_items[disk_name]
            self.disk_tree.selection_set(item)
            self.disk_tree.focus(item)
            self.disk_tree.see(item)

    def _focus_search(self):
        self.search_entry.focus_set()

    def _close(self):
        for image in (self.data_directory / "floppy.st", self.data_directory / "floppy.msa"):
            if image.exists():
                image.unlink()
        self.settings.save(self.controller_choice.get(), self.emulator_choice.get())
        self.destroy()


def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            # noinspection PyUnresolvedReferences
            windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, ImportError, OSError):
            pass
    CompilationDisksPlayer().mainloop()
