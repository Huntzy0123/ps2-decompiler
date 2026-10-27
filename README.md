# PS2 Decompiler Toolkit

A comprehensive toolkit for PlayStation 2 reverse engineering and decompilation, featuring automated ELF extraction from ISOs and integration with Ghidra's Emotion Engine extension.

## Features

- **ISO Extraction**: Automatically extract ELF executables from PS2 disc images (ISO/BIN)
- **Symbol Recovery**: Extract debug symbols using CCC (stdump, uncc, demangle)
- **Ghidra Integration**: Full support via [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded)
- **Automated Workflow**: End-to-end pipeline from ISO to decompiled C code
- **Cross-platform**: Works on Windows, macOS, and Linux

## Requirements

- **Python 3.8+**
- **Ghidra 11.4+** with [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded) extension
- **CMake** (for building CCC tools)
- **Windows, macOS, or Linux**

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ps2-decompiler.git
cd ps2-decompiler
```

On Windows, check out this repo then run the installer (recommended):

```powershell
cd ps2-decompiler
# If scripts are blocked once:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

.\install.ps1
# With Ghidra already installed:
.\install.ps1 -GhidraInstallDir "C:\ghidra_11.4_PUBLIC"
```

`install.ps1` checks Python/Git/CMake, initializes the CCC submodule, builds CCC
(with Visual Studio / Ninja / NMake — avoiding the invalid `-A x64` + NMake combo),
optionally sets `GHIDRA_INSTALL_DIR`, and runs a tool check.

### 2. Build CCC Tools (manual)

**macOS / Linux:**

```bash
cd tools/ccc
cmake -B bin/
cmake --build bin/
cd ../..
```

**Windows (without install.ps1):**

```bat
git submodule update --init --recursive
scripts\build_ccc.bat
```

Or configure manually. **Do not pass `-A x64` with NMake** — that combination causes  
`Generator NMake Makefiles does not support platform specification`.

```bat
cd tools\ccc

REM Clean a bad/partial configure if you hit generator errors:
rmdir /s /q bin

REM Preferred: Visual Studio generator (supports -A x64)
cmake -B bin -G "Visual Studio 17 2022" -A x64
cmake --build bin --config Release

REM Alternative: Ninja (no -A)
REM cmake -B bin -G Ninja -DCMAKE_BUILD_TYPE=Release
REM cmake --build bin

REM Alternative: NMake from "x64 Native Tools Command Prompt for VS" (no -A)
REM cmake -B bin -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
REM cmake --build bin

cd ..\..
```

Built binaries land in `tools\ccc\bin\` or `tools\ccc\bin\Release\`. The Python scripts look in both places.

### 3. Install Ghidra Extension

Download the latest release from [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases) and install into your Ghidra extensions folder:

```bash
# macOS
unzip ghidra-emotionengine-reloaded.zip -d /Applications/Ghidra/Ghidra/Extensions/
```

```bat
REM Windows (adjust Ghidra path as needed)
tar -xf ghidra-emotionengine-reloaded.zip -C "%GHIDRA_INSTALL_DIR%\Ghidra\Extensions"
```

Or use Ghidra's UI: **File → Install Extensions…**

### 4. Point the toolkit at Ghidra (optional)

Scripts auto-detect Ghidra via common install locations and environment variables:

| Variable | Meaning |
|----------|---------|
| `GHIDRA_INSTALL_DIR` | Ghidra root (contains `support/`) |
| `GHIDRA_HOME` | Same as above |
| `GHIDRA_PATH` | Full path to `analyzeHeadless` / `analyzeHeadless.bat` |

**Windows example:**

```bat
setx GHIDRA_INSTALL_DIR "C:\ghidra_11.4_PUBLIC"
```

### 5. Verify Installation

```bash
# Check CCC tools (Unix)
./tools/ccc/bin/stdump --help

# Check CCC tools (Windows)
tools\ccc\bin\stdump.exe --help

