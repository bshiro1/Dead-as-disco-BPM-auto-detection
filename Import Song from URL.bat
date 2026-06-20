@echo off
title DaD Custom Song Importer
echo DaD Custom Song Importer - Paste a song URL
echo.
python "%~dp0src\DaD_Custom_Song_Importer.py" %*
if errorlevel 1 pause
