"""Configuration file management for amplifier-cli-tools.

Provides utilities for reading, writing, and modifying the user's config file.
"""

from pathlib import Path
from typing import Any
import tomllib

from .config import DEFAULT_CONFIG_PATH, get_default_config


def get_config_path() -> Path:
    """Get the user's config file path."""
    return DEFAULT_CONFIG_PATH


def config_exists() -> bool:
    """Check if user config file exists."""
    return DEFAULT_CONFIG_PATH.exists()


def read_config_raw() -> dict:
    """Read raw config as dict, or empty dict if not exists."""
    if not DEFAULT_CONFIG_PATH.exists():
        return {}
    with open(DEFAULT_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def write_config_raw(data: dict) -> None:
    """Write config dict to file in TOML format.
    
    Note: This is a simple writer that handles the common cases.
    For complex configs, consider using tomlkit for round-trip preservation.
    """
    lines = []
    
    # Write top-level sections
    for section, values in data.items():
        if isinstance(values, dict):
            # Check if this is a nested section (like [dev.windows])
            nested_sections = {}
            flat_values = {}
            
            for key, val in values.items():
                if isinstance(val, dict):
                    nested_sections[key] = val
                else:
                    flat_values[key] = val
            
            # Write section header and flat values
            lines.append(f"[{section}]")
            for key, val in flat_values.items():
                lines.append(f"{key} = {_toml_value(val)}")
            lines.append("")
            
            # Write nested sections
            for nested_name, nested_values in nested_sections.items():
                lines.append(f"[{section}.{nested_name}]")
                for key, val in nested_values.items():
                    lines.append(f"{key} = {_toml_value(val)}")
                lines.append("")
        else:
            # Top-level value (unusual but supported)
            lines.append(f"{section} = {_toml_value(values)}")
    
    DEFAULT_CONFIG_PATH.write_text("\n".join(lines))


def _toml_value(val) -> str:
    """Convert Python value to TOML string representation."""
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, str):
        # Escape and quote strings
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        items = ", ".join(_toml_value(v) for v in val)
        return f"[{items}]"
    else:
        return str(val)


def get_setting(section: str, key: str, default=None):
    """Get a specific setting value.
    
    Args:
        section: Config section (e.g., "dev", "reset")
        key: Setting key within section
        default: Default value if not set
        
    Returns:
        Setting value or default
    """
    config = read_config_raw()
    return config.get(section, {}).get(key, default)


def set_setting(section: str, key: str, value) -> None:
    """Set a specific setting value.
    
    Creates the config file if it doesn't exist.
    
    Args:
        section: Config section (e.g., "dev", "reset")
        key: Setting key within section
        value: Value to set
    """
    from importlib import resources
    
    # If config doesn't exist, start with defaults
    if not config_exists():
        try:
            template_bytes = (
                resources.files("amplifier_cli_tools")
                .joinpath("templates", "default-config.toml")
                .read_bytes()
            )
            config = tomllib.loads(template_bytes.decode("utf-8"))
        except Exception:
            config = {}
    else:
        config = read_config_raw()
    
    # Ensure section exists
    if section not in config:
        config[section] = {}
    
    # Set the value
    config[section][key] = value
    
    # Write back
    write_config_raw(config)


def show_config() -> str:
    """Return formatted display of current configuration."""
    from .config import load_config
    
    config = load_config()
    defaults = get_default_config()
    
    lines = []
    lines.append(f"Config file: {DEFAULT_CONFIG_PATH}")
    lines.append(f"  Exists: {'yes' if config_exists() else 'no (using defaults)'}")
    lines.append("")
    
    # Dev settings
    lines.append("[dev]")
    use_tmux_default = defaults.dev.use_tmux
    use_tmux_current = config.dev.use_tmux
    marker = "" if use_tmux_current == use_tmux_default else " (customized)"
    lines.append(f"  use_tmux = {str(use_tmux_current).lower()}{marker}")
    lines.append(f"  main_command = \"{config.dev.main_command}\"")
    lines.append(f"  repos = [{len(config.dev.repos)} repos]")
    lines.append(f"  windows = [{len(config.dev.windows)} windows]")
    
    return "\n".join(lines)


