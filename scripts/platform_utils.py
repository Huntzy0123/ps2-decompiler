#!/usr/bin/env python3
"""
Cross-platform path and tool helpers for the PS2 Decompiler Toolkit.
"""

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


IS_WINDOWS = platform.system() == "Windows"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""
GHIDRA_HEADLESS_NAME = "analyzeHeadless.bat" if IS_WINDOWS else "analyzeHeadless"


def tool_path(directory: Path, name: str) -> Path:
    """Return path to a native tool binary (adds .exe on Windows)."""
    return directory / f"{name}{EXE_SUFFIX}"


def resolve_tool(directory: Path, name: str) -> Path:
    """
    Resolve a CCC-style tool path, preferring the platform suffix but
    also accepting the unsuffixed name (e.g. WSL / Git Bash builds).

    Also checks Visual Studio multi-config output dirs (Release/Debug).
    """
    candidates = [
        tool_path(directory, name),
        directory / name,
        tool_path(directory / "Release", name),
        tool_path(directory / "Debug", name),
        directory / "Release" / name,
        directory / "Debug" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def default_temp_file(name: str = "decompiled.c") -> str:
    """Return a platform-appropriate temporary file path."""
    return str(Path(tempfile.gettempdir()) / name)


def ghidra_search_paths() -> List[str]:
    """Candidate locations for Ghidra's analyzeHeadless launcher."""
    home = Path.home()
    paths: List[str] = []

    # Environment overrides (official Ghidra install var + common aliases)
    for env_var in ("GHIDRA_INSTALL_DIR", "GHIDRA_HOME", "GHIDRA_PATH"):
        value = os.environ.get(env_var)
        if value:
            install = Path(value)
            paths.append(str(install / "support" / GHIDRA_HEADLESS_NAME))
            # Allow pointing directly at analyzeHeadless[.bat]
            if install.name.lower().startswith("analyzeheadless"):
                paths.append(str(install))

    if IS_WINDOWS:
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))

        for base in (program_files, program_files_x86, str(home), local_app_data, r"C:\\"):
            base_path = Path(base)
            if not base_path.exists():
                continue
            # Exact known folders
            for folder in ("Ghidra", "ghidra"):
                paths.append(str(base_path / folder / "support" / GHIDRA_HEADLESS_NAME))
            # Versioned installs: ghidra_11.4_PUBLIC, etc.
            try:
                for child in base_path.iterdir():
                    if child.is_dir() and child.name.lower().startswith("ghidra"):
                        paths.append(str(child / "support" / GHIDRA_HEADLESS_NAME))
            except OSError:
                pass
    else:
        paths.extend([
            f"/Applications/Ghidra/support/{GHIDRA_HEADLESS_NAME}",
            str(home / "ghidra" / "support" / GHIDRA_HEADLESS_NAME),
            f"/opt/ghidra/support/{GHIDRA_HEADLESS_NAME}",
            f"/usr/local/ghidra/support/{GHIDRA_HEADLESS_NAME}",
            str(home / "Applications" / "Ghidra" / "support" / GHIDRA_HEADLESS_NAME),
        ])
        # Versioned installs under /opt and home
        for base in (Path("/opt"), home, Path("/usr/local")):
            if not base.exists():
                continue
            try:
                for child in base.iterdir():
                    if child.is_dir() and child.name.lower().startswith("ghidra"):
                        paths.append(str(child / "support" / GHIDRA_HEADLESS_NAME))
            except OSError:
                pass

    return paths


def find_ghidra() -> Optional[str]:
    """Locate Ghidra's analyzeHeadless launcher on this platform."""
    for path in ghidra_search_paths():
        if path and os.path.exists(path):
            return path

    # PATH lookup (works on Windows and Unix)
    which_result = shutil.which(GHIDRA_HEADLESS_NAME)
    if which_result:
        return which_result

    # Also try the Unix name even on Windows (e.g. WSL-style installs on PATH)
    if IS_WINDOWS:
        alt = shutil.which("analyzeHeadless")
        if alt:
            return alt

    return None


def ghidra_command(ghidra_path: str, *args: str) -> List[str]:
    """
    Build a subprocess command that can invoke analyzeHeadless on any OS.
    Windows .bat files must be launched via cmd /c.
    """
    path = str(ghidra_path)
    cmd_args = [str(a) for a in args]
    if IS_WINDOWS and path.lower().endswith((".bat", ".cmd")):
        return ["cmd", "/c", path, *cmd_args]
    return [path, *cmd_args]


def run_command(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command with Windows-friendly defaults."""
    # Avoid text mode newline issues; callers can still override
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    return subprocess.run(cmd, **kwargs)
