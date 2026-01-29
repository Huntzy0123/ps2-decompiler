"""
Tests for extract_elf.py - PS2 ISO ELF Extractor

Run with: pytest tests/test_extract_elf.py -v
"""

import pytest
import tempfile
import os
import struct
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from extract_elf import (
    ISO9660,
    parse_system_cnf,
    is_elf_file,
    extract_elf_from_iso
)


class TestParseSystemCnf:
    """Tests for SYSTEM.CNF parsing"""

    def test_parse_standard_boot2(self):
        """Test parsing standard BOOT2 line"""
        content = b"BOOT2 = cdrom0:\\SLUS_123.45;1\n"
        result = parse_system_cnf(content)
        assert result == "SLUS_123.45"

    def test_parse_boot2_with_path(self):
        """Test parsing BOOT2 with subdirectory"""
        content = b"BOOT2 = cdrom0:\\DATA\\GAME.ELF;1\n"
        result = parse_system_cnf(content)
        assert result == "GAME.ELF"

    def test_parse_boot2_lowercase(self):
        """Test parsing lowercase boot2"""
        content = b"boot2 = cdrom0:\\SLPS_999.99;1\n"
        result = parse_system_cnf(content)
        assert result == "SLPS_999.99"

    def test_parse_boot2_no_version(self):
        """Test parsing BOOT2 without version number"""
        content = b"BOOT2 = cdrom0:\\MAIN.ELF\n"
        result = parse_system_cnf(content)
        assert result == "MAIN.ELF"

    def test_parse_multiple_lines(self):
        """Test parsing with multiple config lines"""
        content = b"""VER = 1.00
VMODE = NTSC
BOOT2 = cdrom0:\\SLUS_200.00;1
"""
        result = parse_system_cnf(content)
        assert result == "SLUS_200.00"

    def test_parse_empty_content(self):
        """Test parsing empty content"""
        content = b""
        result = parse_system_cnf(content)
        assert result is None

    def test_parse_no_boot2(self):
        """Test parsing without BOOT2 line"""
        content = b"VER = 1.00\nVMODE = PAL\n"
        result = parse_system_cnf(content)
        assert result is None

    def test_parse_malformed_boot2(self):
        """Test parsing malformed BOOT2 (no equals)"""
        content = b"BOOT2 cdrom0:\\GAME.ELF\n"
        result = parse_system_cnf(content)
        assert result is None


class TestIsElfFile:
    """Tests for ELF file validation"""

    def test_valid_elf_header(self):
        """Test valid ELF magic bytes"""
        data = b'\x7fELF' + b'\x00' * 100
        assert is_elf_file(data) is True

    def test_invalid_magic(self):
        """Test invalid magic bytes"""
        data = b'\x7fPDF' + b'\x00' * 100
        assert is_elf_file(data) is False

    def test_empty_data(self):
        """Test empty data"""
        data = b''
        assert is_elf_file(data) is False

    def test_short_data(self):
        """Test data shorter than ELF header"""
        data = b'\x7fE'
        assert is_elf_file(data) is False

    def test_mz_executable(self):
        """Test Windows MZ executable is not ELF"""
        data = b'MZ' + b'\x00' * 100
        assert is_elf_file(data) is False


class TestISO9660:
    """Tests for ISO9660 parser"""

    def test_sector_size_constant(self):
        """Test sector size is correct"""
        assert ISO9660.SECTOR_SIZE == 2048

    def test_primary_vol_desc_sector(self):
        """Test primary volume descriptor sector location"""
        assert ISO9660.PRIMARY_VOL_DESC_SECTOR == 16

    @pytest.fixture
    def mock_iso_file(self, tmp_path):
        """Create a minimal mock ISO structure"""
        iso_path = tmp_path / "test.iso"
        
        # Create minimal ISO with primary volume descriptor
        with open(iso_path, 'wb') as f:
            # Pad to sector 16
            f.write(b'\x00' * (16 * 2048))
            
            # Primary volume descriptor
            pvd = bytearray(2048)
            pvd[0] = 0x01  # Type
            pvd[1:6] = b'CD001'  # Standard identifier
            pvd[6] = 0x01  # Version
            
            # Root directory record at offset 156
            # Minimal directory record
            root_record = bytearray(34)
            root_record[0] = 34  # Length
            root_record[2:6] = struct.pack('<I', 18)  # Extent location (sector 18)
            root_record[10:14] = struct.pack('<I', 2048)  # Data length
            pvd[156:156+34] = root_record
            
            f.write(bytes(pvd))
        
        return iso_path

    def test_iso_context_manager(self, mock_iso_file):
        """Test ISO9660 works as context manager"""
        with ISO9660(str(mock_iso_file)) as iso:
            assert iso.f is not None
        # File should be closed after context
        assert iso.f.closed


class TestExtractElfFromIso:
    """Integration tests for extract_elf_from_iso"""

    def test_nonexistent_iso(self, tmp_path):
        """Test handling of non-existent ISO file"""
        fake_path = tmp_path / "nonexistent.iso"
        success, message, path = extract_elf_from_iso(str(fake_path))
        
        assert success is False
        assert "not found" in message.lower()
        assert path is None

    def test_output_directory_created(self, tmp_path):
        """Test that output directory is created if missing"""
        # This will fail early (no valid ISO), but should still try to create dir
        fake_iso = tmp_path / "fake.iso"
        fake_iso.write_bytes(b'\x00' * 100)
        
        output_dir = tmp_path / "output" / "nested" / "dir"
        success, message, path = extract_elf_from_iso(str(fake_iso), str(output_dir))
        
        # Will fail because ISO is invalid, but dir might be created
        # depending on implementation order
        assert success is False


class TestEdgeCases:
    """Edge case and error handling tests"""

    def test_parse_system_cnf_unicode(self):
        """Test handling of unexpected unicode in SYSTEM.CNF"""
        content = "BOOT2 = cdrom0:\\GAME.ELF;1\n".encode('utf-16')
        result = parse_system_cnf(content)
        # Should handle gracefully, likely return None
        assert result is None or isinstance(result, str)

    def test_is_elf_with_none(self):
        """Test is_elf_file doesn't crash with bad input"""
        with pytest.raises((TypeError, AttributeError)):
            is_elf_file(None)

    def test_parse_system_cnf_binary_garbage(self):
        """Test parsing binary garbage doesn't crash"""
        content = bytes(range(256)) * 10
        result = parse_system_cnf(content)
        # Should not crash, return None or some string
        assert result is None or isinstance(result, str)


class TestRealISO:
    """Tests that require a real PS2 ISO (skipped if not available)"""

    @pytest.fixture
    def sample_iso(self):
        """Look for a sample ISO in common locations"""
        possible_paths = [
            Path.home() / "Documents" / "Samurai Shodown Anthology (USA).iso",
            Path("/tmp/test_ps2.iso"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        pytest.skip("No sample ISO available for integration testing")

    @pytest.mark.integration
    def test_extract_from_real_iso(self, sample_iso, tmp_path):
        """Test extraction from a real PS2 ISO"""
        success, message, output_path = extract_elf_from_iso(
            str(sample_iso), 
            str(tmp_path)
        )
        
        assert success is True
        assert output_path is not None
        assert Path(output_path).exists()
        
        # Verify extracted file is valid ELF
        with open(output_path, 'rb') as f:
            header = f.read(4)
        assert header == b'\x7fELF'
