"""Tmux session management for Amplifier development environments.

Create and manage tmux sessions with multiple windows for development workflows.
"""

from __future__ import annotations

import os
import shlex
import tempfile
from pathlib import Path

import subprocess

from .config import WindowConfig
from .shell import command_exists, run, try_install_tool


def _run_tmux(*args: str) -> None:
    """Run tmux command with arguments directly (no shell parsing).
    
    This avoids quote mangling that happens with shell=True.
    Matches the behavior of the bash script's direct tmux invocation.
    """
    subprocess.run(["tmux", *args], check=True)

__all__ = [
    "session_exists",
    "kill_session",
    "create_session",
    "attach_session",
]


def session_exists(name: str) -> bool:
    """Check if tmux session exists.

    Args:
        name: Session name to check.

    Returns:
        True if session exists, False otherwise.
    """
    result = run(f"tmux has-session -t {shlex.quote(name)} 2>/dev/null", check=False)
    return result.returncode == 0


def kill_session(name: str, clear_resurrect: bool = False) -> None:
    """Kill tmux session.

    Args:
        name: Session name to kill.
        clear_resurrect: If True, also clear tmux-resurrect data.
    """
    if session_exists(name):
        run(f"tmux kill-session -t {shlex.quote(name)}")

    if clear_resurrect:
        resurrect_dir = Path.home() / ".tmux" / "resurrect"
        if resurrect_dir.exists():
            # Remove 'last' symlink and all .txt files
            last_file = resurrect_dir / "last"
            if last_file.exists() or last_file.is_symlink():
                last_file.unlink()

            for txt_file in resurrect_dir.glob("*.txt"):
                txt_file.unlink()


def create_session(
    name: str,
    workdir: Path,
    main_window_name: str,
    main_command: str,
    prompt: str,
    windows: list[WindowConfig],
) -> None:
    """Create tmux session with configured windows.

    Args:
        name: Session name.
        workdir: Working directory for all windows.
        main_window_name: Name of the main window.
        main_command: Command to run in main window (e.g., "amplifier run").
        prompt: Prompt text to pass to main command.
        windows: List of additional window configurations.
    """
    # Create temp directory for rcfiles
    rcfile_dir = Path(tempfile.gettempdir()) / f"amplifier-dev-rcfiles-{os.getpid()}"
    rcfile_dir.mkdir(parents=True, exist_ok=True)

    # Create rcfile for main window
    main_rcfile = _create_main_rcfile(rcfile_dir, workdir, main_command, prompt)

    # Create the session with main window
    # Match bash script exactly: NO -c flag (cd is in rcfile), pass shell-command as single arg
    # Using _run_tmux() avoids shell parsing that mangles quotes
    _run_tmux(
        "new-session", "-d",
        "-s", name,
        "-n", main_window_name,
        f"exec bash --rcfile '{main_rcfile}'"
    )

    # Create additional windows
    for window_config in windows:
        _create_window(name, window_config, workdir, rcfile_dir)

    # Select the main window so we attach to it
    _run_tmux("select-window", "-t", f"{name}:{main_window_name}")


def select_window(session: str, window: str) -> None:
    """Select a window in a tmux session.

    Args:
        session: Session name.
        window: Window name to select.
    """
    try:
        _run_tmux("select-window", "-t", f"{session}:{window}")
    except subprocess.CalledProcessError:
        pass  # Ignore if window doesn't exist


def attach_session(name: str) -> None:
    """Attach to tmux session.

    Handles both inside and outside tmux contexts:
    - If inside tmux: uses switch-client
    - If outside tmux: uses attach-session

    Args:
        name: Session name to attach to.
    """
    quoted_name = shlex.quote(name)

    if os.environ.get("TMUX"):
        # Inside tmux - switch to session
        os.execvp("tmux", ["tmux", "switch-client", "-t", name])
    else:
        # Outside tmux - attach to session
        os.execvp("tmux", ["tmux", "attach-session", "-t", name])


def _create_main_rcfile(
    rcfile_dir: Path,
    workdir: Path,
    main_command: str,
    prompt: str,
) -> Path:
    """Create rcfile for main window with command execution.

    Args:
        rcfile_dir: Directory to store rcfile.
        workdir: Working directory.
        main_command: Command to run.
        prompt: Prompt text for command.

    Returns:
        Path to created rcfile.
    """
    rcfile = rcfile_dir / "main_rcfile.sh"

    # shlex.quote() handles shell escaping - no need for extra $(printf '%s' ...) wrapper
    # which adds unnecessary subshell overhead and potential timing issues
    escaped_prompt = shlex.quote(prompt)
    rcfile_content = f"""\
source ~/.bashrc 2>/dev/null
cd {shlex.quote(str(workdir))}
# Wait for terminal capability queries to settle, then flush any pending input
# This prevents WezTerm/tmux escape sequences from appearing in the command's input
# WezTerm sends DA1, DA2, XTVERSION queries - need enough time for all responses
sleep 0.5
read -t 0.2 -n 10000 discard 2>/dev/null || true
{main_command} {escaped_prompt}
"""
    rcfile.write_text(rcfile_content)
    rcfile.chmod(0o755)
    return rcfile


