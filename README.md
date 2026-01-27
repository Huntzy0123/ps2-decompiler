# PS2 Decompiler Toolkit

A comprehensive toolkit for PlayStation 2 reverse engineering and decompilation, featuring automated ELF extraction from ISOs and integration with Ghidra's Emotion Engine extension.

## Features

- **ISO Extraction**: Automatically extract ELF executables from PS2 disc images (ISO/BIN)
- **Symbol Recovery**: Extract debug symbols using CCC (stdump, uncc, demangle)
- **Ghidra Integration**: Full support via [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded)
- **Automated Workflow**: End-to-end pipeline from ISO to decompiled C code

## Requirements

- **Python 3.8+**
- **Ghidra 11.4+** with [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded) extension
- **CMake** (for building CCC tools)
- **macOS/Linux** (Windows support possible with modifications)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ps2-decompiler.git
cd ps2-decompiler
```

### 2. Build CCC Tools

```bash
cd tools/ccc
cmake -B bin/
cmake --build bin/
cd ../..
```

### 3. Install Ghidra Extension

Download the latest release from [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases) and install to your Ghidra extensions folder:

```bash
# macOS
unzip ghidra-emotionengine-reloaded.zip -d /Applications/Ghidra/Ghidra/Extensions/
```

### 4. Verify Installation

```bash
# Check CCC tools
./tools/ccc/bin/stdump --help

# Check extract script
python3 scripts/extract_elf.py --help
```

## Quick Start

### Extract ELF from ISO

```bash
# Single ISO
python3 scripts/extract_elf.py game.iso ./elfs/

# List ISO contents without extracting
python3 scripts/extract_elf.py --list game.iso

# Batch process multiple ISOs
python3 scripts/extract_elf.py --batch ./isos/ ./elfs/
```

### Extract Debug Symbols (if available)

```bash
# Check what symbol tables exist
./tools/ccc/bin/stdump identify game.elf

# Extract types, functions, globals
./tools/ccc/bin/stdump types game.elf > types.h
./tools/ccc/bin/stdump functions game.elf > functions.cpp
./tools/ccc/bin/stdump globals game.elf > globals.cpp
```

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
| `decompile.sh` | Shell wrapper for common operations |

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
│   └── ghidra_analyze.py   # Headless Ghidra wrapper
├── tools/
│   └── ccc/                # CCC symbol extraction tools
│       └── bin/
│           ├── stdump      # Symbol table dumper
│           ├── uncc        # Source file organizer
│           └── demangle    # C++ demangler
├── isos/                   # Place your ISO files here
├── elfs/                   # Extracted ELF files
├── output/                 # Analysis output
├── decompile.sh           # Main shell script
└── README.md
```

## Workflow Examples

### Example 1: Full Game Analysis

```bash
# 1. Place your ISO in the isos folder
cp "My Game.iso" isos/

# 2. Extract the ELF
python3 scripts/extract_elf.py "isos/My Game.iso" elfs/

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
python3 scripts/extract_elf.py --batch isos/ elfs/

# Extract symbols from all ELFs
for elf in elfs/*.elf; do
    name=$(basename "$elf" .elf)
    ./tools/ccc/bin/stdump types "$elf" > "output/${name}_types.h"
done
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

### PCSX2 save states won't import
Change PCSX2 compression from zstd to Deflate64 in settings.

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
