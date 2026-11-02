@echo off
setlocal
chcp 65001 > nul
title LALGONDAR(8-1)converter // Rhino 8 to 7 Down-Converter
mode con: cols=105 lines=38

:: Locate Python script
set "SCRIPT_PATH=%~dp0lalgondar_converter.py"
if not exist "%SCRIPT_PATH%" (
    if exist "d:\VibeCodingPlugin\lalgondar_converter.py" (
        set "SCRIPT_PATH=d:\VibeCodingPlugin\lalgondar_converter.py"
    )
)

if not exist "%SCRIPT_PATH%" (
    echo.
    echo [ERROR] Could not find 'lalgondar_converter.py'.
    echo Expected at: %~dp0lalgondar_converter.py
    echo.
    pause
    exit /b 1
)

:: Locate Python executable
set "PY_CMD="
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    echo.
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.9+ and check 'Add python.exe to PATH'.
    echo.
    pause
    exit /b 1
)

:: Run LALGONDAR(8-1)converter
if not "%~1"=="" (
    %PY_CMD% "%SCRIPT_PATH%" %*
) else (
    %PY_CMD% "%SCRIPT_PATH%"
)

exit /b 0