# Check extract script
python scripts/extract_elf.py --help

# Check tool discovery
python scripts/ps2_workflow.py --check-tools
```

## Quick Start

### Extract ELF from ISO

```bash
# Single ISO
python scripts/extract_elf.py game.iso ./elfs/

# List ISO contents without extracting
python scripts/extract_elf.py --list game.iso

# Batch process multiple ISOs
python scripts/extract_elf.py --batch ./isos/ ./elfs/
```

### Extract Debug Symbols (if available)

```bash
# Unix
./tools/ccc/bin/stdump identify game.elf
./tools/ccc/bin/stdump types game.elf > types.h

# Windows
tools\ccc\bin\stdump.exe identify game.elf
tools\ccc\bin\stdump.exe types game.elf > types.h
```

### Full pipeline wrappers

| Platform | Command |
|----------|---------|
| macOS / Linux | `./decompile.sh game.iso` |
| Windows CMD | `decompile.bat game.iso` |
| Windows PowerShell | `.\decompile.ps1 game.iso` |
| Any (Python) | `python scripts/ps2_workflow.py game.iso -o output` |

### Analyze in Ghidra

1. Open Ghidra and create/open a project
2. **File → Import File** → Select your `.elf` file
3. **Processor**: Should auto-detect as `MIPS:LE:64:R5900`
4. Click **Analyze** when prompted
5. View decompiled C code in the Decompiler window

## Tools Reference

### Scripts

| Script | Description |
|--------|-------------|
| `scripts/extract_elf.py` | Extract ELF executables from PS2 ISOs |
| `scripts/ps2_workflow.py` | Full automated pipeline |
| `scripts/ghidra_analyze.py` | Headless Ghidra analysis |
| `scripts/platform_utils.py` | Cross-platform path / tool helpers |
| `install.ps1` | Windows installer (prereqs, CCC build, Ghidra env) |
| `decompile.sh` | Shell wrapper (macOS/Linux) |
| `decompile.bat` / `decompile.ps1` | Windows wrappers |
| `scripts/build_ccc.bat` | Windows CCC/CMake build helper |

### CCC Tools (Chaos Compiler Collection)

| Tool | Description |
|------|-------------|
| `stdump` | Extract STABS debug symbols (types, functions, globals) |
| `uncc` | Organize symbols into separate source files |
| `demangle` | Demangle C++ symbol names |
| `objdump` | MIPS disassembler |

### Ghidra Scripts (from emotionengine-reloaded)

| Script | Description |
|--------|-------------|
| `ImportSymFile.py` | Import .sym symbol files |
| `ExportDvpOverlays.py` | Export VU overlay data |
| `PCSX2SaveStateImporter.java` | Import PCSX2 save states for runtime analysis |
| `ImportMMIORegisterLabels.java` | Label PS2 hardware registers |

## Directory Structure

```
ps2-decompiler/
├── scripts/
│   ├── extract_elf.py      # ISO extraction tool
│   ├── ps2_workflow.py     # Full workflow automation
│   ├── ghidra_analyze.py   # Headless Ghidra wrapper
│   └── platform_utils.py   # Windows/macOS/Linux helpers
├── tools/
│   └── ccc/                # CCC symbol extraction tools
│       └── bin/
│           ├── stdump[.exe]
│           ├── uncc[.exe]
│           └── demangle[.exe]
├── isos/                   # Place your ISO files here
├── elfs/                   # Extracted ELF files
├── output/                 # Analysis output
├── decompile.sh            # Unix pipeline wrapper
├── decompile.bat           # Windows CMD wrapper
├── decompile.ps1           # Windows PowerShell wrapper
└── README.md
```

## Workflow Examples

### Example 1: Full Game Analysis

```bash
# 1. Place your ISO in the isos folder
cp "My Game.iso" isos/

# 2. Extract the ELF
python scripts/extract_elf.py "isos/My Game.iso" elfs/

