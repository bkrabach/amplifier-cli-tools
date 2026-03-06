"""Subprocess wrapper with consistent error handling and tool installation support.

This module provides utilities for executing shell commands with proper error
handling, checking command availability, and attempting automatic tool installation.

Example:
    >>> from amplifier_cli_tools.shell import run, command_exists, ensure_commands
    >>> result = run("echo hello")
    >>> result.stdout
    'hello\\n'
    >>> command_exists("git")
    True
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


class ShellError(Exception):
    """Raised when shell command fails.

    Attributes:
        returncode: The exit code of the failed command, if available.
    """

    def __init__(self, message: str, returncode: int | None = None):
        self.returncode = returncode
        super().__init__(message)


def run(
    cmd: str | list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    """Run shell command.

    Args:
        cmd: Command to run. String commands use shell=True, list commands use shell=False.
        cwd: Working directory for the command.
        check: If True, raise ShellError on non-zero exit code.
        capture: If True, capture stdout and stderr.
        quiet: If True, suppress stderr output on failure.

    Returns:
        CompletedProcess with stdout/stderr as strings if captured.

    Raises:
        ShellError: If check=True and command returns non-zero exit code.

    Example:
        >>> result = run("ls -la", cwd=Path("/tmp"))
        >>> result = run(["git", "status"], check=False)
    """
    use_shell = isinstance(cmd, str)

    try:
        result = subprocess.run(
            cmd,
            shell=use_shell,
            cwd=cwd,
            capture_output=capture,
            text=True if capture else None,
        )
    except FileNotFoundError as e:
        # Command not found (for list-style commands)
        cmd_name = cmd[0] if isinstance(cmd, list) else cmd.split()[0]
        raise ShellError(f"Command not found: {cmd_name}", returncode=127) from e
    except Exception as e:
        raise ShellError(f"Failed to execute command: {e}") from e

    if check and result.returncode != 0:
        # Build error message
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
        error_msg = f"Command failed with exit code {result.returncode}: {cmd_str}"

        # Print stderr for debugging unless quiet
        if not quiet and capture and result.stderr:
            print(result.stderr, file=sys.stderr)

        raise ShellError(error_msg, returncode=result.returncode)

    return result


def command_exists(name: str) -> bool:
    """Check if command is available in PATH.

    Args:
        name: Name of the command to check.

    Returns:
        True if command exists in PATH, False otherwise.

    Example:
        >>> command_exists("git")
        True
        >>> command_exists("nonexistent-cmd-12345")
        False
    """
    return shutil.which(name) is not None


def ensure_commands(*names: str) -> None:
    """Validate that required commands exist.

    Args:
        *names: Command names to check.

    Raises:
        ShellError: If any command is missing from PATH.

    Example:
        >>> ensure_commands("git", "python")  # OK if both exist
        >>> ensure_commands("nonexistent")  # Raises ShellError
    """
    missing = [name for name in names if not command_exists(name)]
    if missing:
        missing_str = ", ".join(missing)
        raise ShellError(f"Required commands not found: {missing_str}")


# Package manager mappings for different platforms
_TOOL_PACKAGES: dict[str, dict[str, str]] = {
    # tool_name: {package_manager: package_name}
    "lazygit": {
        "brew": "lazygit",
        "winget": "JesseDuffield.lazygit",
        # Linux uses GitHub releases - see _install_lazygit_linux()
    },
    "mc": {
        "brew": "mc",
        "apt": "mc",
        "dnf": "mc",
    },
    "tmux": {
        "brew": "tmux",
        "apt": "tmux",
        "dnf": "tmux",
    },
    "git": {
        "brew": "git",
        "apt": "git",
        "dnf": "git",
        "winget": "Git.Git",
    },
    "mosh": {
        "brew": "mosh",
        "apt": "mosh",
        "dnf": "mosh",
    },
    "xclip": {
        "apt": "xclip",
        "dnf": "xclip",
    },
    "xsel": {
        "apt": "xsel",
        "dnf": "xsel",
    },
}


def _get_arch() -> str:
    """Get system architecture for downloads."""
    import platform as plat
    machine = plat.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    return machine


def _install_lazygit_linux() -> bool:
    """Install lazygit on Linux via GitHub releases.
    
    Returns:
        True if installation successful, False otherwise.
    """
    import json
    import urllib.request
    import tarfile
    import tempfile
    
    print("Installing lazygit from GitHub releases...")
    
    try:
        # Get latest version
        url = "https://api.github.com/repos/jesseduffield/lazygit/releases/latest"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            version = data["tag_name"].lstrip("v")
        
        arch = _get_arch()
        if arch not in ("x86_64", "arm64"):
            print(f"Unsupported architecture: {arch}")
            return False
        
        # Download tarball
        tarball_url = (
            f"https://github.com/jesseduffield/lazygit/releases/download/"
            f"v{version}/lazygit_{version}_Linux_{arch}.tar.gz"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / "lazygit.tar.gz"
            print(f"Downloading lazygit v{version}...")
            urllib.request.urlretrieve(tarball_url, tarball_path)
            
            # Extract
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extract("lazygit", tmpdir)
            
            lazygit_bin = Path(tmpdir) / "lazygit"
            
            # Install to /usr/local/bin (needs sudo) or ~/.local/bin
            local_bin = Path.home() / ".local" / "bin"
            if _has_sudo():
                result = run(
                    ["sudo", "install", str(lazygit_bin), "-D", "-t", "/usr/local/bin/"],
                    check=False,
                    capture=False,
                )
                if result.returncode == 0:
                    print("Successfully installed lazygit to /usr/local/bin")
                    return True
            
            # Fallback to ~/.local/bin
            local_bin.mkdir(parents=True, exist_ok=True)
            dest = local_bin / "lazygit"
            shutil.copy2(lazygit_bin, dest)
            dest.chmod(0o755)
            print(f"Successfully installed lazygit to {dest}")
            print(f"Make sure {local_bin} is in your PATH")
            return True
            
    except Exception as e:
        print(f"Failed to install lazygit: {e}")
        return False


def _detect_package_manager() -> str | None:
    """Detect available package manager.

    Returns:
        Package manager name ('brew', 'apt', 'dnf') or None if not found.
    """
    system = platform.system()

    if system == "Darwin":
        if command_exists("brew"):
            return "brew"
    elif system == "Linux":
        if command_exists("apt"):
            return "apt"
        if command_exists("dnf"):
            return "dnf"
    elif system == "Windows":
        if command_exists("winget"):
            return "winget"

    return None


def _has_sudo() -> bool:
    """Check if sudo is available."""
    return command_exists("sudo")


def try_install_tool(name: str) -> bool:
    """Try to install a tool via package manager.

    Attempts to detect the platform and available package manager,
    then installs the tool if a mapping exists.

    Args:
        name: Name of the tool to install.

    Returns:
        True if installation was successful, False otherwise.

    Note:
        On Linux, uses sudo if available. User may be prompted for password.
        Returns False if package manager not found or tool has no mapping.

    Example:
        >>> try_install_tool("tmux")  # Returns True if installed successfully
    """
    pkg_manager = _detect_package_manager()
    if pkg_manager is None:
        print(f"No supported package manager found. Please install '{name}' manually.")
        return False

    # Special case: lazygit on Linux uses GitHub releases
    if name == "lazygit" and platform.system() == "Linux":
        return _install_lazygit_linux()

    # Get package name for this tool and package manager
    tool_mapping = _TOOL_PACKAGES.get(name, {})
    package_name = tool_mapping.get(pkg_manager)

    # If no mapping, try using the tool name directly as package name
    if package_name is None:
        # Only do this for known package managers where tool name usually matches
        if pkg_manager in ("brew", "apt", "dnf"):
            package_name = name
        else:
            print(
                f"No package mapping for '{name}' on {pkg_manager}. "
                f"Please install manually."
            )
            return False

    # Build install command
    if pkg_manager == "winget":
        install_cmd = [
            "winget", "install", "--id", package_name,
            "--silent", "--accept-source-agreements", "--accept-package-agreements",
        ]
    elif pkg_manager == "brew":
        install_cmd = ["brew", "install", package_name]
    elif pkg_manager == "apt":
        if _has_sudo():
            install_cmd = ["sudo", "apt", "install", "-y", package_name]
        else:
            print(
                f"sudo not available. Run: apt install {package_name}"
            )
            return False
    elif pkg_manager == "dnf":
        if _has_sudo():
            install_cmd = ["sudo", "dnf", "install", "-y", package_name]
        else:
            print(
                f"sudo not available. Run: dnf install {package_name}"
            )
            return False
    else:
        return False

    # Attempt installation
    print(f"Installing {name} via {pkg_manager}...")
    try:
        result = run(install_cmd, check=False, capture=False)
        if result.returncode == 0:
            print(f"Successfully installed {name}")
            return True
        else:
            print(f"Failed to install {name} (exit code {result.returncode})")
            return False
    except ShellError as e:
        print(f"Failed to install {name}: {e}")
        return False


__all__ = [
    "ShellError",
    "run",
    "command_exists",
    "ensure_commands",
    "try_install_tool",
]
