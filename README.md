# DaD Custom Song Tools

Standalone tools for importing custom songs into **Dead as Disco**.

## Tools

- **DaD_BPM_AutoDetect** - Drag-and-drop audio files to auto-detect BPM and create ready-to-use song folders
- **DaD_Custom_Song_Importer** - Paste a YouTube/playlist URL to download and import songs

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
python src/DaD_Custom_Song_Importer.py "https://youtube.com/watch?v=..."
```

### Build Executables

```bash
pip install pyinstaller
pyinstaller --onefile --name DaD_BPM_AutoDetect src/DaD_BPM_AutoDetect.py
pyinstaller --onefile --name DaD_Custom_Song_Importer src/DaD_Custom_Song_Importer.py
```

Executables will be in the `dist/` folder.

## Output

Songs are exported to:
`%LOCALAPPDATA%\Pagoda\Saved\ImportedSongs`

Each song gets its own folder with:
- `Audio.ogg` - Converted audio file
- `Original.*` - Original source file
- `Meta.json` - Song metadata (BPM, offsets, etc.)

## License

MIT