def _parse_key(key: str) -> tuple[str, str, str | None]:
    """Parse dot-notation key into components.
    
    Args:
        key: Key like 'dev.repos' or 'dev.windows.git'
        
    Returns:
        Tuple of (section, setting, nested_key or None)
        - 'dev.use_tmux' -> ('dev', 'use_tmux', None)
        - 'dev.repos' -> ('dev', 'repos', None)
        - 'dev.windows.git' -> ('dev', 'windows', 'git')
        
    Raises:
        ValueError: If key format is invalid
    """
    parts = key.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid key format: '{key}'. Use 'section.key' (e.g., 'dev.use_tmux')")
    
    section = parts[0]
    setting = parts[1]
    nested_key = ".".join(parts[2:]) if len(parts) > 2 else None
    
    return section, setting, nested_key


def get_nested_setting(key: str) -> Any:
    """Get setting by dot-notation key.
    
    Args:
        key: Key like 'dev.use_tmux', 'dev.repos', or 'dev.windows.git'
        
    Returns:
        The setting value (from config file or defaults)
        
    Examples:
        >>> get_nested_setting('dev.use_tmux')
        True
        >>> get_nested_setting('dev.repos')
        ['https://github.com/...', ...]
        >>> get_nested_setting('dev.windows.git')
        'lazygit'
    """
    from .config import load_config
    
    section, setting, nested_key = _parse_key(key)
    
    # Use load_config which merges with defaults
    config = load_config()
    
    if section == "dev":
        dev = config.dev
        if setting == "use_tmux":
            return dev.use_tmux
        elif setting == "bundle":
            return dev.bundle
        elif setting == "main_command":
            return dev.main_command
        elif setting == "default_prompt":
            return dev.default_prompt
        elif setting == "agents_template":
            return dev.agents_template
        elif setting == "repos":
            return dev.repos
        elif setting == "windows":
            # Convert WindowConfig list to dict
            windows_dict = {w.name: w.command for w in dev.windows}
            if nested_key:
                return windows_dict.get(nested_key)
            return windows_dict
    
    return None


def set_nested_setting(key: str, value: Any) -> None:
    """Set setting by dot-notation key.
    
    Args:
        key: Key like 'dev.use_tmux' or 'dev.windows.git'
        value: Value to set
        
    Examples:
        >>> set_nested_setting('dev.use_tmux', False)
        >>> set_nested_setting('dev.windows.git', 'tig')
    """
    section, setting, nested_key = _parse_key(key)
    
    # Load or create config
    if not config_exists():
        _initialize_config()
    config = read_config_raw()
    
    # Ensure section exists
    if section not in config:
        config[section] = {}
    
    if nested_key is not None:
        # Setting a nested key (e.g., dev.windows.git)
        if setting not in config[section]:
            config[section][setting] = {}
        if not isinstance(config[section][setting], dict):
            raise ValueError(f"Cannot set nested key: '{section}.{setting}' is not a dict")
        config[section][setting][nested_key] = value
    else:
        # Setting a top-level key in section
        config[section][setting] = value
    
    write_config_raw(config)


def add_to_setting(key: str, value: str) -> str:
    """Add value to a list or dict setting.
    
    Args:
        key: Key like 'dev.repos' (list) or 'dev.windows' (dict, requires nested key)
        value: Value to add. For dicts, use 'key=value' format.
        
    Returns:
        Success message
        
    Raises:
        ValueError: If key doesn't point to a list/dict, or format is invalid
        
    Examples:
        >>> add_to_setting('dev.repos', 'https://github.com/example/repo.git')
        'Added to dev.repos'
        >>> add_to_setting('dev.windows', 'logs=tail -f /var/log/syslog')
        'Added dev.windows.logs'
    """
    section, setting, nested_key = _parse_key(key)
    
    if not config_exists():
        _initialize_config()
    config = read_config_raw()
    
    if section not in config:
        config[section] = {}
    
    current = config[section].get(setting)
    
    # Handle list
    if isinstance(current, list):
        if nested_key:
            raise ValueError(f"'{section}.{setting}' is a list, not a dict. Use '{section}.{setting}' without nested key.")
        if value in current:
            return f"Value already exists in {key}"
        current.append(value)
        config[section][setting] = current
        write_config_raw(config)
        return f"Added to {key}"
    
    # Handle dict
    if isinstance(current, dict) or current is None:
        if nested_key:
            # Key provided: dev.windows.git = value
            if setting not in config[section]:
                config[section][setting] = {}
            config[section][setting][nested_key] = value
            write_config_raw(config)
            return f"Added {section}.{setting}.{nested_key}"
        else:
            # No nested key, expect key=value format
            if "=" not in value:
                raise ValueError(f"'{section}.{setting}' is a dict. Use 'key=value' format or specify full key like '{section}.{setting}.name'")
            k, v = value.split("=", 1)
            if setting not in config[section]:
                config[section][setting] = {}
            config[section][setting][k.strip()] = v.strip()
            write_config_raw(config)
            return f"Added {section}.{setting}.{k.strip()}"
    
    raise ValueError(f"'{key}' is not a list or dict (type: {type(current).__name__})")


