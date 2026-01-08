"""Workspace creation and tmux session orchestration for amplifier-dev command.

This module provides the main entry point for the amplifier-dev workflow,
handling workspace setup (git repo initialization, submodules, AGENTS.md)
and tmux session management.

Example:
    >>> from amplifier_cli_tools.dev import run_dev
    >>> from amplifier_cli_tools.config import load_config
    >>> config = load_config()
    >>> run_dev(config.dev, Path("~/amplifier-workspace").expanduser())
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import shutil

import os
import shlex

from .config import DevConfig
from .shell import ensure_commands, ShellError
from . import git
from . import tmux


def get_session_name(workdir: Path) -> str:
    """Get tmux session name from workdir (basename).

    Args:
        workdir: Workspace directory path.

    Returns:
        Session name derived from directory basename.

    Example:
        >>> get_session_name(Path("/home/user/my-workspace"))
        'my-workspace'
    """
    return workdir.name


def build_main_command(config: DevConfig) -> str:
    """Build the main command with bundle flag if configured.

    Inserts --bundle <bundle> after 'amplifier run' if config.bundle is set.

    Args:
        config: Dev configuration with main_command and bundle.

    Returns:
        Command string with bundle flag inserted if applicable.

    Example:
        >>> config = DevConfig(main_command="amplifier run --mode chat", bundle="amplifier-dev", ...)
        >>> build_main_command(config)
        'amplifier run --bundle amplifier-dev --mode chat'
    """
    if not config.main_command:
        return ""

    if not config.bundle:
        return config.main_command

    # Insert --bundle after 'amplifier run'
    cmd = config.main_command
    if "amplifier run" in cmd:
        cmd = cmd.replace("amplifier run", f"amplifier run --bundle {config.bundle}", 1)
    else:
        # Fallback: append to end if pattern not found
        cmd = f"{cmd} --bundle {config.bundle}"

    return cmd


def compute_final_prompt(
    config: DevConfig,
    prompt: str | None,
    extra: str | None,
) -> str:
    """Compute final prompt from config default, override, and extra.

    Args:
        config: Dev configuration with default_prompt.
        prompt: Override prompt (None = use config default).
        extra: Extra text to append to prompt.

    Returns:
        Final computed prompt string.

    Example:
        >>> config = DevConfig(default_prompt="Hello", ...)
        >>> compute_final_prompt(config, None, "World")
        'Hello\\nWorld'
        >>> compute_final_prompt(config, "Override", None)
        'Override'
    """
    # Use override if provided, else use config default
    base_prompt = prompt if prompt is not None else config.default_prompt

    # Append extra if provided
    if extra:
        if base_prompt:
            return f"{base_prompt}\n{extra}"
        return extra

    return base_prompt


def create_agents_md(workdir: Path, config: DevConfig) -> bool:
    """Create AGENTS.md from template if not exists.

    Priority:
    1. Skip if AGENTS.md already exists
    2. Use custom template from config.agents_template if set and exists
    3. Use built-in template from templates/AGENTS.md
    4. Create minimal content if built-in doesn't exist

    Args:
        workdir: Workspace directory path.
        config: Dev configuration with agents_template path.

    Returns:
        True on success, False on failure.
    """
    agents_path = workdir / "AGENTS.md"

    # Skip if already exists
    if agents_path.exists():
        print(f"AGENTS.md already exists at {agents_path}")
        return True

    # Try custom template first
    if config.agents_template:
        custom_template = Path(config.agents_template)
        if custom_template.exists():
            print(f"Copying AGENTS.md from custom template: {custom_template}")
            try:
                shutil.copy(custom_template, agents_path)
                return True
            except OSError as e:
                print(f"Failed to copy custom template: {e}")
                return False
        else:
            print(f"Warning: Custom template not found: {custom_template}")

    # Try built-in template
    try:
        template_content = resources.files(__package__).joinpath(
            "templates", "AGENTS.md"
        ).read_text()
        print("Creating AGENTS.md from built-in template")
        agents_path.write_text(template_content)
        return True
    except (FileNotFoundError, TypeError):
        pass

    # Fallback: create minimal content
    print("Creating minimal AGENTS.md")
    minimal_content = """\
# Amplifier Development Workspace

This workspace contains Amplifier repositories as git submodules.

## Notes

