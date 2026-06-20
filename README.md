# DaD Custom Song Tools

Standalone tool for importing custom songs into **Dead as Disco**.

## Tool

- **DaD_BPM_AutoDetect** - Drag-and-drop audio files or folders to auto-detect BPM and create ready-to-use song folders

## How to Build

### Prerequisites

- Python 3.8 or newer
- pip

### Setup

```bash
pip install -r requirements.txt
```

### Run from Source

```bash
python src/DaD_BPM_AutoDetect.py "path\to\song.mp3"
```

Drag & drop files or folders onto `Drop Songs Here.bat`.

### Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --name DaD_BPM_AutoDetect src/DaD_BPM_AutoDetect.py
```

Executable will be in the `dist/` folder.

## Output

Songs are exported to:
`%LOCALAPPDATA%\Pagoda\Saved\ImportedSongs`

Each song gets its own folder with:
- `Audio.ogg` - Converted audio file
- `Original.*` - Original source file
- `Meta.json` - Song metadata (BPM, offsets, etc.)

## License

MIT