def remove_from_setting(key: str, value: str | None = None) -> str:
    """Remove from a list (by value or index) or dict (by key).
    
    Args:
        key: Key like 'dev.repos' (list) or 'dev.windows.git' (dict entry)
        value: For lists: value to remove or index (e.g., '0', '1').
               For dicts: omit if key includes the entry name.
               
    Returns:
        Success message
        
    Raises:
        ValueError: If operation is invalid
        
    Examples:
        >>> remove_from_setting('dev.repos', 'https://github.com/example/repo.git')
        'Removed from dev.repos'
        >>> remove_from_setting('dev.repos', '0')  # Remove by index
        'Removed from dev.repos: https://...'
        >>> remove_from_setting('dev.windows.git')  # Remove dict key
        'Removed dev.windows.git'
    """
    section, setting, nested_key = _parse_key(key)
    
    if not config_exists():
        raise ValueError("No config file exists")
    
    config = read_config_raw()
    
    if section not in config or setting not in config[section]:
        raise ValueError(f"Setting '{section}.{setting}' not found")
    
    current = config[section][setting]
    
    # Remove from dict by nested key
    if nested_key is not None:
        if not isinstance(current, dict):
            raise ValueError(f"'{section}.{setting}' is not a dict")
        if nested_key not in current:
            raise ValueError(f"Key '{nested_key}' not found in {section}.{setting}")
        del current[nested_key]
        write_config_raw(config)
        return f"Removed {key}"
    
    # Remove from list
    if isinstance(current, list):
        if value is None:
            raise ValueError(f"'{key}' is a list. Specify value or index to remove.")
        
        # Try as index first
        if value.isdigit():
            idx = int(value)
            if idx < 0 or idx >= len(current):
                raise ValueError(f"Index {idx} out of range (list has {len(current)} items)")
            removed = current.pop(idx)
            write_config_raw(config)
            return f"Removed from {key}: {removed}"
        
        # Try as value
        if value not in current:
            raise ValueError(f"Value '{value}' not found in {key}")
        current.remove(value)
        write_config_raw(config)
        return f"Removed from {key}"
    
    # Remove dict key via value parameter
    if isinstance(current, dict):
        if value is None:
            raise ValueError(f"'{key}' is a dict. Specify key to remove (e.g., '{key}.keyname' or provide key as value)")
        if value not in current:
            raise ValueError(f"Key '{value}' not found in {key}")
        del current[value]
        write_config_raw(config)
        return f"Removed {key}.{value}"
    
    raise ValueError(f"'{key}' is not a list or dict")


