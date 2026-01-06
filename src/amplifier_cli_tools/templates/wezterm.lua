-- Minimal WezTerm configuration for amplifier-cli-tools
-- Works on macOS, Windows (WSL), and Linux
-- Place at ~/.wezterm.lua or ~/.config/wezterm/wezterm.lua

local wezterm = require("wezterm")
local config = wezterm.config_builder()

-- Appearance (Catppuccin Mocha - matches tmux theme)
config.color_scheme = "Catppuccin Mocha"
config.font = wezterm.font_with_fallback({
	"JetBrains Mono",
	"Cascadia Code",
	"Consolas",
	"SF Mono",
	"Menlo",
	"monospace",
})
config.font_size = 14.0
config.line_height = 1.1

-- Window
config.window_padding = { left = 8, right = 8, top = 8, bottom = 8 }
config.window_decorations = "RESIZE"
config.initial_rows = 40
config.initial_cols = 140

-- Tabs
config.hide_tab_bar_if_only_one_tab = true

-- Scrollback (tmux handles this, but nice for non-tmux use)
config.scrollback_lines = 50000

-- Bell
config.audible_bell = "Disabled"
config.visual_bell = {
	fade_in_duration_ms = 75,
	fade_out_duration_ms = 75,
	target = "CursorColor",
}

-- Keys - tmux-friendly (don't conflict with Ctrl+b prefix)
config.keys = {
	-- Clear scrollback (Cmd+K on mac, Ctrl+Shift+K elsewhere)
	{ key = "k", mods = "CMD", action = wezterm.action.ClearScrollback("ScrollbackAndViewport") },
	{ key = "k", mods = "CTRL|SHIFT", action = wezterm.action.ClearScrollback("ScrollbackAndViewport") },
}

-- Platform-specific adjustments
if wezterm.target_triple:find("windows") then
	-- Windows: default to WSL Ubuntu
	config.default_domain = "WSL:Ubuntu"
	config.wsl_domains = wezterm.default_wsl_domains()
	for _, domain in ipairs(config.wsl_domains) do
		if domain.name:find("Ubuntu") then
			domain.default_prog = { "bash", "-c", "cd ~ && exec bash -l" }
		end
	end
elseif wezterm.target_triple:find("darwin") then
	-- macOS: Option as Meta for terminal apps (Alt+arrow in tmux)
	config.send_composed_key_when_left_alt_is_pressed = false
	config.send_composed_key_when_right_alt_is_pressed = true
end

-- Performance
config.front_end = "WebGpu"
config.max_fps = 120

-- Terminal capability query settings
-- These can help reduce escape sequences sent on terminal startup that may
-- interfere with applications if they arrive before the shell is ready.
-- The rcfile-based flush logic in amplifier-cli-tools handles this, but
-- disabling unnecessary features can reduce the window for race conditions.
config.enable_kitty_keyboard = false
config.enable_csi_u_key_encoding = false

return config
