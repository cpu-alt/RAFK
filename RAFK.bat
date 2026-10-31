@echo off
title RAFK - Roblox anti-AFK
cd /d "%~dp0"
if not exist config.toml copy config.example.toml config.toml >nul
python -m rafk %*
pause
