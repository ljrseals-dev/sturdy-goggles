# PyInstaller spec for a self-contained executable that bundles Python and numpy.
# NOT built or tested in the environment this package was made in (no PyInstaller, no network). Build it on each
# target OS yourself:   pip install pyinstaller numpy   then   pyinstaller aoc.spec
# Result: dist/aoc (aoc.exe on Windows). Size depends on your numpy build; measure it, do not assume.
# a.k.a. one-file mode; remove the exclusions if you add features that need them.
block_cipher = None
a = Analysis(['aoc/__main__.py'], pathex=['.'], binaries=[], datas=[], hiddenimports=['aoc.cli'],
             excludes=['tkinter', 'scipy', 'matplotlib', 'pandas', 'PIL', 'IPython', 'pytest'], noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='aoc', debug=False, strip=False, upx=False,
          console=True)
