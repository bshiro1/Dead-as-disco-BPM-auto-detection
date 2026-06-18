import sys
import os
import json
import subprocess
import random
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except ImportError:
    input("ERROR: imageio_ffmpeg not found. Run: pip install imageio-ffmpeg")
    sys.exit(1)

try:
    import librosa
    import numpy as np
except ImportError:
    input("ERROR: librosa not found. Run: pip install librosa")
    sys.exit(1)

FFMPEG = get_ffmpeg_exe()
EXPORT_DIR = Path(os.environ["LOCALAPPDATA"]) / "Pagoda" / "Saved" / "ImportedSongs"
INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize(name):
    name = INVALID_CHARS.sub("", name)
    name = name.strip().rstrip(".")
    return name if name else "Unknown_Song"


def get_duration(fp):
    r = subprocess.run(
        [FFMPEG, "-i", str(fp), "-f", "null", "-"],
        capture_output=True, text=True, timeout=120,
    )
    m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", r.stderr)
    if m:
        h, mi, s, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        return h * 3600 + mi * 60 + s + ms / 100.0
    return None


def detect_bpm(audio_path):
    try:
        r = subprocess.run(
            [FFMPEG, "-y", "-i", str(audio_path), "-vn", "-acodec", "pcm_s16le",
             "-ar", "22050", "-ac", "1", "-f", "wav", "-"],
            capture_output=True, timeout=120,
        )
        if r.returncode != 0:
            return 120

        a = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        if len(a) < 2048:
            return 120

        t, _ = librosa.beat.beat_track(y=a, sr=22050)
        return max(100, min(200, round(float(t))))
    except Exception:
        return 120


def process_file(input_path):
    input_path = Path(input_path)
    if not input_path.is_file():
        return f"NOT FOUND: {input_path}"

    stem = input_path.stem
    print(f'\n{"=" * 60}\nProcessing: {input_path.name}\n{"=" * 60}')
    sys.stdout.flush()

    ogg = Path(tempfile.gettempdir()) / f"dad_{random.randint(0, 999999):06d}.ogg"

    print("Converting to OGG...")
    r = subprocess.run(
        [FFMPEG, "-y", "-i", str(input_path), "-vn", "-ar", "44100", "-ac", "2",
         "-c:a", "libvorbis", "-q:a", "5", str(ogg)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        return "OGG conversion failed"

    size_mb = ogg.stat().st_size / 1024 / 1024
    print(f"  -> OGG ({size_mb:.1f} MB)")

    bpm = detect_bpm(ogg)
    print(f"  -> BPM: {bpm}")

    duration = get_duration(ogg) or 180.0
    print(f"  -> Duration: {duration:.1f}s")

    sdn = sanitize(stem)[:80]
    uid = random.randint(0, 2147483647)
    sd = random.randint(0, 2147483647)

    song_dir = EXPORT_DIR / sdn
    song_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(str(ogg), str(song_dir / "Audio.ogg"))
    ogg.unlink(missing_ok=True)

    dest_orig = song_dir / f"Original{input_path.suffix}"
    shutil.copy2(str(input_path), str(dest_orig))

    fh = hashlib.md5()
    with open(dest_orig, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            fh.update(chunk)

    meta = {
        "version": 1,
        "uniqueId": uid,
        "songName": stem,
        "performedBy": [],
        "writtenBy": [],
        "seed": sd,
        "tempo": bpm,
        "customTempoSections": [],
        "beatOffset": 0,
        "startSongOffset": 0,
        "endSongOffset": 0,
        "uEAssetName": sdn,
        "originalAudioFileHash": fh.hexdigest(),
        "originalAudioFilePath": str(dest_orig.resolve()),
    }

    with open(song_dir / "Meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent="\t")

    print(f"\nDONE -> {song_dir}\n       BPM={bpm}, Duration={duration:.1f}s")
    sys.stdout.flush()
    return None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(
            "Drag & drop audio files (M4A, MP3, AAC, WAV, FLAC, OGG) onto this exe.\n"
            "Output goes to: IMPORTED SONGS FOLDER"
        )
        input("\nPress Enter to exit...")
        sys.exit(0)

    errors = []
    for f in args:
        err = process_file(f)
        if err:
            errors.append(err)

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")

    print("\nDone. Launch Dead as Disco and check Free Play.")
    input("Press Enter to exit...")
