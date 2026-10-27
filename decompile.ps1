# PS2 ISO Decompilation Pipeline (PowerShell)
# Extracts ELF from ISO and runs Ghidra analysis

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$InputPath,

    [Parameter(Position = 1)]
    [string]$OutputDirectory = ".\output",

    [switch]$ExtractOnly,
    [switch]$AnalyzeOnly,
    [switch]$Batch,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Usage {
    Write-Host @"
PS2 Decompilation Pipeline

Usage: .\decompile.ps1 <iso_file> [output_directory]
       .\decompile.ps1 -Batch <iso_directory> [output_directory]

Options:
  -ExtractOnly    Only extract ELF, skip Ghidra analysis
  -AnalyzeOnly    Only run Ghidra (expects ELF input)
  -Batch          Process all ISOs in directory
  -Help           Show this help

Examples:
  .\decompile.ps1 game.iso
  .\decompile.ps1 -Batch .\isos\ .\output\
  .\decompile.ps1 -ExtractOnly game.iso
"@
}

if ($Help -or [string]::IsNullOrWhiteSpace($InputPath)) {
    Show-Usage
    if ($Help) { exit 0 }
    exit 1
}

function Resolve-Python {
    foreach ($candidate in @(
        @{ File = "py"; Args = @("-3") },
        @{ File = "python"; Args = @() },
        @{ File = "python3"; Args = @() }
    )) {
        $cmd = Get-Command $candidate.File -ErrorAction SilentlyContinue
        if ($cmd) {
            return @{ File = $cmd.Source; Args = $candidate.Args }
        }
    }
    throw "Python 3 not found on PATH. Install Python 3.8+ from https://python.org"
}

$Python = Resolve-Python
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

Write-Host "========================================"
Write-Host "PS2 Decompilation Pipeline"
Write-Host "========================================"
Write-Host "Input: $InputPath"
Write-Host "Output: $OutputDirectory"
Write-Host ""

function Invoke-PythonScript {
    param([string[]]$ScriptArgs)
    & $Python.File @($Python.Args + $ScriptArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

if (-not $AnalyzeOnly) {
    Write-Host "=== Step 1: Extracting ELF from ISO ==="
    $extractArgs = @(
        (Join-Path $ScriptDir "scripts\extract_elf.py")
    )
    if ($Batch) {
        $extractArgs += @("--batch", $InputPath, (Join-Path $OutputDirectory "elfs"))
    } else {
        $extractArgs += @($InputPath, (Join-Path $OutputDirectory "elfs"))
    }
    Invoke-PythonScript -ScriptArgs $extractArgs
    Write-Host ""
}

if (-not $ExtractOnly) {
    Write-Host "=== Step 2: Ghidra Analysis ==="
    $ElfDir = if ($AnalyzeOnly) { $InputPath } else { Join-Path $OutputDirectory "elfs" }

    $analyzeArgs = @(Join-Path $ScriptDir "scripts\ghidra_analyze.py")
    if (Test-Path $ElfDir -PathType Container) {
        $analyzeArgs += @("--batch", $ElfDir, (Join-Path $OutputDirectory "decompiled"))
    } elseif (Test-Path $ElfDir -PathType Leaf) {
        $analyzeArgs += @($ElfDir, (Join-Path $OutputDirectory "decompiled"))
    } else {
        Write-Warning "ELF path not found: $ElfDir"
        exit 0
    }
    Invoke-PythonScript -ScriptArgs $analyzeArgs
}

Write-Host ""
Write-Host "========================================"
Write-Host "Pipeline Complete!"
Write-Host "========================================"
Write-Host "Output directory: $OutputDirectory"
Get-ChildItem $OutputDirectory
