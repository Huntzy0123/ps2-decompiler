#!/bin/bash
# PS2 ISO Decompilation Pipeline
# Extracts ELF from ISO and runs Ghidra analysis
# On Windows, use decompile.bat or decompile.ps1 instead.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer python3, fall back to python
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found on PATH"
    exit 1
fi

usage() {
    echo "PS2 Decompilation Pipeline"
    echo ""
    echo "Usage: $0 <iso_file> [output_directory]"
    echo "       $0 --batch <iso_directory> [output_directory]"
    echo ""
    echo "Options:"
    echo "  --extract-only    Only extract ELF, skip Ghidra analysis"
    echo "  --analyze-only    Only run Ghidra (expects ELF input)"
    echo "  --batch           Process all ISOs in directory"
    echo "  --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 game.iso"
    echo "  $0 --batch ./isos/ ./output/"
    echo "  $0 --extract-only game.iso"
    echo ""
    echo "Windows: use decompile.bat or .\\decompile.ps1"
}

EXTRACT_ONLY=false
ANALYZE_ONLY=false
BATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --extract-only)
            EXTRACT_ONLY=true
            shift
            ;;
        --analyze-only)
            ANALYZE_ONLY=true
            shift
            ;;
        --batch)
            BATCH=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

INPUT="$1"
OUTPUT="${2:-./output}"

if [ -z "$INPUT" ]; then
    usage
    exit 1
fi

mkdir -p "$OUTPUT"

echo "========================================"
echo "PS2 Decompilation Pipeline"
echo "========================================"
echo "Input: $INPUT"
echo "Output: $OUTPUT"
echo ""

if [ "$ANALYZE_ONLY" = false ]; then
    echo "=== Step 1: Extracting ELF from ISO ==="
    
    if [ "$BATCH" = true ]; then
        "$PYTHON" "$SCRIPT_DIR/scripts/extract_elf.py" --batch "$INPUT" "$OUTPUT/elfs"
    else
        "$PYTHON" "$SCRIPT_DIR/scripts/extract_elf.py" "$INPUT" "$OUTPUT/elfs"
    fi
    
    echo ""
fi

if [ "$EXTRACT_ONLY" = false ]; then
    echo "=== Step 2: Ghidra Analysis ==="
    
    ELF_DIR="$OUTPUT/elfs"
    if [ "$ANALYZE_ONLY" = true ]; then
        ELF_DIR="$INPUT"
    fi
    
    if [ -d "$ELF_DIR" ]; then
        "$PYTHON" "$SCRIPT_DIR/scripts/ghidra_analyze.py" --batch "$ELF_DIR" "$OUTPUT/decompiled"
    elif [ -f "$ELF_DIR" ]; then
        "$PYTHON" "$SCRIPT_DIR/scripts/ghidra_analyze.py" "$ELF_DIR" "$OUTPUT/decompiled"
    fi
fi

echo ""
echo "========================================"
echo "Pipeline Complete!"
echo "========================================"
echo "Output directory: $OUTPUT"
ls -la "$OUTPUT"
