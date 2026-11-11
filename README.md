# Snake

A classic Snake game built with Python and Pygame. Run it from source or build a standalone executable for 64-bit Windows.

| Key | Action |
| --- | --- |
| Enter | Start or play again |
| Arrow keys or WASD | Steer |
| P | Pause or resume |
| M | Toggle sound |

The snake moves eight cells per second and wraps around all four edges. Each piece of food adds one point and one segment. Hitting your body ends the run. Filling the board wins. Switching away from the window pauses play.

The five best completed runs and your sound setting are saved in `%LOCALAPPDATA%\Snake\history.json`. Earlier runs rank first on ties.

## Run from source

Open PowerShell in this folder and run:

```powershell
python -m pip install -r requirements.txt
python snake.py
```

## Rebuild the executable

```powershell
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --onefile --windowed --name Snake snake.py
```

The rebuilt executable appears in `dist`.
