#!/usr/bin/env python3
"""
PS2 ISO ELF Extractor
Extracts ELF executables from PS2 ISO images by parsing SYSTEM.CNF

Usage:
    python3 extract_elf.py <iso_file> [output_directory]
    python3 extract_elf.py --batch <iso_directory> [output_directory]
"""

import os
import sys
import struct
import argparse
from pathlib import Path
from typing import Optional, Tuple, List


class ISO9660:
    """Simple ISO 9660 parser for PS2 disc images"""
    
    SECTOR_SIZE = 2048
    PRIMARY_VOL_DESC_SECTOR = 16
    
    def __init__(self, iso_path: str):
        self.iso_path = iso_path
        self.f = None
        self.root_dir_record = None
        self.path_table_loc = 0
        
    def __enter__(self):
        self.f = open(self.iso_path, 'rb')
        self._read_primary_volume_descriptor()
        return self
    
    def __exit__(self, *args):
        if self.f:
            self.f.close()
    
    def _read_sector(self, sector: int) -> bytes:
        self.f.seek(sector * self.SECTOR_SIZE)
        return self.f.read(self.SECTOR_SIZE)
    
    def _read_primary_volume_descriptor(self):
        """Read and parse the primary volume descriptor"""
        data = self._read_sector(self.PRIMARY_VOL_DESC_SECTOR)
        
        if data[0:1] != b'\x01' or data[1:6] != b'CD001':
            raise ValueError("Invalid ISO 9660 primary volume descriptor")
        
        self.root_dir_record = data[156:156+34]
        self.path_table_loc = struct.unpack('<I', data[140:144])[0]
    
    def _parse_directory_record(self, data: bytes, offset: int) -> Optional[dict]:
        """Parse a single directory record"""
        if offset >= len(data):
            return None
            
        record_len = data[offset]
        if record_len == 0:
            return None
        
        if offset + record_len > len(data):
            return None
            
        extent_loc = struct.unpack('<I', data[offset+2:offset+6])[0]
        data_len = struct.unpack('<I', data[offset+10:offset+14])[0]
        flags = data[offset+25]
        name_len = data[offset+32]
        
        if offset + 33 + name_len > len(data):
            return None
            
        name = data[offset+33:offset+33+name_len]
        
        if name == b'\x00':
            name = b'.'
        elif name == b'\x01':
            name = b'..'
        else:
            try:
                name = name.decode('ascii').split(';')[0]
            except:
                name = name.decode('latin-1').split(';')[0]
        
        return {
            'length': record_len,
            'extent': extent_loc,
            'size': data_len,
            'flags': flags,
            'name': name if isinstance(name, str) else name.decode('ascii', errors='replace'),
            'is_dir': bool(flags & 0x02)
        }
    
    def _list_directory(self, extent: int, size: int) -> List[dict]:
        """List all entries in a directory"""
        entries = []
        sectors_to_read = (size + self.SECTOR_SIZE - 1) // self.SECTOR_SIZE
        
        data = b''
        for i in range(sectors_to_read):
            data += self._read_sector(extent + i)
        
        data = data[:size]
        offset = 0
        
        while offset < len(data):
            record = self._parse_directory_record(data, offset)
            if record is None:
                next_sector = ((offset // self.SECTOR_SIZE) + 1) * self.SECTOR_SIZE
                if next_sector <= len(data):
                    offset = next_sector
                    continue
                break
            
            if record['name'] not in ['.', '..']:
                entries.append(record)
            
            offset += record['length']
        
        return entries
    
    def list_root(self) -> List[dict]:
        """List root directory contents"""
        extent = struct.unpack('<I', self.root_dir_record[2:6])[0]
        size = struct.unpack('<I', self.root_dir_record[10:14])[0]
        return self._list_directory(extent, size)
    
    def find_file(self, filename: str) -> Optional[dict]:
        """Find a file in root directory (case-insensitive)"""
        filename_upper = filename.upper()
        for entry in self.list_root():
            if entry['name'].upper() == filename_upper:
                return entry
        return None
    
    def read_file(self, entry: dict) -> bytes:
        """Read file contents from ISO"""
        sectors_to_read = (entry['size'] + self.SECTOR_SIZE - 1) // self.SECTOR_SIZE
        data = b''
        for i in range(sectors_to_read):
            data += self._read_sector(entry['extent'] + i)
        return data[:entry['size']]


def parse_system_cnf(content: bytes) -> Optional[str]:
    """Parse SYSTEM.CNF to find the main executable"""
    try:
        text = content.decode('ascii', errors='ignore')
    except:
        return None
    
    for line in text.split('\n'):
        line = line.strip()
        if line.upper().startswith('BOOT2'):
            parts = line.split('=', 1)
            if len(parts) < 2:
                continue
            
            boot_path = parts[1].strip()
            if boot_path.upper().startswith('CDROM0:'):
                boot_path = boot_path[7:]
            if boot_path.startswith('\\') or boot_path.startswith('/'):
                boot_path = boot_path[1:]
            if ';' in boot_path:
                boot_path = boot_path.split(';')[0]
            
            boot_path = boot_path.replace('\\', '/')
            return boot_path.split('/')[-1]
    
    return None


def is_elf_file(data: bytes) -> bool:
    """Check if data is a valid ELF file"""
    if len(data) < 4:
        return False
    return data[:4] == b'\x7fELF'


def extract_elf_from_iso(iso_path: str, output_dir: str = None) -> Tuple[bool, str, Optional[str]]:
    """Extract ELF from PS2 ISO"""
    iso_path = Path(iso_path)
    
    if not iso_path.exists():
        return False, f"ISO file not found: {iso_path}", None
    
    if output_dir is None:
        output_dir = iso_path.parent / "elfs"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with ISO9660(str(iso_path)) as iso:
            system_cnf = iso.find_file('SYSTEM.CNF')
            if not system_cnf:
                return False, "SYSTEM.CNF not found in ISO", None
            
            cnf_content = iso.read_file(system_cnf)
            elf_name = parse_system_cnf(cnf_content)
            
            if not elf_name:
                return False, "Could not parse BOOT2 from SYSTEM.CNF", None
            
            print(f"  Found executable: {elf_name}")
            
            elf_entry = iso.find_file(elf_name)
            if not elf_entry:
                for entry in iso.list_root():
                    if entry['name'].upper().startswith(elf_name.upper().split('.')[0]):
                        elf_entry = entry
                        elf_name = entry['name']
                        break
            
            if not elf_entry:
                return False, f"ELF file not found: {elf_name}", None
            
            elf_data = iso.read_file(elf_entry)
            
            if not is_elf_file(elf_data):
                return False, f"File {elf_name} is not a valid ELF", None
            
            base_name = iso_path.stem
            output_path = output_dir / f"{base_name}.elf"
            
            with open(output_path, 'wb') as f:
                f.write(elf_data)
            
            return True, f"Extracted {elf_name} ({len(elf_data):,} bytes)", str(output_path)
            
    except Exception as e:
        return False, f"Error processing ISO: {str(e)}", None


def batch_extract(iso_dir: str, output_dir: str = None) -> dict:
    """Process multiple ISOs in a directory"""
    iso_dir = Path(iso_dir)
    results = {'success': [], 'failed': []}
    
    iso_files = list(iso_dir.glob('*.iso')) + list(iso_dir.glob('*.ISO'))
    iso_files += list(iso_dir.glob('*.bin')) + list(iso_dir.glob('*.BIN'))
    
    if not iso_files:
        print(f"No ISO files found in {iso_dir}")
        return results
    
    print(f"Found {len(iso_files)} ISO files")
    
    for iso_file in iso_files:
        print(f"\nProcessing: {iso_file.name}")
        success, message, output_path = extract_elf_from_iso(str(iso_file), output_dir)
        
        if success:
            results['success'].append((iso_file.name, output_path))
            print(f"  SUCCESS: {message}")
        else:
            results['failed'].append((iso_file.name, message))
            print(f"  FAILED: {message}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Extract ELF executables from PS2 ISO images'
    )
    
    parser.add_argument('input', help='ISO file or directory (with --batch)')
    parser.add_argument('output', nargs='?', help='Output directory')
    parser.add_argument('--batch', action='store_true', help='Process all ISOs in directory')
    parser.add_argument('--list', action='store_true', help='List ISO contents')
    
    args = parser.parse_args()
    
    if args.list:
        with ISO9660(args.input) as iso:
            print(f"\nContents of {args.input}:")
            print("-" * 60)
            for entry in iso.list_root():
                type_str = "[DIR]" if entry['is_dir'] else "     "
                print(f"{type_str} {entry['name']:40} {entry['size']:>12,} bytes")
        return
    
    if args.batch:
        results = batch_extract(args.input, args.output)
        print(f"\nSUMMARY: {len(results['success'])} succeeded, {len(results['failed'])} failed")
    else:
        success, message, output_path = extract_elf_from_iso(args.input, args.output)
        if success:
            print(f"SUCCESS: {message}")
            print(f"Output: {output_path}")
        else:
            print(f"FAILED: {message}")
            sys.exit(1)


if __name__ == '__main__':
    main()
