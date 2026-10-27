"""
Tests for platform_utils.py - cross-platform helpers

Run with: pytest tests/test_platform_utils.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from platform_utils import (
    EXE_SUFFIX,
    GHIDRA_HEADLESS_NAME,
    IS_WINDOWS,
    default_temp_file,
    find_ghidra,
    ghidra_command,
    ghidra_search_paths,
    resolve_tool,
    tool_path,
)


class TestToolPaths:
    def test_tool_path_adds_suffix(self, tmp_path):
        path = tool_path(tmp_path, "stdump")
        assert path.name == f"stdump{EXE_SUFFIX}"

    def test_resolve_tool_prefers_platform_binary(self, tmp_path):
        preferred = tmp_path / f"stdump{EXE_SUFFIX}"
        preferred.write_text("x")
        # Also create unsuffixed if different
        if EXE_SUFFIX:
            (tmp_path / "stdump").write_text("y")
        resolved = resolve_tool(tmp_path, "stdump")
        assert resolved == preferred

    def test_resolve_tool_falls_back_to_unsuffixed(self, tmp_path):
        if not EXE_SUFFIX:
            pytest.skip("Fallback only differs when EXE_SUFFIX is set")
        unsuffixed = tmp_path / "stdump"
        unsuffixed.write_text("x")
        resolved = resolve_tool(tmp_path, "stdump")
        assert resolved == unsuffixed


class TestTempFile:
    def test_default_temp_file_uses_system_temp(self):
        path = default_temp_file("decompiled.c")
        assert path.endswith("decompiled.c")
        assert os.path.isabs(path)


class TestGhidraDiscovery:
    def test_headless_name_matches_platform(self):
        if IS_WINDOWS:
            assert GHIDRA_HEADLESS_NAME.endswith(".bat")
        else:
            assert GHIDRA_HEADLESS_NAME == "analyzeHeadless"

    def test_search_paths_nonempty(self):
        paths = ghidra_search_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0

    def test_find_ghidra_returns_string_or_none(self):
        result = find_ghidra()
        assert result is None or isinstance(result, str)

    @patch.dict(os.environ, {"GHIDRA_INSTALL_DIR": "/fake/ghidra"}, clear=False)
    def test_env_install_dir_in_search_paths(self):
        paths = ghidra_search_paths()
        expected = str(Path("/fake/ghidra") / "support" / GHIDRA_HEADLESS_NAME)
        assert expected in paths

    def test_ghidra_command_wraps_bat_on_windows(self):
        cmd = ghidra_command(r"C:\ghidra\support\analyzeHeadless.bat", "proj", "name")
        if IS_WINDOWS:
            assert cmd[:3] == ["cmd", "/c", r"C:\ghidra\support\analyzeHeadless.bat"]
            assert cmd[3:] == ["proj", "name"]
        else:
            assert cmd[0].endswith("analyzeHeadless.bat")
            assert cmd[1:] == ["proj", "name"]

    def test_ghidra_command_unix_passthrough(self):
        cmd = ghidra_command("/opt/ghidra/support/analyzeHeadless", "proj")
        assert cmd == ["/opt/ghidra/support/analyzeHeadless", "proj"]
