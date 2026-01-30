@echo off
echo ============================================
echo   Live Darshan Stream Updater
echo ============================================
echo.

cd /d "d:\Experiements\livedarshan_automation"

echo [1/3] Finding live streams...
"D:\Experiements\livedarshan_automation\.venv\Scripts\python.exe" find_live_streams.py

echo.
echo [2/3] Committing changes...
git add live_streams.json
git commit -m "Update live streams - %date% %time%"

echo.
echo [3/3] Pushing to GitHub...
git push

echo.
echo ============================================
echo   Done! Streams updated on GitHub.
echo ============================================
echo.
pause
