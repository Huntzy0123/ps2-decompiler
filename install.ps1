#Requires -Version 5.1
<#
.SYNOPSIS
  Install / set up the PS2 Decompiler Toolkit on Windows.

.DESCRIPTION
  Checks prerequisites, initializes the CCC git submodule, builds CCC tools
  with an appropriate CMake generator, optionally records GHIDRA_INSTALL_DIR,
  and verifies the install.

.PARAMETER GhidraInstallDir
  Path to your Ghidra root folder (contains support\analyzeHeadless.bat).
  Stored as a User environment variable when provided.

.PARAMETER SkipBuild
  Skip building CCC (only check tools / set Ghidra path).

.PARAMETER SkipSubmodule
  Skip git submodule update.

.PARAMETER Clean
  Delete tools\ccc\bin before configuring (default: true when building).

.EXAMPLE
  .\install.ps1

.EXAMPLE
  .\install.ps1 -GhidraInstallDir "C:\ghidra_11.4_PUBLIC"
#>

[CmdletBinding()]
param(
    [string]$GhidraInstallDir,
    [switch]$SkipBuild,
    [switch]$SkipSubmodule,
    [bool]$Clean = $true
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location | Select-Object -ExpandProperty Path }

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail([string]$Message) {
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Resolve-Python {
    foreach ($candidate in @(
        @{ File = "py"; Args = @("-3") },
        @{ File = "python"; Args = @() },
        @{ File = "python3"; Args = @() }
    )) {
        $cmd = Get-Command $candidate.File -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $versionArgs = $candidate.Args + @("-c", "import sys; print('%d.%d'%sys.version_info[:2]); sys.exit(0 if sys.version_info >= (3,8) else 1)")
            $out = & $cmd.Source @versionArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                return @{ File = $cmd.Source; Args = $candidate.Args; Version = "$out".Trim() }
            }
        } catch {
            continue
        }
    }
    return $null
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $Root
    )
    Write-Host "  > $FilePath $($ArgumentList -join ' ')" -ForegroundColor DarkGray
    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
            throw "Command failed (exit $LASTEXITCODE): $FilePath $($ArgumentList -join ' ')"
        }
    } finally {
        Pop-Location
    }
}

