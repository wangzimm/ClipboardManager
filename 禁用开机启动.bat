@echo off
chcp 65001 >nul

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ClipboardManager" /f

if %errorlevel% equ 0 (
    echo [OK] Auto-start disabled!
) else (
    echo [INFO] Auto-start was not enabled.
)
pause
