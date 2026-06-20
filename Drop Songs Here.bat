@echo off
title DaD BPM Auto-Detect
echo DaD BPM Auto-Detect - Drag M4A/MP3/FLAC/OGG/WAV files or folders onto this window
echo.
python "%~dp0src\DaD_BPM_AutoDetect.py" %*
if errorlevel 1 pause