# 3. Check for debug symbols
./tools/ccc/bin/stdump identify "elfs/My Game.elf"

# 4. If debug symbols exist, extract them
./tools/ccc/bin/stdump types "elfs/My Game.elf" > output/types.h
./tools/ccc/bin/stdump functions "elfs/My Game.elf" > output/functions.cpp

# 5. Open in Ghidra for full analysis
# Import elfs/My Game.elf with processor MIPS:LE:64:R5900
```

### Example 2: Batch Processing

```bash
# Process all ISOs in a folder
python scripts/extract_elf.py --batch isos/ elfs/

# Extract symbols from all ELFs (Unix)
for elf in elfs/*.elf; do
    name=$(basename "$elf" .elf)
    ./tools/ccc/bin/stdump types "$elf" > "output/${name}_types.h"
done
```

```bat
REM Extract symbols from all ELFs (Windows CMD)
for %%f in (elfs\*.elf) do tools\ccc\bin\stdump.exe types "%%f" > "output\%%~nf_types.h"
```

## PS2 Technical Notes

### Emotion Engine (EE) CPU
- **Architecture**: MIPS R5900 (64-bit with 128-bit multimedia extensions)
- **Processor ID in Ghidra**: `MIPS:LE:64:R5900`

### Common PS2 SDK Libraries
| Library | Purpose |
|---------|---------|
| `libgraph` | Graphics/GS interface |
| `libdma` | DMA controller |
| `libvu0/libvu1` | Vector Units |
| `libipu` | Image Processing (MPEG) |
| `libpad` | Controller input |
| `libcdvd` | CD/DVD access |
| `libmc` | Memory card |
| `libsdr` | Sound |

### Debug Symbol Types
- **`.mdebug`**: STABS debug info (best - full types and function signatures)
- **`.symtab`**: Basic ELF symbols (function names only)
- **Stripped**: No symbols (common in retail games)

## Troubleshooting

### CCC shows no symbols
Most retail PS2 games are stripped of debug symbols. Use Ghidra for analysis instead - it will:
- Auto-detect function boundaries
- Decompile to C code
- Apply PS2-specific patterns

### Ghidra doesn't detect R5900
1. Ensure ghidra-emotionengine-reloaded is installed
2. Manually select: `MIPS:LE:64:R5900` in the import dialog

### Ghidra not found on Windows
1. Set `GHIDRA_INSTALL_DIR` to your Ghidra root folder
2. Or pass `--ghidra` with the full path to `analyzeHeadless.bat`
3. Confirm Java is installed (Ghidra requires a JDK)

### CMake: NMake does not support platform specification (Windows)
You used `-A x64` with the NMake Makefiles generator. Fix:

```bat
cd tools\ccc
rmdir /s /q bin
scripts\build_ccc.bat
```

Or pick one generator explicitly (see Build CCC Tools above). Prefer Visual Studio 2022 with the **Desktop development with C++** workload, or use Ninja / an **x64 Native Tools** prompt with NMake and **no** `-A`.

### PCSX2 save states won't import
Change PCSX2 compression from zstd to Deflate64 in settings.

### PowerShell script blocked
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Or run via CMD: `decompile.bat ...`

## Resources

- [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded) - Ghidra PS2 extension
- [CCC](https://github.com/chaoticgd/ccc) - Symbol extraction tools
- [PS2 Dev Wiki](https://www.psdevwiki.com/ps2/) - Technical documentation
- [PCSX2](https://pcsx2.net/) - PS2 emulator for testing

## License

MIT License - See individual tool licenses for dependencies.

## Credits

- **CCC**: [chaoticgd](https://github.com/chaoticgd/ccc)
- **ghidra-emotionengine-reloaded**: [chaoticgd](https://github.com/chaoticgd/ghidra-emotionengine-reloaded)
- **Ghidra**: [NSA](https://github.com/NationalSecurityAgency/ghidra)