def _create_shell_rcfile(rcfile_dir: Path, workdir: Path) -> Path:
    """Create rcfile for shell window.

    Args:
        rcfile_dir: Directory to store rcfile.
        workdir: Working directory.

    Returns:
        Path to created rcfile.
    """
    rcfile = rcfile_dir / "shell_rcfile.sh"
    rcfile_content = f"""\
source ~/.bashrc 2>/dev/null
cd {shlex.quote(str(workdir))}
"""
    rcfile.write_text(rcfile_content)
    rcfile.chmod(0o755)
    return rcfile


def _create_window(
    session: str,
    config: WindowConfig,
    workdir: Path,
    rcfile_dir: Path,
) -> None:
    """Create a window in the tmux session.

    Args:
        session: Session name.
        config: Window configuration.
        workdir: Working directory.
        rcfile_dir: Directory for rcfiles.
    """

    # Special handling for "shell" window - create with 2 horizontal panes
    if config.name == "shell":
        shell_rcfile = _create_shell_rcfile(rcfile_dir, workdir)

        # Match bash script: NO -c flag, pass shell-command as single arg
        _run_tmux(
            "new-window",
            "-t", session,
            "-n", config.name,
            f"exec bash --rcfile '{shell_rcfile}'"
        )
        # Split horizontally for second pane
        _run_tmux(
            "split-window", "-h",
            "-t", f"{session}:{config.name}",
            f"exec bash --rcfile '{shell_rcfile}'"
        )
        return

    # For other windows, check if the tool exists
    tool_name = _extract_tool_name(config.command)

    if tool_name and not command_exists(tool_name):
        # Try to install the tool
        if not try_install_tool(tool_name):
            # Installation failed - create window with instructions
            _create_missing_tool_window(session, config.name, tool_name, workdir)
            return

    # Tool exists or no tool needed - create window with command
    # Create rcfile for this command window (like bash script does)
    cmd_rcfile = rcfile_dir / f"{config.name}_rcfile.sh"
    cmd_rcfile_content = f"""\
source ~/.bashrc 2>/dev/null
cd {shlex.quote(str(workdir))}
{config.command}
"""
    cmd_rcfile.write_text(cmd_rcfile_content)
    cmd_rcfile.chmod(0o755)
    
    _run_tmux(
        "new-window",
        "-t", session,
        "-n", config.name,
        f"exec bash --rcfile '{cmd_rcfile}'"
    )


def _create_missing_tool_window(
    session: str,
    window_name: str,
    tool_name: str,
    workdir: Path,
) -> None:
    """Create window with instructions for missing tool.

    Args:
        session: Session name.
        window_name: Window name.
        tool_name: Name of the missing tool.
        workdir: Working directory.
    """
    # Get install instructions based on tool
    install_cmd = _get_install_instruction(tool_name)
    message = f"Tool '{tool_name}' not found. Install with: {install_cmd}"

    # Create window that displays the message then drops to shell
    _run_tmux(
        "new-window",
        "-t", session,
        "-n", window_name,
        f"bash -c 'cd {shlex.quote(str(workdir))}; echo {shlex.quote(message)}; exec bash'"
    )


def _extract_tool_name(command: str) -> str | None:
    """Extract the primary tool name from a command string.

    Args:
        command: Command string (e.g., "lazygit", "mc -b").

    Returns:
        Tool name or None if command is empty.
    """
    if not command:
        return None

    # Get first word of command
    parts = shlex.split(command)
    return parts[0] if parts else None


def _get_install_instruction(tool_name: str) -> str:
    """Get installation instruction for a tool.

    Args:
        tool_name: Name of the tool.

    Returns:
        Installation command string.
    """
    # Common tools and their install commands
    install_commands = {
        "lazygit": "brew install lazygit",
        "mc": "brew install midnight-commander",
        "htop": "brew install htop",
        "btop": "brew install btop",
        "nvim": "brew install neovim",
        "vim": "brew install vim",
        "fzf": "brew install fzf",
        "rg": "brew install ripgrep",
        "fd": "brew install fd",
        "bat": "brew install bat",
        "eza": "brew install eza",
        "delta": "brew install git-delta",
        "jq": "brew install jq",
        "yq": "brew install yq",
    }

    return install_commands.get(tool_name, f"brew install {tool_name}")
