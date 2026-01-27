#!/usr/bin/env python3
"""
PS2 Decompilation Workflow
Integrated pipeline for PS2 reverse engineering using:
- ISO extraction
- CCC symbol extraction (stdump)
- Ghidra analysis with emotionengine-reloaded

Usage:
    python3 ps2_workflow.py <iso_or_elf> [--output DIR]
    python3 ps2_workflow.py --symbols-only <elf_file>
    python3 ps2_workflow.py --ghidra <elf_file>
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple


# Tool paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CCC_BIN = PROJECT_DIR / "tools" / "ccc" / "bin"
STDUMP = CCC_BIN / "stdump"
UNCC = CCC_BIN / "uncc"
DEMANGLE = CCC_BIN / "demangle"

GHIDRA_PATH = "/Applications/Ghidra/support/analyzeHeadless"


def check_tools() -> dict:
    """Check which tools are available"""
    tools = {
        'stdump': STDUMP.exists(),
        'uncc': UNCC.exists(),
        'demangle': DEMANGLE.exists(),
        'ghidra': Path(GHIDRA_PATH).exists(),
    }
    return tools


def extract_symbols_stdump(elf_path: Path, output_dir: Path) -> Tuple[bool, str]:
    """
    Extract symbols from ELF using stdump (CCC)
    
    This extracts:
    - Data types (structs, unions, enums)
    - Function signatures
    - Global variables
    """
    if not STDUMP.exists():
        return False, f"stdump not found at {STDUMP}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate different outputs
    results = []
    
    # 1. Print symbols as C++ code
    cpp_output = output_dir / f"{elf_path.stem}_symbols.cpp"
    try:
        result = subprocess.run(
            [str(STDUMP), "symbols", str(elf_path), "--print-cpp"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            with open(cpp_output, 'w') as f:
                f.write(result.stdout)
            results.append(f"C++ symbols: {cpp_output}")
    except Exception as e:
        results.append(f"C++ export failed: {e}")
    
    # 2. Export as JSON for further processing
    json_output = output_dir / f"{elf_path.stem}_symbols.json"
    try:
        result = subprocess.run(
            [str(STDUMP), "symbols", str(elf_path), "--print-json"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            with open(json_output, 'w') as f:
                f.write(result.stdout)
            results.append(f"JSON symbols: {json_output}")
    except Exception as e:
        results.append(f"JSON export failed: {e}")
    
    # 3. List files (for uncc)
    files_output = output_dir / "SOURCES.txt"
    try:
        result = subprocess.run(
            [str(STDUMP), "files", str(elf_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            with open(files_output, 'w') as f:
                f.write(result.stdout)
            results.append(f"Source files: {files_output}")
    except Exception as e:
        results.append(f"Files list failed: {e}")
    
    # 4. Print all types
    types_output = output_dir / f"{elf_path.stem}_types.h"
    try:
        result = subprocess.run(
            [str(STDUMP), "types", str(elf_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            with open(types_output, 'w') as f:
                f.write(result.stdout)
            results.append(f"Types header: {types_output}")
    except Exception as e:
        results.append(f"Types export failed: {e}")
    
    return True, "\n".join(results)


def run_uncc(elf_path: Path, output_dir: Path) -> Tuple[bool, str]:
    """
    Run uncc to organize symbols into separate source files
    Requires SOURCES.txt in output_dir
    """
    if not UNCC.exists():
        return False, f"uncc not found at {UNCC}"
    
    sources_file = output_dir / "SOURCES.txt"
    if not sources_file.exists():
        return False, "SOURCES.txt not found. Run stdump files first."
    
    src_output = output_dir / "src"
    src_output.mkdir(exist_ok=True)
    
    try:
        result = subprocess.run(
            [str(UNCC), str(elf_path), str(src_output)],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            # Count generated files
            cpp_files = list(src_output.glob("**/*.cpp"))
            h_files = list(src_output.glob("**/*.h"))
            return True, f"Generated {len(cpp_files)} .cpp and {len(h_files)} .h files"
        else:
            return False, f"uncc failed: {result.stderr}"
    
    except Exception as e:
        return False, f"uncc error: {e}"


def create_ghidra_import_script(elf_path: Path, symbols_dir: Path, output_path: Path):
    """Create a Ghidra script to import symbols"""
    
    script_content = f'''
// Auto-generated Ghidra import script for {elf_path.name}
// @category PS2
// @runtime PyGhidra

import typing
if typing.TYPE_CHECKING:
    from ghidra.ghidra_builtins import *

import os
import json
from ghidra.program.model.symbol import SourceType
from ghidra.program.flatapi import FlatProgramAPI

def import_symbols():
    """Import symbols from CCC JSON output"""
    
    json_file = r"{symbols_dir / f'{elf_path.stem}_symbols.json'}"
    
    if not os.path.exists(json_file):
        print(f"Symbol file not found: {{json_file}}")
        return
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    flat_api = FlatProgramAPI(currentProgram)
    function_manager = currentProgram.functionManager
    symbol_table = currentProgram.symbolTable
    
    # Import functions
    func_count = 0
    if 'functions' in data:
        for func in data['functions']:
            try:
                addr = toAddr(hex(func.get('address', 0)))
                name = func.get('name', '')
                
                if addr and name:
                    existing = function_manager.getFunctionAt(addr)
                    if existing:
                        existing.setName(name, SourceType.IMPORTED)
                    else:
                        flat_api.createFunction(addr, name)
                    func_count += 1
            except:
                pass
    
    print(f"Imported {{func_count}} functions")

import_symbols()
'''
    
    with open(output_path, 'w') as f:
        f.write(script_content)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='PS2 Decompilation Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', help='ISO or ELF file')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--symbols-only', action='store_true',
                        help='Only extract symbols with CCC')
    parser.add_argument('--ghidra', action='store_true',
                        help='Launch Ghidra analysis')
    parser.add_argument('--check-tools', action='store_true',
                        help='Check available tools')
    
    args = parser.parse_args()
    
    if args.check_tools:
        tools = check_tools()
        print("Available tools:")
        for tool, available in tools.items():
            status = "OK" if available else "MISSING"
            print(f"  {tool}: {status}")
        return
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    output_dir = Path(args.output) if args.output else input_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine if input is ISO or ELF
    elf_path = input_path
    if input_path.suffix.lower() in ['.iso', '.bin']:
        print("=== Step 1: Extracting ELF from ISO ===")
        # Import and use extract_elf module
        sys.path.insert(0, str(SCRIPT_DIR))
        from extract_elf import extract_elf_from_iso
        
        success, message, extracted_path = extract_elf_from_iso(
            str(input_path), 
            str(output_dir / "elfs")
        )
        
        if not success:
            print(f"Failed to extract ELF: {message}")
            sys.exit(1)
        
        print(f"  {message}")
        elf_path = Path(extracted_path)
    
    print(f"\n=== Step 2: Extracting Symbols with CCC ===")
    symbols_dir = output_dir / "symbols"
    success, message = extract_symbols_stdump(elf_path, symbols_dir)
    if success:
        print(f"  {message}")
    else:
        print(f"  Warning: {message}")
    
    if args.symbols_only:
        print(f"\nSymbols extracted to: {symbols_dir}")
        return
    
    print(f"\n=== Step 3: Running uncc (source reconstruction) ===")
    success, message = run_uncc(elf_path, symbols_dir)
    print(f"  {message}")
    
    print(f"\n=== Step 4: Creating Ghidra import script ===")
    script_path = output_dir / "import_symbols.py"
    create_ghidra_import_script(elf_path, symbols_dir, script_path)
    print(f"  Created: {script_path}")
    
    print(f"""
================================================================================
WORKFLOW COMPLETE
================================================================================

Output directory: {output_dir}

Next steps:
1. Open Ghidra and create a new project
2. Import the ELF file: {elf_path}
3. Select processor: MIPS:LE:64:R5900 (Emotion Engine)
4. After analysis, run the import script via Window > Python
5. Load: {script_path}

Or use Ghidra's built-in STABS analyzer (enabled by default with emotionengine-reloaded)

Symbol files:
  - {symbols_dir / f'{elf_path.stem}_symbols.cpp'} (C++ declarations)
  - {symbols_dir / f'{elf_path.stem}_types.h'} (Type definitions)
  - {symbols_dir / f'{elf_path.stem}_symbols.json'} (JSON for tools)

================================================================================
""")


if __name__ == '__main__':
    main()
