"""CLI entry points for amplifier-cli-tools.

Thin layer that parses arguments and calls business logic modules.
All business logic is in dev.py, reset.py, and setup.py - this module only handles:
- Argument parsing via argparse
- Error handling and exit codes
- User confirmation prompts

Entry Points
------------
- main_dev(): amplifier-dev command (with setup/config subcommands)
- main_reset(): amplifier-reset command
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from . import dev
from . import reset
from . import tmux


def _confirm(message: str) -> bool:
    """Prompt user for confirmation.

    Args:
        message: Message to display before [y/N] prompt.

    Returns:
        True if user confirms with 'y' or 'Y', False otherwise.
    """
    try:
        response = input(f"{message}\n\nAre you sure? [y/N] ")
        return response.lower() == "y"
    except EOFError:
        return False


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle the default run command (create/attach workspace)."""
    try:
        config = load_config(args.config)
        workdir = args.workdir.resolve()

        # Determine tmux mode: CLI flag overrides config
        use_tmux = args.use_tmux if args.use_tmux is not None else config.dev.use_tmux

        # Handle --kill or --fresh: kill session only, don't delete files
        # --fresh implies --kill but continues to create new session
        if args.kill or args.fresh:
            session_name = dev.get_session_name(workdir)
            if tmux.session_exists(session_name):
                print(f"Killing tmux session: {session_name}")
                tmux.kill_session(session_name)
                print("Session killed.")
            else:
                print(f"No session '{session_name}' to kill.")
            
            # If --fresh, continue to create new session; otherwise exit
            if not args.fresh:
                return 0

        if args.destroy:
            # Derive session name from workdir
            session_name = dev.get_session_name(workdir)

            # Build confirmation message
            message = "This will:"
            if tmux.session_exists(session_name):
                message += f"\n  1. Kill tmux session '{session_name}'"
                message += f"\n  2. Delete directory '{workdir}'"
            else:
                message += f"\n  1. Delete directory '{workdir}'"

            if not _confirm(message):
                print("Aborted.")
                return 0

            dev.destroy_workspace(workdir, session_name)
            return 0

        # Run dev workflow
        success = dev.run_dev(
            config=config.dev,
            workdir=workdir,
            prompt=args.prompt,
            extra=args.extra,
            no_tmux=not use_tmux,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_setup(args: argparse.Namespace) -> int:
    """Handle the setup subcommand."""
    from . import setup

    try:
        success = setup.run_setup(
            interactive=not args.yes,
            skip_tools=args.skip_tools,
            skip_tmux=args.skip_tmux,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_config(args: argparse.Namespace) -> int:
    """Handle the config subcommand."""
    from . import config_manager

    try:
        if args.config_command is None or args.config_command == "show":
            print(config_manager.show_config())
            return 0

        elif args.config_command == "get":
            parts = args.key.split(".", 1)
            if len(parts) != 2:
                print("Error: Key must be in format 'section.key' (e.g., dev.use_tmux)")
                return 1
            section, key = parts
            value = config_manager.get_setting(section, key)
            if value is None:
                print(f"{args.key}: (not set)")
            else:
                print(f"{args.key} = {value}")
            return 0

        elif args.config_command == "set":
            parts = args.key.split(".", 1)
            if len(parts) != 2:
                print("Error: Key must be in format 'section.key' (e.g., dev.use_tmux)")
                return 1
            section, key = parts

            # Parse value
            value_str = args.value.lower()
            if value_str in ("true", "yes", "on", "1"):
                value = True
            elif value_str in ("false", "no", "off", "0"):
                value = False
            else:
                # Try as number, else string
                try:
                    value = int(args.value)
                except ValueError:
                    try:
                        value = float(args.value)
                    except ValueError:
                        value = args.value

            config_manager.set_setting(section, key, value)
            print(f"Set {args.key} = {value}")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        elif args.config_command == "tmux-on":
            config_manager.set_setting("dev", "use_tmux", True)
            print("Enabled tmux mode (dev.use_tmux = true)")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        elif args.config_command == "tmux-off":
            config_manager.set_setting("dev", "use_tmux", False)
            print("Disabled tmux mode (dev.use_tmux = false)")
            print("amplifier-dev will now run amplifier directly without tmux")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        else:
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main_dev() -> int:
    """Entry point for amplifier-dev command.

    Supports subcommands:
    - (default): Create and launch workspace
    - setup: First-time setup
    - config: View/modify configuration

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    # Check if first arg is a subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ("setup", "config"):
        return _main_dev_subcommands()

    # Default: workspace mode
    return _main_dev_workspace()


def _main_dev_subcommands() -> int:
    """Handle setup and config subcommands."""
    parser = argparse.ArgumentParser(
        prog="amplifier-dev",
        description="Amplifier development workspace manager.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Setup subcommand
    setup_parser = subparsers.add_parser(
        "setup",
        help="First-time setup: install dependencies and create configs",
    )
    setup_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Non-interactive mode (auto-accept all prompts)",
    )
    setup_parser.add_argument(
        "--skip-tools",
        action="store_true",
        help="Skip tool installation",
    )
    setup_parser.add_argument(
        "--skip-tmux",
        action="store_true",
        help="Skip tmux.conf creation",
    )

    # Config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="View and modify configuration",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Config commands")

    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("tmux-on", help="Enable tmux mode")
    config_subparsers.add_parser("tmux-off", help="Disable tmux mode (run amplifier directly)")

    get_parser = config_subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")

    set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")
    set_parser.add_argument("value", help="Value to set")

    args = parser.parse_args()

    if args.command == "setup":
        return _cmd_setup(args)
    elif args.command == "config":
        return _cmd_config(args)
    else:
        parser.print_help()
        return 0


def _main_dev_workspace() -> int:
    """Handle the default workspace creation command."""
    parser = argparse.ArgumentParser(
        prog="amplifier-dev",
        description="Amplifier development workspace manager.",
        epilog="""
Subcommands:
  setup              First-time setup: install dependencies and create configs
  config             View and modify configuration

Examples:
  amplifier-dev ~/myproject            Create/attach to workspace
  amplifier-dev -k ~/myproject         Kill session (keep files)
  amplifier-dev -f ~/myproject         Kill session and start fresh
  amplifier-dev -d ~/myproject         Destroy workspace (with confirmation)
  amplifier-dev --no-tmux ~/myproject  Run without tmux
  amplifier-dev setup                  First-time setup
  amplifier-dev config show            Show configuration
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "workdir",
        metavar="WORKDIR",
        type=Path,
        nargs="?",
        help="Directory for workspace (required for create/destroy)",
    )
    parser.add_argument(
        "-k", "--kill",
        action="store_true",
        help="Kill tmux session only (preserve workspace files)",
    )
    parser.add_argument(
        "-f", "--fresh",
        action="store_true",
        help="Kill session and start fresh (implies --kill, then creates new session)",
    )
    parser.add_argument(
        "-d", "--destroy",
        action="store_true",
        help="Destroy session and delete workspace (with confirmation)",
    )
    parser.add_argument(
        "-p", "--prompt",
        metavar="TEXT",
        help="Override default prompt",
    )
    parser.add_argument(
        "-e", "--extra",
        metavar="TEXT",
        help="Append to prompt",
    )
    parser.add_argument(
        "-c", "--config",
        metavar="FILE",
        type=Path,
        help="Use specific config file",
    )
    # Tmux mode options (mutually exclusive)
    tmux_group = parser.add_mutually_exclusive_group()
    tmux_group.add_argument(
        "--tmux",
        action="store_true",
        dest="use_tmux",
        default=None,
        help="Use tmux (override config)",
    )
    tmux_group.add_argument(
        "--no-tmux",
        action="store_false",
        dest="use_tmux",
        help="Run amplifier directly without tmux (override config)",
    )

    args = parser.parse_args()

    # If no workdir provided, show help
    if args.workdir is None:
        parser.print_help()
        return 0

    return _cmd_run(args)


def main_reset() -> int:
    """Entry point for amplifier-reset command.

    Resets the Amplifier installation by removing ~/.amplifier and reinstalling.

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    parser = argparse.ArgumentParser(
        prog="amplifier-reset",
        description="Reset Amplifier installation.",
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Remove entire ~/.amplifier including preserved dirs",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Uninstall only, don't reinstall",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Don't launch amplifier after install",
    )

    args = parser.parse_args()

    try:
        config = load_config()

        # Confirmation unless --yes
        if not args.yes:
            if args.all:
                message = "This will remove ~/.amplifier entirely (including preserved directories)."
            else:
                preserved = ", ".join(config.reset.preserve) if config.reset.preserve else "none"
                message = f"This will reset ~/.amplifier (preserving: {preserved})."

            if not args.no_install:
                message += "\nAmplifier will be reinstalled afterward."

            if not _confirm(message):
                print("Aborted.")
                return 0

        # Run reset workflow
        success = reset.run_reset(
            config=config.reset,
            remove_all=args.all,
            skip_confirm=True,  # We already confirmed above
            no_install=args.no_install,
            no_launch=args.no_launch,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