def reset_setting(key: str | None = None) -> str:
    """Reset setting(s) to default values.
    
    Args:
        key: Key to reset (e.g., 'dev.use_tmux', 'dev.windows'), 
             or None to reset entire config
             
    Returns:
        Success message
        
    Examples:
        >>> reset_setting('dev.use_tmux')
        'Reset dev.use_tmux to default: true'
        >>> reset_setting()
        'Reset all settings to defaults'
    """
    defaults = get_default_config()
    
    if key is None:
        # Reset entire config - delete file so defaults are used
        if config_exists():
            DEFAULT_CONFIG_PATH.unlink()
        return "Reset all settings to defaults (config file removed)"
    
    section, setting, nested_key = _parse_key(key)
    
    # Get default value
    if section == "dev":
        dev_defaults = defaults.dev
        if setting == "use_tmux":
            default_val = dev_defaults.use_tmux
        elif setting == "repos":
            default_val = dev_defaults.repos
        elif setting == "bundle":
            default_val = dev_defaults.bundle
        elif setting == "main_command":
            default_val = dev_defaults.main_command
        elif setting == "default_prompt":
            default_val = dev_defaults.default_prompt
        elif setting == "agents_template":
            default_val = dev_defaults.agents_template
        elif setting == "windows":
            # Convert WindowConfig list to dict for storage
            default_val = {w.name: w.command for w in dev_defaults.windows}
            if nested_key:
                # Resetting just one window
                window_default = default_val.get(nested_key)
                if window_default is None:
                    # Key doesn't exist in defaults - remove it
                    config = read_config_raw()
                    if section in config and setting in config[section] and nested_key in config[section][setting]:
                        del config[section][setting][nested_key]
                        write_config_raw(config)
                        return f"Removed {key} (not in defaults)"
                    return f"{key} already not set"
                set_nested_setting(key, window_default)
                return f"Reset {key} to default: {window_default!r}"
        else:
            raise ValueError(f"Unknown setting: {key}")
    else:
        raise ValueError(f"Unknown section: {section}")
    
    # Set to default value
    if not config_exists():
        return f"{key} already at default: {_format_value(default_val)}"
    
    set_nested_setting(key, default_val)
    return f"Reset {key} to default: {_format_value(default_val)}"


def _format_value(val: Any) -> str:
    """Format a value for display."""
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, list):
        return f"[{len(val)} items]"
    if isinstance(val, dict):
        return f"{{{len(val)} entries}}"
    return str(val)


def show_config_full() -> str:
    """Return comprehensive formatted display of ALL settings.
    
    Shows all scalars, lists, and dicts with their full values.
    """
    from .config import load_config
    
    config = load_config()
    defaults = get_default_config()
    raw = read_config_raw()
    
    lines = []
    lines.append(f"Config file: {DEFAULT_CONFIG_PATH}")
    lines.append(f"  Exists: {'yes' if config_exists() else 'no (using defaults)'}")
    lines.append("")
    
    # Dev section
    lines.append("[dev]")
    
    # Scalars
    scalars = [
        ("use_tmux", config.dev.use_tmux, defaults.dev.use_tmux),
        ("bundle", config.dev.bundle, defaults.dev.bundle),
        ("main_command", config.dev.main_command, defaults.dev.main_command),
        ("default_prompt", config.dev.default_prompt, defaults.dev.default_prompt),
        ("agents_template", config.dev.agents_template, defaults.dev.agents_template),
    ]
    
    for name, current, default in scalars:
        marker = "" if current == default else " (customized)"
        if isinstance(current, bool):
            lines.append(f"  {name} = {str(current).lower()}{marker}")
        elif isinstance(current, str):
            display = current if len(current) <= 50 else current[:47] + "..."
            lines.append(f'  {name} = "{display}"{marker}')
        else:
            lines.append(f"  {name} = {current}{marker}")
    
    # Repos (list)
    lines.append("")
    lines.append("  repos:")
    if config.dev.repos:
        for i, repo in enumerate(config.dev.repos):
            lines.append(f"    [{i}] {repo}")
    else:
        lines.append("    (empty)")
    
    # Windows (dict)
    lines.append("")
    lines.append("  windows:")
    if config.dev.windows:
        for w in config.dev.windows:
            cmd_display = w.command if w.command else "(shell only)"
            lines.append(f"    {w.name} = {cmd_display}")
    else:
        lines.append("    (empty)")
    
    return "\n".join(lines)


def _initialize_config() -> None:
    """Initialize config file from defaults if it doesn't exist."""
    from importlib import resources
    
    if config_exists():
        return
    
    try:
        template_bytes = (
            resources.files("amplifier_cli_tools")
            .joinpath("templates", "default-config.toml")
            .read_bytes()
        )
        config = tomllib.loads(template_bytes.decode("utf-8"))
    except Exception:
        config = {}
    
    write_config_raw(config)


__all__ = [
    "get_config_path",
    "config_exists",
    "read_config_raw",
    "write_config_raw",
    "get_setting",
    "set_setting",
    "show_config",
    "get_nested_setting",
    "set_nested_setting",
    "add_to_setting",
    "remove_from_setting",
    "reset_setting",
    "show_config_full",
]
