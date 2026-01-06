"""Tmux session management for Amplifier development environments.

Create and manage tmux sessions with multiple windows for development workflows.
"""

from __future__ import annotations

import os
import shlex
import tempfile
from pathlib import Path

from .config import WindowConfig
from .shell import command_exists, run, try_install_tool

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
    quoted_name = shlex.quote(name)
    quoted_workdir = shlex.quote(str(workdir))
    quoted_main_window = shlex.quote(main_window_name)
    quoted_rcfile = shlex.quote(str(main_rcfile))

    # Use 'exec bash' to replace the shell process, preventing extra shell layers
    # that could receive terminal capability query responses before our flush logic runs
    run(
        f"tmux new-session -d -s {quoted_name} -n {quoted_main_window} "
        f"-c {quoted_workdir} 'exec bash --rcfile {quoted_rcfile}'"
    )

    # Create additional windows
    for window_config in windows:
        _create_window(name, window_config, workdir, rcfile_dir)

    # Select the main window so we attach to it
    run(f"tmux select-window -t {quoted_name}:{quoted_main_window}")


def select_window(session: str, window: str) -> None:
    """Select a window in a tmux session.

    Args:
        session: Session name.
        window: Window name to select.
    """
    run(f"tmux select-window -t {shlex.quote(session)}:{shlex.quote(window)}", check=False)


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
sleep 0.3
read -t 0.1 -n 10000 discard 2>/dev/null || true
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
    quoted_session = shlex.quote(session)
    quoted_window = shlex.quote(config.name)
    quoted_workdir = shlex.quote(str(workdir))

    # Special handling for "shell" window - create with 2 horizontal panes
    if config.name == "shell":
        shell_rcfile = _create_shell_rcfile(rcfile_dir, workdir)
        quoted_rcfile = shlex.quote(str(shell_rcfile))

        # Create window with first pane (use exec to replace shell process)
        run(
            f"tmux new-window -t {quoted_session} -n {quoted_window} "
            f"-c {quoted_workdir} 'exec bash --rcfile {quoted_rcfile}'"
        )
        # Split horizontally for second pane
        run(
            f"tmux split-window -h -t {quoted_session}:{quoted_window} "
            f"-c {quoted_workdir} 'exec bash --rcfile {quoted_rcfile}'"
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
    run(
        f"tmux new-window -t {quoted_session} -n {quoted_window} "
        f"-c {quoted_workdir} {shlex.quote(config.command)}"
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
    quoted_session = shlex.quote(session)
    quoted_window = shlex.quote(window_name)
    quoted_workdir = shlex.quote(str(workdir))

    # Get install instructions based on tool
    install_cmd = _get_install_instruction(tool_name)

    message = f"Tool '{tool_name}' not found. Install with: {install_cmd}"
    quoted_message = shlex.quote(message)

    # Create window that displays the message
    run(
        f"tmux new-window -t {quoted_session} -n {quoted_window} "
        f"-c {quoted_workdir} bash -c 'echo {quoted_message}; exec bash'"
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
