# amplifier-cli-tools

CLI tools for Amplifier development workflows.

**New to remote/mobile development?** See [Remote & Mobile Development Guide](docs/REMOTE_MOBILE_DEV.md) for setting up Tailscale + Mosh + tmux for seamless multi-device workflows.

## Installation

```bash
uv tool install git+https://github.com/bkrabach/amplifier-cli-tools
```

## First-Time Setup

Run the setup subcommand to install dependencies and configure tmux:

```bash
amplifier-dev setup
```

This will:
- Check for and install required tools (git, tmux)
- Check for and install optional tools (mosh, lazygit, mc)
- Create a minimal `~/.tmux.conf` if you don't have one (with mouse support, keybindings, etc.)
- Create a `~/.wezterm.lua` if WezTerm is installed but not configured

**Options:**
- `-y, --yes` - Non-interactive mode (auto-accept all prompts)
- `--skip-tools` - Skip tool installation
- `--skip-tmux` - Skip tmux.conf creation

## Commands

### amplifier-dev

Amplifier development workspace manager with subcommands.

#### Create/Attach Workspace (default)

```bash
# Create workspace and launch tmux session
amplifier-dev ~/work/my-feature

# Run amplifier directly without tmux
amplifier-dev --no-tmux ~/work/my-feature

# With a starting prompt for amplifier
amplifier-dev -p "Let's work on the auth module" ~/work/auth-work

# Destroy workspace when done
amplifier-dev -d ~/work/my-feature
```

**Options:**
- `WORKDIR` - Directory for workspace (required)
- `-d, --destroy` - Destroy session and delete workspace (with confirmation)
- `-p, --prompt TEXT` - Override default prompt
- `-e, --extra TEXT` - Append to prompt
- `-c, --config FILE` - Use specific config file
- `--tmux` - Use tmux (override config setting)
- `--no-tmux` - Run amplifier directly without tmux (override config setting)

**What it creates:**
- Git repository with Amplifier repos as submodules
- AGENTS.md file for workspace context
- tmux session with windows:
  - `amplifier` - Amplifier CLI
  - `shell` - Two shell panes
  - `git` - lazygit
  - `files` - mc (midnight commander)

#### Setup Subcommand

First-time setup for dependencies and configuration:

```bash
amplifier-dev setup           # Interactive setup
amplifier-dev setup -y        # Non-interactive (auto-accept)
amplifier-dev setup --skip-tools   # Skip tool installation
```

#### Config Subcommand

View and modify configuration settings:

```bash
# Show current configuration
amplifier-dev config show

# Toggle tmux mode (quick shortcuts)
amplifier-dev config tmux-off   # Run amplifier directly without tmux
amplifier-dev config tmux-on    # Use tmux (default)

# Get/set specific settings
amplifier-dev config get dev.use_tmux
amplifier-dev config set dev.use_tmux false
```

**Config subcommands:**
- `show` - Display current configuration (default)
- `tmux-on` - Enable tmux mode
- `tmux-off` - Disable tmux mode (run amplifier directly)
- `get KEY` - Get a setting value (e.g., `dev.use_tmux`)
- `set KEY VALUE` - Set a setting value

## Resetting Amplifier

To reset your Amplifier installation, use the built-in `amplifier reset` command:

```bash
amplifier reset              # Interactive mode
amplifier reset --cache-only # Just clear cache (safest)
amplifier reset --full -y    # Remove everything
```

See `amplifier reset --help` for all options.

## Configuration

Create `~/.amplifier-cli-tools.toml` to customize behavior:

```toml
[dev]
# Use tmux for multi-window workspace (false = run amplifier directly)
use_tmux = true

# Repositories to clone as submodules
repos = [
    "https://github.com/microsoft/amplifier.git",
    "https://github.com/microsoft/amplifier-core.git",
    "https://github.com/microsoft/amplifier-foundation.git",
]

# Command to run in main window
main_command = "amplifier run --mode chat"

# Default prompt (empty = no auto-prompt)
default_prompt = ""

# Path to custom AGENTS.md template (empty = use built-in)
agents_template = ""

# Tmux windows: name = "command" (empty = shell only)
[dev.windows]
shell = ""           # Two panes, just shell
git = "lazygit"
files = "mc"
```

## Requirements

**Runtime:**
- Python 3.11+
- git
- tmux

Run `amplifier-dev setup` to automatically install missing tools.

**Optional tools (installed by `amplifier-dev setup`):**
- mosh - for resilient remote connections (recommended for mobile/remote dev)
- lazygit - for git window
- mc (midnight commander) - for files window

## Platform Support

Works on:
- **WSL/Ubuntu** with Windows Terminal or any terminal
- **macOS** with Terminal.app, iTerm2, or any terminal
- **Linux** with any terminal

The `amplifier-dev setup` command handles platform-specific installation:
- macOS: Uses Homebrew
- Linux: Uses apt/dnf, or GitHub releases for lazygit

## License

MIT
