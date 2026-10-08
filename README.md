# Atari-ST-Comp-Disks-Player

Compilation Disks are a great part of the Atari ST home computer scene. So many and so great releases that cover the most part of Atari ST game (and not only) library are a must-have for any user.
Many sites covered the need to search among the teams and groups who created such compilation disks. Stonish and Atari Legend just to name a few...

But I find interesting to be able to search and finally play a disk image directly on my pc, without the need to search online where to find a game.
So, just for fun, I created a small app in Python that helps to:

- Present the available library of my CD floppy images grouped by teams (at the moment Automation, D-Bug, Flame of Finland, Medway Boys, Pompey Pirates and Superior teams are supported)
- Search in the library for a game (searches in user's collection but also in the full list of all supported teams)
- Play the game with Hatari emulator

The player runs on Windows and macOS: 
- On macOS, install Hatari separately (for example directly in /Applications folder or with "brew install hatari" if you have homebrew installed) and ensure the "hatari" command is available in PATH. 
- On Windows just place Hatari executable in data/hatari folder.

Install Python 3.11 or later and run the player with: 
- "python3 comp_disks_player.pyw" in Terminal for MacOS
- "python comp_disks_player.pyw" in Command Prompt for Windows. 

If you want to create MacOS or Windows executables you must:
- Install pyinstaller (pip install pyinstaller) and pillow (pip install pillow)
- run "build.py" script in Terminal for MacOS or in Command Prompt for Windows. It will create a dist folder with the executable inside.
- after successful build executable is placed in dist folder. Just move it to the main project directory.

The app will create a config file in the same folder where it is run, so you can change the default settings (like Hatari path, TOS version, etc.) if needed.

An Atari ST 1040 system is emulated for best compatibility purposes. TOS 1.04 is included downloaded from http://www.avtandil.narod.ru/tose.html

Place your collection in .\data\floppies folder regarding the team. Please consult CompDisksNaming.txt file for correct naming of the floppy images. Most of the time, collections already available online have correct names. The player recognizes the filenames listed in CompDisks.json, including .ST and .MSA disk images. If an image is instead stored as a same-named .zip, it will also be found. ZIP archives should contain one .ST or .MSA image (a matching image basename is preferred if there are several).
Folder names must be "automation", "dbug", "fof", "medway", "pompey" and "superior".
if you have no disks yet, a good place to start is https://archive.org/details/atari-st-collection-1997-cdr-alien-pompey-pirates

When start, the app will populate the treeview according to the available floppy images, grouped by teams.

Double click on a disk or press Start Disk button to start it!

Note: Some releases use two (some times more) disks for a game. Unfortunately most of them do not support a second floppy drive, so it is impossible to automate the process in emulator.
In this cases (you will know as these disks are noted as (A), (B) and so on) if you want to play a multiple disk game you have to swap the floppy image by your own. Use emulator's gui for that (F12).

Following keyboard shortcuts are used in the emulator:
- [F12] to enter emulator's gui
- [Q] to Quit emulator
- [ESC] to to toggle fullscreen/windowed mode
- [CMD+C] (Mac) or [AltGr+C] (Win) for cold reset
- [CMD+R] (Mac) or [AltGr+R] (Win) for warm reset

Keyboard controls are cursor keys for movement and Space for Fire (configurable in Options > Settings).

I hope you find it useful. If needed, please open an issue on GitHub.

Have fun...!!!
