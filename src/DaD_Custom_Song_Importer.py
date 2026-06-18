import sys
import os
import json
import subprocess
import random
import hashlib
import re
import shutil
import tempfile
import time
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

try:
    import yt_dlp
except ImportError:
    input("ERROR: yt-dlp not found. Run: pip install yt-dlp")
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


def process_download(m4a_path, title):
    print(f"\n  Processing: {title}")
    sys.stdout.flush()

    ogg = Path(tempfile.gettempdir()) / f"dad_{random.randint(0, 999999):06d}.ogg"

    r = subprocess.run(
        [FFMPEG, "-y", "-i", str(m4a_path), "-vn", "-ar", "44100", "-ac", "2",
         "-c:a", "libvorbis", "-q:a", "5", str(ogg)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print("    OGG conversion failed")
        return None

    size_mb = ogg.stat().st_size / 1024 / 1024
    print(f"    OGG: {size_mb:.1f} MB")

    bpm = detect_bpm(ogg)
    print(f"    BPM: {bpm}")

    duration = get_duration(ogg) or 180.0
    print(f"    Duration: {duration:.1f}s")

    sdn = sanitize(title)[:80]
    uid = random.randint(0, 2147483647)
    sd = random.randint(0, 2147483647)

    song_dir = EXPORT_DIR / sdn
    song_dir.mkdir(parents=True, exist_ok=True)

    dest_ogg = song_dir / "Audio.ogg"
    shutil.copy2(str(ogg), str(dest_ogg))
    ogg.unlink(missing_ok=True)

    dest_m4a = song_dir / "Original.m4a"
    shutil.copy2(str(m4a_path), str(dest_m4a))

    fh = hashlib.md5()
    with open(dest_m4a, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            fh.update(chunk)

    meta = {
        "version": 1,
        "uniqueId": uid,
        "songName": title,
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
        "originalAudioFilePath": str(dest_m4a.resolve()),
    }

    with open(song_dir / "Meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent="\t")

    print(f"    Saved: {sdn}")
    sys.stdout.flush()
    return None


def process_url(url):
    tmp = Path(tempfile.mkdtemp(prefix="dad_url_"))

    print(f'\n{"=" * 60}\nFetching: {url}\n{"=" * 60}')
    sys.stdout.flush()

    entries = []

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ValueError("No info")
            entries = info["entries"] if "entries" in info else [info]
    except Exception:
        print("ERROR: Could not fetch info")
        shutil.rmtree(tmp, ignore_errors=True)
        return

    print(f"Found {len(entries)} track(s)")

    for idx, entry in enumerate(entries, 1):
        title = entry.get("title", f"Track_{idx}")
        dur = entry.get("duration", 0)

        if dur and dur < 30:
            print(f'\n  [{idx}/{len(entries)}] Skipping \'{title}\'')
            continue

        vurl = (
            entry.get("webpage_url")
            or entry.get("url")
            or entry.get("original_url")
            or url
        )

        print(f'\n  [{idx}/{len(entries)}] Downloading: {title}')
        sys.stdout.flush()

        out_tmpl = str(tmp / f"{sanitize(title)}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extractor_retries": 10,
            "throttled_rate": "100K",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([vurl])
        except Exception:
            print("    Retry...")
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
            ]
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([vurl])
            except Exception as e2:
                print(f"    Download failed: {e2}")
                continue

        time.sleep(0.5)

        downloaded = sorted(
            [p for p in tmp.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not downloaded:
            print("    ERROR: No file found")
            sys.stdout.flush()
            continue

        src = downloaded[0]
        print(f"    Downloaded: {src.name}")

        if src.suffix not in (".m4a", ".aac"):
            m4a = tmp / f"{sanitize(title)}.m4a"
            rc = subprocess.run(
                [FFMPEG, "-y", "-i", str(src), "-vn", "-acodec", "aac",
                 "-ar", "44100", "-ac", "2", "-b:a", "192k", str(m4a)],
                capture_output=True, text=True, timeout=300,
            )
            if rc.returncode != 0:
                print("    Conversion failed")
                continue
            src.unlink(missing_ok=True)
            m4a_path = m4a
        else:
            m4a_path = src

        process_download(m4a_path, title)
        m4a_path.unlink(missing_ok=True)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nFinished {len(entries)} track(s)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Import Custom Songs for Dead as Disco\nPaste a song URL below:")
        url = input("URL: ").strip()
        if url:
            process_url(url)
        else:
            print("No URL provided.")
        input("\nPress Enter to exit...")
        sys.exit(0)

    for url in args:
        process_url(url)

    print("\nFinished.")
    input("Press Enter to exit...")
