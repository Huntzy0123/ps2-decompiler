"""
Tests for ghidra_analyze.py - Ghidra Headless Analysis

Run with: pytest tests/test_ghidra_analyze.py -v
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from ghidra_analyze import (
    find_ghidra,
    GHIDRA_PATH,
    PROJECT_NAME
)
from platform_utils import GHIDRA_HEADLESS_NAME


class TestFindGhidra:
    """Tests for Ghidra discovery"""

    def test_find_ghidra_returns_string_or_none(self):
        """Test that find_ghidra returns string path or None"""
        result = find_ghidra()
        assert result is None or isinstance(result, str)

    def test_default_ghidra_path_mentions_headless(self):
        """Test default path references analyzeHeadless"""
        assert "analyzeHeadless" in GHIDRA_PATH or "ghidra" in GHIDRA_PATH.lower()

    @patch('platform_utils.os.path.exists')
    def test_find_ghidra_checks_search_paths(self, mock_exists):
        """Test that a discovered path is returned when it exists"""
        mock_exists.return_value = True

        result = find_ghidra()

        assert result is not None
        assert GHIDRA_HEADLESS_NAME in result or "analyzeHeadless" in result

    @patch('platform_utils.os.path.exists', return_value=False)
    @patch('platform_utils.shutil.which')
    def test_find_ghidra_falls_back_to_path(self, mock_which, mock_exists):
        """Test fallback to PATH via shutil.which"""
        mock_which.return_value = f'/usr/local/bin/{GHIDRA_HEADLESS_NAME}'

        result = find_ghidra()

        assert result == f'/usr/local/bin/{GHIDRA_HEADLESS_NAME}'
        mock_which.assert_called()


class TestConstants:
    """Tests for module constants"""

    def test_project_name_is_string(self):
        """Test PROJECT_NAME is a string"""
        assert isinstance(PROJECT_NAME, str)
        assert len(PROJECT_NAME) > 0

    def test_ghidra_path_is_string(self):
        """Test GHIDRA_PATH is a string"""
        assert isinstance(GHIDRA_PATH, str)


class TestAnalyzeElf:
    """Tests for analyze_elf function (mocked)"""

    @pytest.fixture
    def mock_elf(self, tmp_path):
        """Create a mock ELF file"""
        elf_path = tmp_path / "test.elf"
        elf_path.write_bytes(b'\x7fELF' + b'\x00' * 1000)
        return elf_path

    def test_analyze_elf_nonexistent_file(self, tmp_path):
        """Test handling of non-existent ELF file"""
        from ghidra_analyze import analyze_elf

        fake_path = tmp_path / "nonexistent.elf"
        success, message = analyze_elf(str(fake_path))

        assert success is False
        assert "not found" in message.lower()

    @patch('ghidra_analyze.find_ghidra')
    def test_analyze_elf_no_ghidra(self, mock_find, mock_elf):
        """Test handling when Ghidra is not found"""
        from ghidra_analyze import analyze_elf

        mock_find.return_value = None

        success, message = analyze_elf(str(mock_elf))

        assert success is False
        assert "ghidra" in message.lower()

    @patch('ghidra_analyze.find_ghidra')
    @patch('subprocess.run')
    def test_analyze_elf_creates_output_dir(self, mock_run, mock_find, mock_elf, tmp_path):
        """Test that output directory is created"""
        from ghidra_analyze import analyze_elf

        mock_find.return_value = "/usr/bin/analyzeHeadless"
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        output_dir = tmp_path / "new_output"

        analyze_elf(str(mock_elf), str(output_dir), ghidra_path="/usr/bin/analyzeHeadless")

        assert output_dir.exists()

    @patch('ghidra_analyze.find_ghidra')
    @patch('subprocess.run')
    def test_analyze_elf_timeout_handled(self, mock_run, mock_find, mock_elf):
        """Test that subprocess timeout is handled"""
        from ghidra_analyze import analyze_elf
        import subprocess

        mock_find.return_value = "/usr/bin/analyzeHeadless"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=300)

        success, message = analyze_elf(str(mock_elf), ghidra_path="/usr/bin/analyzeHeadless")

        assert success is False
        assert "timed out" in message.lower() or "timeout" in message.lower()

    @patch('ghidra_analyze.find_ghidra')
    @patch('subprocess.run')
    def test_analyze_elf_uses_ghidra_command_wrapper(self, mock_run, mock_find, mock_elf, tmp_path):
        """Ensure analyze_elf builds a platform-aware command list"""
        from ghidra_analyze import analyze_elf
        from platform_utils import ghidra_command

        mock_find.return_value = "/usr/bin/analyzeHeadless"
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        analyze_elf(str(mock_elf), str(tmp_path / "out"), ghidra_path="/usr/bin/analyzeHeadless")

        first_cmd = mock_run.call_args_list[0][0][0]
        expected_prefix = ghidra_command("/usr/bin/analyzeHeadless")
        assert first_cmd[:len(expected_prefix)] == expected_prefix


class TestCreateGhidraScripts:
    """Tests for Ghidra script generation"""

    def test_create_ghidra_scripts_creates_directory(self, tmp_path):
        """Test that scripts directory is created"""
        from ghidra_analyze import create_ghidra_scripts

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        create_ghidra_scripts(output_dir)

        scripts_dir = output_dir / "ghidra_scripts"
        assert scripts_dir.exists()

    def test_create_ghidra_scripts_creates_export_script(self, tmp_path):
        """Test that ExportCCode.java is created"""
        from ghidra_analyze import create_ghidra_scripts

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        create_ghidra_scripts(output_dir)

        export_script = output_dir / "ghidra_scripts" / "ExportCCode.java"
        assert export_script.exists()

    def test_export_script_is_valid_java(self, tmp_path):
        """Test that generated Java script has expected structure"""
        from ghidra_analyze import create_ghidra_scripts

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        create_ghidra_scripts(output_dir)

        export_script = output_dir / "ghidra_scripts" / "ExportCCode.java"
        content = export_script.read_text(encoding='utf-8')

        # Check for expected Java elements
        assert "public class ExportCCode" in content
        assert "extends GhidraScript" in content
        assert "public void run()" in content
        # Portable temp dir (Windows + Unix), not a hardcoded /tmp path
        assert "java.io.tmpdir" in content
        assert '"/tmp/decompiled.c"' not in content


class TestIntegration:
    """Integration tests (require Ghidra installed)"""

    @pytest.fixture
    def has_ghidra(self):
        """Check if Ghidra is available"""
        result = find_ghidra()
        if result is None:
            pytest.skip("Ghidra not installed")
        return result

    @pytest.mark.integration
    @pytest.mark.slow
    def test_ghidra_help_runs(self, has_ghidra):
        """Test that Ghidra headless can show help"""
        import subprocess
        from platform_utils import ghidra_command

        result = subprocess.run(
            ghidra_command(has_ghidra, "--help"),
            capture_output=True,
            text=True,
            timeout=30
        )

        # Ghidra help should run without error
        # (returncode may vary but shouldn't crash)
        assert result.returncode is not None
