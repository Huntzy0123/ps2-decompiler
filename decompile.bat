@echo off
REM PS2 ISO Decompilation Pipeline (Windows)
REM Extracts ELF from ISO and runs Ghidra analysis

setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "EXTRACT_ONLY=0"
set "ANALYZE_ONLY=0"
set "BATCH=0"

:parse_args
if "%~1"=="" goto after_parse
if /I "%~1"=="--extract-only" (
    set "EXTRACT_ONLY=1"
    shift
    goto parse_args
)
if /I "%~1"=="--analyze-only" (
    set "ANALYZE_ONLY=1"
    shift
    goto parse_args
)
if /I "%~1"=="--batch" (
    set "BATCH=1"
    shift
    goto parse_args
)
if /I "%~1"=="--help" goto usage
if /I "%~1"=="-h" goto usage
goto after_parse

:usage
echo PS2 Decompilation Pipeline
echo.
echo Usage: %~nx0 ^<iso_file^> [output_directory]
echo        %~nx0 --batch ^<iso_directory^> [output_directory]
echo.
echo Options:
echo   --extract-only    Only extract ELF, skip Ghidra analysis
echo   --analyze-only    Only run Ghidra (expects ELF input)
echo   --batch           Process all ISOs in directory
echo   --help            Show this help
echo.
echo Examples:
echo   %~nx0 game.iso
echo   %~nx0 --batch .\isos\ .\output\
echo   %~nx0 --extract-only game.iso
exit /b 0

:after_parse
set "INPUT=%~1"
set "OUTPUT=%~2"
if "%OUTPUT%"=="" set "OUTPUT=.\output"

if "%INPUT%"=="" goto usage

REM Prefer `py -3`, then `python`, then `python3`
set "PYTHON="
where py >nul 2>&1 && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON where python3 >nul 2>&1 && set "PYTHON=python3"
if not defined PYTHON (
    echo ERROR: Python 3 not found on PATH. Install Python 3.8+ from https://python.org
    exit /b 1
)

if not exist "%OUTPUT%" mkdir "%OUTPUT%"

echo ========================================
echo PS2 Decompilation Pipeline
echo ========================================
echo Input: %INPUT%
echo Output: %OUTPUT%
echo.

if "%ANALYZE_ONLY%"=="0" (
    echo === Step 1: Extracting ELF from ISO ===
    if "%BATCH%"=="1" (
        %PYTHON% "%SCRIPT_DIR%scripts\extract_elf.py" --batch "%INPUT%" "%OUTPUT%\elfs"
    ) else (
        %PYTHON% "%SCRIPT_DIR%scripts\extract_elf.py" "%INPUT%" "%OUTPUT%\elfs"
    )
    if errorlevel 1 exit /b 1
    echo.
)

if "%EXTRACT_ONLY%"=="0" (
    echo === Step 2: Ghidra Analysis ===
    set "ELF_DIR=%OUTPUT%\elfs"
    if "%ANALYZE_ONLY%"=="1" set "ELF_DIR=%INPUT%"

    if exist "!ELF_DIR!\" (
        %PYTHON% "%SCRIPT_DIR%scripts\ghidra_analyze.py" --batch "!ELF_DIR!" "%OUTPUT%\decompiled"
    ) else if exist "!ELF_DIR!" (
        %PYTHON% "%SCRIPT_DIR%scripts\ghidra_analyze.py" "!ELF_DIR!" "%OUTPUT%\decompiled"
    ) else (
        echo WARNING: ELF path not found: !ELF_DIR!
    )
    if errorlevel 1 exit /b 1
)

echo.
echo ========================================
echo Pipeline Complete!
echo ========================================
echo Output directory: %OUTPUT%
dir "%OUTPUT%"
exit /b 0
