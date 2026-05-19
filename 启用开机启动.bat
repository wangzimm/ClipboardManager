@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "APP_PATH=%CD%\dist\历史粘贴板.exe"

if not exist "%APP_PATH%" (
    echo [Error] EXE not found: %APP_PATH%
    pause
    exit /b 1
)

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ClipboardManager" /t REG_SZ /d "%APP_PATH%" /f

if %errorlevel% equ 0 (
    echo [OK] Auto-start enabled!
) else (
    echo [FAIL] Registry write failed.
)
pause
