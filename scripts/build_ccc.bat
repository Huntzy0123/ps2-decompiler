@echo off
REM Build CCC tools on Windows with a generator that matches the local toolchain.
REM Prefer Visual Studio; fall back to Ninja, then NMake (no -A for Makefile generators).

setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "CCC_DIR=%SCRIPT_DIR%..\tools\ccc"
set "BUILD_DIR=%CCC_DIR%\bin"

if not exist "%CCC_DIR%\CMakeLists.txt" (
    echo ERROR: CCC sources not found at "%CCC_DIR%"
    echo Run: git submodule update --init --recursive
    exit /b 1
)

where cmake >nul 2>&1
if errorlevel 1 (
    echo ERROR: cmake not found on PATH.
    echo Install CMake and/or open a "Developer Command Prompt for VS".
    exit /b 1
)

if exist "%BUILD_DIR%" (
    echo Cleaning previous build directory...
    rmdir /s /q "%BUILD_DIR%"
)

echo Configuring CCC in "%BUILD_DIR%"...

REM Try Visual Studio generators first (these support -A x64)
for %%G in ("Visual Studio 17 2022" "Visual Studio 16 2019" "Visual Studio 15 2017") do (
    echo Trying generator %%~G ...
    cmake -S "%CCC_DIR%" -B "%BUILD_DIR%" -G %%G -A x64
    if not errorlevel 1 goto build_vs
)

REM Ninja (single-config; architecture comes from the environment / compiler)
where ninja >nul 2>&1
if not errorlevel 1 (
    echo Trying generator Ninja ...
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    cmake -S "%CCC_DIR%" -B "%BUILD_DIR%" -G Ninja -DCMAKE_BUILD_TYPE=Release
    if not errorlevel 1 goto build_ninja
)

REM NMake: do NOT pass -A; use an x64 Native Tools prompt so cl targets x64
echo Trying generator "NMake Makefiles" ...
echo NOTE: Open "x64 Native Tools Command Prompt for VS" before this if you need 64-bit.
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
cmake -S "%CCC_DIR%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo.
    echo ERROR: CMake configure failed.
    echo.
    echo Fix options:
    echo   1. Install Visual Studio 2022 with "Desktop development with C++"
    echo   2. Or install Ninja and re-run this script
    echo   3. Or from "x64 Native Tools Command Prompt for VS":
    echo        cd tools\ccc
    echo        cmake -B bin -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
    echo        cmake --build bin
    exit /b 1
)
goto build_ninja

:build_vs
echo Building Release...
cmake --build "%BUILD_DIR%" --config Release
if errorlevel 1 exit /b 1
goto locate

:build_ninja
echo Building...
cmake --build "%BUILD_DIR%"
if errorlevel 1 exit /b 1
goto locate

:locate
echo.
echo Looking for built tools...
set "FOUND=0"
for %%T in (stdump uncc demangle) do (
    if exist "%BUILD_DIR%\%%T.exe" (
        echo   FOUND: %BUILD_DIR%\%%T.exe
        set "FOUND=1"
    ) else if exist "%BUILD_DIR%\Release\%%T.exe" (
        echo   FOUND: %BUILD_DIR%\Release\%%T.exe
        set "FOUND=1"
    ) else if exist "%BUILD_DIR%\Debug\%%T.exe" (
        echo   FOUND: %BUILD_DIR%\Debug\%%T.exe
        set "FOUND=1"
    ) else (
        echo   MISSING: %%T.exe
    )
)

if "%FOUND%"=="0" (
    echo.
    echo WARNING: No CCC .exe files found. Check the build log above.
    exit /b 1
)

echo.
echo CCC build complete. Scripts will find tools under tools\ccc\bin\ ^(including Release\^).
exit /b 0
