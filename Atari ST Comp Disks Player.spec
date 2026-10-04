# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

project_dir = Path(SPECPATH)
block_cipher = None


a = Analysis([str(project_dir / 'comp_disks_player.pyw')],
             pathex=[str(project_dir)],
             binaries=[],
             datas=[(str(project_dir / 'atari.ico'), '.'), (str(project_dir / 'CompDisks.json'), '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Atari ST Comp Disks Player',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon=str(project_dir / 'atari.ico') if sys.platform == 'win32' else None)
