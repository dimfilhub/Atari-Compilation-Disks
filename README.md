# Atari-ST-Comp-Disks-Player

Compilation Disks are a great part of the Atari ST home computer scene. So many and so great releases that cover the most part of Atari ST game (and not only) library are a must-have for any user.
Many sites covered the need to search among the teams and groups who created such compilation disks. Stonish and Atari Legend just to name a few...

But I find interesting to be able to search and finally play a disk image directly on my pc, without the need to search online where to find a game.
So, just for fun, I created a small app in Python that helps to:

- Present the available library of my CD floppy images grouped by teams (at the moment Automation, D-Bug, Flame of Finland, Medway Boys, Pompey Pirates and Superior teams are supported)
- Search in the library for a game (searches in user's collection but also in the full list of all supported teams)
- Play the game with Hatari emulator (Steem SSE option added in v2.0 )

The player runs on Windows and macOS. On macOS, install Hatari separately (for example, with `brew install hatari`) and ensure the `hatari` command is available in `PATH`; Steem SSE is Windows-only. The application looks for its `data` folder next to the player, independent of the working directory.

An Atari ST 1040 system is emulated for best compatibility purposes. TOS 1.04 is included downloaded from http://www.avtandil.narod.ru/tose.html

Place your collection in .\data\floppies folder regarding the team. Please consult CompDisksNaming.txt file for correct naming of the floppy images. Most of the time, collections already available online have correct names. The player recognizes the filenames listed in CompDisks.json, including `.ST` and `.MSA` disk images; if an image is instead stored as a same-named `.zip`, it will also be found. ZIP archives should contain one `.ST` or `.MSA` image (a matching image basename is preferred if there are several).
Folder names must be "automation", "dbug", "fof", "medway", "pompey" and "superior".
if you have no disks yet, a good place to start is https://archive.org/details/atari-st-collection-1997-cdr-alien-pompey-pirates

When start, the app will populate the treeview according to the available floppy images, grouped by teams.

Double click on a disk or press Start Disk button to start it!

Note: Some releases use two (some times more) disks for a game. Unfortunately most of them do not support a second floppy drive, so it is impossible to automate the process in emulator.
In this cases (you will know as these disks are noted as (A), (B) and so on) if you want to play a multiple disk game you have to swap the floppy image by your own. Use emulator's gui for that (F12).

Both emulators share the following keyboard shortcuts:
- [F12] to enter emulator's gui
- [Q] to Quit emulator
- [ESC] to to toggle fullscreen/windowed mode
- [AltGr+C] for cold reset
- [AltGr+R] for warm reset

Keyboard controls are cursor keys for movement and RCtrl for Fire.

Please note that in Steem you may need to set your real joystick/joypad in settings.
Just press F12 in-game (started with keyboard option enabled) and set your joystick/joypad in port 1. This has to take place for bot options (scanlines and no-scanlines) as two different ini files are used.

I hope you find it usefull. If needed, please open an issue on GitHub.

Have fun...!!!
