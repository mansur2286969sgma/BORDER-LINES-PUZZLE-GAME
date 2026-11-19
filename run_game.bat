@echo off
title BORDER LINES - Bureaucratic Logic Puzzle
echo Starting BORDER LINES...
python main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start the game. Make sure Python 3.8+ and pygame are installed:
    echo   pip install -r requirements.txt
    pause
)
