#!/bin/bash
# PS2 ISO Decompilation Pipeline
# Extracts ELF from ISO and runs Ghidra analysis

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
        python3 "$SCRIPT_DIR/scripts/extract_elf.py" --batch "$INPUT" "$OUTPUT/elfs"
    else
        python3 "$SCRIPT_DIR/scripts/extract_elf.py" "$INPUT" "$OUTPUT/elfs"
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
        python3 "$SCRIPT_DIR/scripts/ghidra_analyze.py" --batch "$ELF_DIR" "$OUTPUT/decompiled"
    elif [ -f "$ELF_DIR" ]; then
        python3 "$SCRIPT_DIR/scripts/ghidra_analyze.py" "$ELF_DIR" "$OUTPUT/decompiled"
    fi
fi

echo ""
echo "========================================"
echo "Pipeline Complete!"
echo "========================================"
echo "Output directory: $OUTPUT"
ls -la "$OUTPUT"
