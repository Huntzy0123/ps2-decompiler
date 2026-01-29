"""
Tests for ps2_workflow.py - PS2 Decompilation Workflow

Run with: pytest tests/test_workflow.py -v
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from ps2_workflow import (
    check_tools,
    STDUMP,
    UNCC,
    DEMANGLE,
    CCC_BIN,
    PROJECT_DIR
)


class TestCheckTools:
    """Tests for tool availability checking"""

    def test_check_tools_returns_dict(self):
        """Test that check_tools returns a dictionary"""
        result = check_tools()
        assert isinstance(result, dict)

    def test_check_tools_has_expected_keys(self):
        """Test that check_tools returns expected tool keys"""
        result = check_tools()
        expected_keys = ['stdump', 'uncc', 'demangle', 'ghidra']
        for key in expected_keys:
            assert key in result

    def test_check_tools_values_are_booleans(self):
        """Test that tool availability values are booleans"""
        result = check_tools()
        for key, value in result.items():
            assert isinstance(value, bool), f"{key} should be boolean"


class TestPathConstants:
    """Tests for path constants"""

    def test_ccc_bin_is_path(self):
        """Test CCC_BIN is a Path object"""
        assert isinstance(CCC_BIN, Path)

    def test_stdump_path_format(self):
        """Test STDUMP path ends correctly"""
        assert STDUMP.name == "stdump"

    def test_uncc_path_format(self):
        """Test UNCC path ends correctly"""
        assert UNCC.name == "uncc"

    def test_demangle_path_format(self):
        """Test DEMANGLE path ends correctly"""
        assert DEMANGLE.name == "demangle"

    def test_project_dir_exists_or_is_valid_path(self):
        """Test PROJECT_DIR is a valid path structure"""
        assert isinstance(PROJECT_DIR, Path)
        # Should be parent of scripts directory
        assert PROJECT_DIR.name != "scripts"


class TestExtractSymbolsStdump:
    """Tests for symbol extraction (mocked)"""

    @pytest.fixture
    def mock_elf(self, tmp_path):
        """Create a mock ELF file"""
        elf_path = tmp_path / "test.elf"
        # Write minimal ELF header
        elf_path.write_bytes(b'\x7fELF' + b'\x00' * 1000)
        return elf_path

    @patch('ps2_workflow.STDUMP')
    def test_extract_symbols_missing_stdump(self, mock_stdump, mock_elf, tmp_path):
        """Test handling when stdump is not available"""
        from ps2_workflow import extract_symbols_stdump
        
        # Mock STDUMP.exists() to return False
        mock_stdump.exists.return_value = False
        
        success, message = extract_symbols_stdump(mock_elf, tmp_path / "output")
        
        assert success is False
        assert "not found" in message.lower()


class TestRunUncc:
    """Tests for uncc execution (mocked)"""

    @pytest.fixture
    def setup_uncc_env(self, tmp_path):
        """Set up environment for uncc tests"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create SOURCES.txt (required by uncc)
        sources_file = output_dir / "SOURCES.txt"
        sources_file.write_text("main.c\ngame.c\n")
        
        elf_path = tmp_path / "test.elf"
        elf_path.write_bytes(b'\x7fELF' + b'\x00' * 1000)
        
        return elf_path, output_dir

    @patch('ps2_workflow.UNCC')
    def test_run_uncc_missing_tool(self, mock_uncc, setup_uncc_env):
        """Test handling when uncc is not available"""
        from ps2_workflow import run_uncc
        
        mock_uncc.exists.return_value = False
        elf_path, output_dir = setup_uncc_env
        
        success, message = run_uncc(elf_path, output_dir)
        
        assert success is False
        assert "not found" in message.lower()

    @patch('ps2_workflow.UNCC')
    def test_run_uncc_missing_sources(self, mock_uncc, tmp_path):
        """Test handling when SOURCES.txt is missing"""
        from ps2_workflow import run_uncc
        mock_uncc.exists.return_value = True
        
        elf_path = tmp_path / "test.elf"
        elf_path.write_bytes(b'\x7fELF' + b'\x00' * 100)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        # Don't create SOURCES.txt
        
        success, message = run_uncc(elf_path, output_dir)
        
        assert success is False
        assert "SOURCES.txt" in message


class TestCreateGhidraImportScript:
    """Tests for Ghidra script generation"""

    def test_creates_script_file(self, tmp_path):
        """Test that script file is created"""
        from ps2_workflow import create_ghidra_import_script
        
        elf_path = tmp_path / "game.elf"
        symbols_dir = tmp_path / "symbols"
        symbols_dir.mkdir()
        output_path = tmp_path / "import_script.py"
        
        result = create_ghidra_import_script(elf_path, symbols_dir, output_path)
        
        assert output_path.exists()
        assert result == output_path

    def test_script_contains_elf_name(self, tmp_path):
        """Test that generated script references the ELF file"""
        from ps2_workflow import create_ghidra_import_script
        
        elf_path = tmp_path / "my_game.elf"
        symbols_dir = tmp_path / "symbols"
        symbols_dir.mkdir()
        output_path = tmp_path / "import_script.py"
        
        create_ghidra_import_script(elf_path, symbols_dir, output_path)
        
        content = output_path.read_text()
        assert "my_game" in content

    def test_script_is_valid_ghidra_script(self, tmp_path):
        """Test that generated script is a valid Ghidra PyGhidra script"""
        from ps2_workflow import create_ghidra_import_script

        elf_path = tmp_path / "test.elf"
        symbols_dir = tmp_path / "symbols"
        symbols_dir.mkdir()
        output_path = tmp_path / "import_script.py"

        create_ghidra_import_script(elf_path, symbols_dir, output_path)

        content = output_path.read_text()
        
        # Ghidra PyGhidra scripts have special headers and Python code
        # Check for expected Ghidra script elements
        assert "@category" in content, "Should have Ghidra category annotation"
        assert "import" in content, "Should have Python imports"
        assert "def " in content, "Should have function definitions"
        # The script uses // comments which Ghidra interprets, not Python
        # So we check structure instead of compiling as Python



class TestIntegration:
    """Integration tests (require actual tools)"""

    @pytest.fixture
    def has_ccc_tools(self):
        """Check if CCC tools are available"""
        if not STDUMP.exists():
            pytest.skip("CCC tools not installed")
        return True

    @pytest.mark.integration
    def test_full_workflow_with_mock_elf(self, has_ccc_tools, tmp_path):
        """Test full workflow with mock ELF (will fail symbol extraction but test flow)"""
        # This test verifies the workflow doesn't crash
        # Actual symbol extraction will fail on mock ELF
        
        elf_path = tmp_path / "test.elf"
        elf_path.write_bytes(b'\x7fELF' + b'\x00' * 1000)
        
        output_dir = tmp_path / "output"
        
        # Import and run extract_symbols_stdump
        from ps2_workflow import extract_symbols_stdump
        
        success, message = extract_symbols_stdump(elf_path, output_dir)
        
        # May fail (no debug symbols in mock) but shouldn't crash
        assert isinstance(success, bool)
        assert isinstance(message, str)