function Find-CccTool([string]$Name) {
    $bin = Join-Path $Root "tools\ccc\bin"
    $candidates = @(
        (Join-Path $bin "$Name.exe"),
        (Join-Path $bin $Name),
        (Join-Path $bin "Release\$Name.exe"),
        (Join-Path $bin "Debug\$Name.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Find-GhidraInstall([string]$Hint) {
    $names = @("analyzeHeadless.bat", "analyzeHeadless")
    $roots = New-Object System.Collections.Generic.List[string]

    if ($Hint) { $roots.Add($Hint) }
    foreach ($envName in @("GHIDRA_INSTALL_DIR", "GHIDRA_HOME")) {
        $v = [Environment]::GetEnvironmentVariable($envName, "User")
        if (-not $v) { $v = [Environment]::GetEnvironmentVariable($envName, "Machine") }
        if (-not $v) { $v = [Environment]::GetEnvironmentVariable($envName, "Process") }
        if ($v) { $roots.Add($v) }
    }
    $direct = [Environment]::GetEnvironmentVariable("GHIDRA_PATH", "User")
    if (-not $direct) { $direct = $env:GHIDRA_PATH }
    if ($direct -and (Test-Path $direct)) { return $direct }

    foreach ($base in @(
        ${env:ProgramFiles},
        ${env:ProgramFiles(x86)},
        $env:LOCALAPPDATA,
        $env:USERPROFILE,
        "C:\"
    )) {
        if (-not $base -or -not (Test-Path $base)) { continue }
        foreach ($folder in @("Ghidra", "ghidra")) {
            $roots.Add((Join-Path $base $folder))
        }
        Get-ChildItem -Path $base -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "ghidra*" } |
            ForEach-Object { $roots.Add($_.FullName) }
    }

    foreach ($root in ($roots | Select-Object -Unique)) {
        if (-not $root) { continue }
        foreach ($n in $names) {
            $p = Join-Path $root "support\$n"
            if (Test-Path $p) { return $p }
            if ((Split-Path $root -Leaf) -like "analyzeHeadless*") {
                if (Test-Path $root) { return $root }
            }
        }
    }

    foreach ($n in $names) {
        $which = Get-Command $n -ErrorAction SilentlyContinue
        if ($which) { return $which.Source }
    }
    return $null
}

function Build-Ccc {
    param([bool]$DoClean)

    $cccDir = Join-Path $Root "tools\ccc"
    $buildDir = Join-Path $cccDir "bin"
    $cmakeLists = Join-Path $cccDir "CMakeLists.txt"

    if (-not (Test-Path $cmakeLists)) {
        throw "CCC sources missing at $cccDir. Run with submodule init (omit -SkipSubmodule)."
    }
    if (-not (Test-CommandExists "cmake")) {
        throw "cmake not found on PATH. Install CMake and/or open a Developer PowerShell for VS."
    }

    if ($DoClean -and (Test-Path $buildDir)) {
        Write-Host "  Cleaning $buildDir ..."
        Remove-Item -Recurse -Force $buildDir
    }

    $configured = $false
    $multiConfig = $false

    $vsGenerators = @(
        "Visual Studio 17 2022",
        "Visual Studio 16 2019",
        "Visual Studio 15 2017"
    )

    foreach ($gen in $vsGenerators) {
        Write-Host "  Trying generator: $gen"
        if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
        & cmake -S $cccDir -B $buildDir -G $gen -A x64
        if ($LASTEXITCODE -eq 0) {
            $configured = $true
            $multiConfig = $true
            Write-Ok "Configured with $gen"
            break
        }
        Write-Warn "Generator failed: $gen"
    }

    if (-not $configured -and (Test-CommandExists "ninja")) {
        Write-Host "  Trying generator: Ninja"
        if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
        & cmake -S $cccDir -B $buildDir -G Ninja -DCMAKE_BUILD_TYPE=Release
        if ($LASTEXITCODE -eq 0) {
            $configured = $true
            Write-Ok "Configured with Ninja"
        }
    }

    if (-not $configured) {
        Write-Host "  Trying generator: NMake Makefiles (no -A; use x64 Native Tools prompt)"
        if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
        & cmake -S $cccDir -B $buildDir -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
        if ($LASTEXITCODE -eq 0) {
            $configured = $true
            Write-Ok "Configured with NMake Makefiles"
        }
    }

    if (-not $configured) {
        throw @"
CMake configure failed for CCC.

Install one of:
  - Visual Studio 2022 with 'Desktop development with C++'
  - Ninja + a C++ compiler
  - Build Tools, then open 'x64 Native Tools Command Prompt for VS' / Developer PowerShell

Then re-run: .\install.ps1
"@
    }

    Write-Host "  Building CCC..."
    if ($multiConfig) {
        Invoke-External -FilePath "cmake" -ArgumentList @("--build", $buildDir, "--config", "Release")
    } else {
        Invoke-External -FilePath "cmake" -ArgumentList @("--build", $buildDir)
    }

    $missing = @()
    foreach ($tool in @("stdump", "uncc", "demangle")) {
        $path = Find-CccTool $tool
        if ($path) { Write-Ok "$tool -> $path" }
        else {
            Write-Fail "$tool.exe not found under tools\ccc\bin"
            $missing += $tool
        }
    }
    if ($missing.Count -gt 0) {
        throw "CCC build finished but missing: $($missing -join ', ')"
    }
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

Write-Host "PS2 Decompiler Toolkit - Windows installer" -ForegroundColor White
Write-Host "Root: $Root"

$failures = New-Object System.Collections.Generic.List[string]

Write-Step "Checking prerequisites"

$python = Resolve-Python
if ($python) {
    Write-Ok "Python $($python.Version) ($($python.File))"
} else {
    Write-Fail "Python 3.8+ not found on PATH"
    $failures.Add("Install Python 3.8+ from https://www.python.org/downloads/ (enable Add to PATH)")
}

if (Test-CommandExists "git") {
    Write-Ok "git $((git --version) -replace 'git version ','')"
} else {
    Write-Fail "git not found"
    $failures.Add("Install Git for Windows: https://git-scm.com/download/win")
}

if (Test-CommandExists "cmake") {
    Write-Ok "$((cmake --version | Select-Object -First 1))"
} else {
    Write-Fail "cmake not found"
    $failures.Add("Install CMake: https://cmake.org/download/ (or Visual Studio C++ workload)")
}

if ($failures.Count -gt 0 -and -not $SkipBuild) {
    Write-Host ""
    Write-Host "Cannot continue until prerequisites are installed:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

if (-not $SkipSubmodule) {
    Write-Step "Initializing git submodules (CCC)"
    if (-not (Test-CommandExists "git")) {
        throw "git is required for submodule setup"
    }
    Push-Location $Root
    try {
        & git submodule update --init --recursive
        if ($LASTEXITCODE -ne 0) {
            throw "git submodule update failed (exit $LASTEXITCODE)"
        }
        Write-Ok "Submodules ready"
    } finally {
        Pop-Location
    }
} else {
    Write-Step "Skipping submodule update (-SkipSubmodule)"
}

if ($PSBoundParameters.ContainsKey("GhidraInstallDir") -or $GhidraInstallDir) {
    Write-Step "Configuring Ghidra path"
    if (-not $GhidraInstallDir) {
        throw "-GhidraInstallDir was specified but empty"
    }
    $ghidraRoot = $GhidraInstallDir.TrimEnd('\', '/')
    $headless = Join-Path $ghidraRoot "support\analyzeHeadless.bat"
    if (-not (Test-Path $headless)) {
        throw "analyzeHeadless.bat not found at $headless"
    }
    [Environment]::SetEnvironmentVariable("GHIDRA_INSTALL_DIR", $ghidraRoot, "User")
    $env:GHIDRA_INSTALL_DIR = $ghidraRoot
    Write-Ok "Set User env GHIDRA_INSTALL_DIR=$ghidraRoot"
    Write-Warn "Open a new terminal later so other apps see the User variable"
} else {
    Write-Step "Looking for Ghidra"
    $found = Find-GhidraInstall $GhidraInstallDir
    if ($found) {
        Write-Ok "Ghidra headless: $found"
        $support = Split-Path $found -Parent
        $guessRoot = Split-Path $support -Parent
        if (-not $env:GHIDRA_INSTALL_DIR -and (Test-Path (Join-Path $guessRoot "support"))) {
            Write-Host "  Tip: persist this with:" -ForegroundColor DarkGray
            Write-Host "    .\install.ps1 -GhidraInstallDir `"$guessRoot`" -SkipBuild -SkipSubmodule" -ForegroundColor DarkGray
        }
    } else {
        Write-Warn "Ghidra not found. Install Ghidra 11.4+, then re-run:"
        Write-Host "    .\install.ps1 -GhidraInstallDir `"C:\path\to\ghidra_XX_PUBLIC`" -SkipBuild" -ForegroundColor DarkGray
        Write-Warn "Also install ghidra-emotionengine-reloaded via File -> Install Extensions"
    }
}

if (-not $SkipBuild) {
    Write-Step "Building CCC tools"
    Build-Ccc -DoClean:$Clean
} else {
    Write-Step "Skipping CCC build (-SkipBuild)"
}

Write-Step "Verifying toolkit"
$verifyOk = $true
foreach ($tool in @("stdump", "uncc", "demangle")) {
    $path = Find-CccTool $tool
    if ($path) { Write-Ok $tool }
    else {
        Write-Fail "$tool missing"
        $verifyOk = $false
    }
}

$ghidraNow = Find-GhidraInstall $GhidraInstallDir
if ($ghidraNow) { Write-Ok "ghidra" } else {
    Write-Warn "ghidra missing (optional for ISO extraction / CCC-only workflows)"
}

if ($python) {
    $checkScript = Join-Path $Root "scripts\ps2_workflow.py"
    Write-Host "  Running: ps2_workflow.py --check-tools"
    & $python.File @($python.Args + @($checkScript, "--check-tools"))
}

Write-Host ""
if ($verifyOk) {
    Write-Host "Install complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  python scripts\extract_elf.py game.iso .\elfs\"
    Write-Host "  .\decompile.ps1 game.iso"
    Write-Host "  python scripts\ps2_workflow.py game.iso -o output"
    if (-not $ghidraNow) {
        Write-Host ""
        Write-Host "When Ghidra is installed:"
        Write-Host "  .\install.ps1 -GhidraInstallDir `"C:\path\to\ghidra`" -SkipBuild -SkipSubmodule"
    }
    exit 0
} else {
    Write-Host "Install finished with missing CCC tools. Re-run without -SkipBuild after fixing the C++ toolchain." -ForegroundColor Yellow
    exit 1
}