Add your project-specific notes and instructions here.
"""
    try:
        agents_path.write_text(minimal_content)
        return True
    except OSError as e:
        print(f"Failed to create AGENTS.md: {e}")
        return False


def setup_workspace(workdir: Path, config: DevConfig) -> bool:
    """Initialize git repo with submodules and AGENTS.md.

    Workflow:
    1. If workdir/.git doesn't exist:
       - Initialize git repo
       - Add each repo from config as submodule
       - Checkout submodules to main branch
       - Create initial commit
    2. Create AGENTS.md from template

    Args:
        workdir: Workspace directory path.
        config: Dev configuration with repos list.

    Returns:
        True on success, False on failure.
    """
    try:
        # Initialize git repo if needed
        if not git.is_git_repo(workdir):
            print(f"Setting up new workspace: {workdir}")

            # Initialize git repo (creates directory if needed)
            git.init_repo(workdir)

            # Add each repo as submodule
            for repo_url in config.repos:
                git.add_submodule(workdir, repo_url)

            # Checkout submodules to main branch and pull
            if config.repos:
                git.checkout_submodules_to_main(workdir)

            # Create initial commit
            git.initial_commit(
                workdir,
                "Initial workspace setup with Amplifier submodules",
            )
        else:
            print(f"Workspace already initialized: {workdir}")

        # Create AGENTS.md
        if not create_agents_md(workdir, config):
            return False

        return True

    except ShellError as e:
        print(f"Workspace setup failed: {e}")
        return False


def destroy_workspace(workdir: Path, session_name: str) -> bool:
    """Kill tmux session and delete workspace directory.

    Args:
        workdir: Workspace directory to delete.
        session_name: Tmux session name to kill.

    Returns:
        True on success, False on failure.
    """
    # Kill tmux session if exists
    if tmux.session_exists(session_name):
        print(f"Killing tmux session: {session_name}")
        tmux.kill_session(session_name)

    # Delete workspace directory
    if workdir.exists():
        print(f"Deleting workspace: {workdir}")
        try:
            shutil.rmtree(workdir)
            print(f"Workspace destroyed: {workdir}")
            return True
        except OSError as e:
            print(f"Failed to delete workspace: {e}")
            return False
    else:
        print(f"Workspace directory does not exist: {workdir}")
        return True


def _run_amplifier_directly(
    workdir: Path,
    config: DevConfig,
    prompt: str | None,
    extra: str | None,
) -> bool:
    """Run amplifier directly without tmux.

    Changes to workdir and executes the main command, optionally with a prompt.

    Args:
        workdir: Workspace directory.
        config: Dev configuration.
        prompt: Override prompt.
        extra: Extra text to append to prompt.

    Returns:
        True (doesn't return on success due to execvp).
    """
    final_prompt = compute_final_prompt(config, prompt, extra)

    # Change to workdir
    os.chdir(workdir)
    print(f"Changed to: {workdir}")

    # Build command with bundle flag
    final_command = build_main_command(config)
    if not final_command:
        print("No main_command configured. Shell ready.")
        return True

    # Parse command and add prompt if provided
    cmd_parts = shlex.split(final_command)
    if final_prompt:
        cmd_parts.extend(["--prompt", final_prompt])

    print(f"Running: {' '.join(cmd_parts)}")

    # Replace current process with amplifier
    os.execvp(cmd_parts[0], cmd_parts)

    # execvp doesn't return on success
    return True


def run_dev(
    config: DevConfig,
    workdir: Path,
    prompt: str | None = None,
    extra: str | None = None,
    no_tmux: bool = False,
) -> bool:
    """Main entry point for amplifier-dev workflow.

    Workflow:
    1. Ensure required tools exist (git, tmux unless no_tmux, amplifier)
    2. Setup workspace (git repo, submodules, AGENTS.md)
    3. If not no_tmux:
       - Compute session name from workdir basename
       - If session exists, select main window and attach
       - Else create new session and attach

    Args:
        config: Dev configuration.
        workdir: Workspace directory path.
        prompt: Override default prompt (None = use config default).
        extra: Extra text to append to prompt.
        no_tmux: If True, setup workspace only without launching tmux.

    Returns:
        True on success, False on failure.
    """
    # Build list of required commands
    required_commands = ["git"]
    if not no_tmux:
        required_commands.append("tmux")

    # Extract command name from main_command for validation
    # (e.g., "amplifier run --mode chat" -> "amplifier")
    if config.main_command:
        main_cmd_name = config.main_command.split()[0]
        required_commands.append(main_cmd_name)

    # Ensure required tools exist
    try:
        ensure_commands(*required_commands)
    except ShellError as e:
        print(f"Error: {e}")
        return False

    # Setup workspace
    if not setup_workspace(workdir, config):
        return False

    # If not using tmux, run amplifier directly
    if no_tmux:
        print(f"Workspace ready: {workdir}")
        return _run_amplifier_directly(workdir, config, prompt, extra)

    # Compute session name and prompt
    session_name = get_session_name(workdir)
    final_prompt = compute_final_prompt(config, prompt, extra)

    # Handle tmux session
    if tmux.session_exists(session_name):
        print(f"Attaching to existing session: {session_name}")
        # Select the main window before attaching
        tmux.select_window(session_name, "amplifier")
        # Note: attach_session uses execvp, so this call doesn't return
        tmux.attach_session(session_name)
    else:
        print(f"Creating new session: {session_name}")
        tmux.create_session(
            name=session_name,
            workdir=workdir,
            main_window_name="amplifier",
            main_command=build_main_command(config),
            prompt=final_prompt,
            windows=config.windows,
        )
        # Note: attach_session uses execvp, so this call doesn't return
        tmux.attach_session(session_name)

    return True


__all__ = [
    "run_dev",
    "setup_workspace",
    "create_agents_md",
    "destroy_workspace",
    "get_session_name",
    "compute_final_prompt",
    "build_main_command",
]
