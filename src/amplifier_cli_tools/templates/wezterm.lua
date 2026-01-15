-- Enhanced WezTerm configuration for amplifier-cli-tools
-- Works on macOS, Windows (WSL), and Linux
-- Place at ~/.wezterm.lua or ~/.config/wezterm/wezterm.lua

local wezterm = require("wezterm")
local config = wezterm.config_builder()

-- Detect OS
local is_windows = wezterm.target_triple:find("windows") ~= nil
local is_mac = wezterm.target_triple:find("darwin") ~= nil

-- Windows: use PowerShell instead of cmd.exe
if is_windows then
	config.default_prog = { "powershell.exe" }
end

-- Font settings (with fallback if Nerd Font not installed)
config.font = wezterm.font_with_fallback({
	"JetBrainsMono Nerd Font",
	"JetBrains Mono",
	"Cascadia Code",
	"Consolas",
	"SF Mono",
	"Menlo",
	"monospace",
})
config.font_size = 16.0
config.line_height = 1.1

-- Appearance (Catppuccin Mocha - matches tmux theme)
config.color_scheme = "Catppuccin Mocha"

-- Window appearance
if is_windows then
	-- Windows: minimal - just resize borders, drag from tab bar
	config.window_decorations = "RESIZE"
else
	-- Mac/Linux: integrated buttons in tab bar (no separate title bar)
	config.window_decorations = "INTEGRATED_BUTTONS|RESIZE"
end

config.window_padding = {
	left = 10,
	right = 10,
	top = 10,
	bottom = 10,
}
config.initial_rows = 40
config.initial_cols = 140

-- Tab bar
-- Always show tab bar (needed for integrated buttons and dragging)
config.hide_tab_bar_if_only_one_tab = false
config.tab_bar_at_bottom = false -- Top, so drag area is at top like normal title bar
config.tab_max_width = 25 -- Prevent super wide tabs
config.show_tab_index_in_tab_bar = false -- Cleaner: no "1:" prefix

-- Style the tab bar (fancy tab bar has close buttons on tabs)
config.use_fancy_tab_bar = true

-- Make integrated buttons native style, on the right to reduce gap
if is_windows then
	config.integrated_title_button_style = "Windows"
else
	config.integrated_title_button_style = "MacOsNative"
end
config.integrated_title_button_alignment = "Right"

-- Tab bar colors to match Catppuccin Mocha
config.window_frame = {
	font = wezterm.font("JetBrainsMono Nerd Font"),
	font_size = 13.0,
	active_titlebar_bg = "#1e1e2e",
	inactive_titlebar_bg = "#1e1e2e",
}

config.colors = {
	tab_bar = {
		background = "#1e1e2e",
		active_tab = {
			bg_color = "#89b4fa",
			fg_color = "#1e1e2e",
			intensity = "Bold",
		},
		inactive_tab = {
			bg_color = "#1e1e2e",
			fg_color = "#6c7086",
		},
		inactive_tab_hover = {
			bg_color = "#313244",
			fg_color = "#cdd6f4",
		},
		new_tab = {
			bg_color = "#1e1e2e",
			fg_color = "#6c7086",
		},
		new_tab_hover = {
			bg_color = "#313244",
			fg_color = "#cdd6f4",
		},
	},
}

-- Tab colors (Catppuccin Mocha palette)
-- Each color has 'active' (bright) and 'inactive' (dimmed) variants
local tab_colors = {
	red = { active_bg = "#f38ba8", inactive_bg = "#6e3a4a", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	green = { active_bg = "#a6e3a1", inactive_bg = "#4a6648", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	blue = { active_bg = "#89b4fa", inactive_bg = "#3a5070", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	yellow = { active_bg = "#f9e2af", inactive_bg = "#6e6348", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	purple = { active_bg = "#cba6f7", inactive_bg = "#5a4870", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	pink = { active_bg = "#f5c2e7", inactive_bg = "#6e5668", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	orange = { active_bg = "#fab387", inactive_bg = "#6e5038", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
	teal = { active_bg = "#94e2d5", inactive_bg = "#406660", fg = "#1e1e2e", inactive_fg = "#cdd6f4" },
}

-- Clean tab titles (just "PowerShell" not "powershell.exe")
-- Supports "name:color" format (e.g., "Server:blue", "Dev:red")
wezterm.on("format-tab-title", function(tab, tabs, panes, config, hover, max_width)
	local title = tab.tab_title
	local color = nil

	if title and #title > 0 then
		-- Check for "name:color" format
		local name, col = title:match("^(.+):(%w+)$")
		if name and tab_colors[col] then
			title = name
			color = tab_colors[col]
		end
	else
		title = tab.active_pane.title
		-- Remove .exe extension and path
		title = title:gsub("%.exe$", "")
		title = title:gsub(".*[/\\]", "")
		-- Capitalize first letter
		title = title:sub(1, 1):upper() .. title:sub(2)
	end

	-- Add padding
	title = "  " .. title .. "  "

	-- Return with color if specified (bright when active, dimmed when inactive)
	if color then
		if tab.is_active then
			-- ACTIVE: bright colored background, dark text, with indicator
			return {
				{ Background = { Color = color.active_bg } },
				{ Foreground = { Color = color.fg } },
				{ Attribute = { Intensity = "Bold" } },
				{ Text = " ● " .. title },
			}
		else
			-- INACTIVE: dark background, colored text only (no colored bg)
			return {
				{ Background = { Color = "#1e1e2e" } },
				{ Foreground = { Color = color.active_bg } },
				{ Text = title },
			}
		end
	end

	return title
end)

-- Scrollback (tmux handles this, but nice for non-tmux use)
config.scrollback_lines = 50000

-- Cursor
config.default_cursor_style = "SteadyBar"

-- Bell
config.audible_bell = "Disabled"
config.visual_bell = {
	fade_in_duration_ms = 75,
	fade_out_duration_ms = 75,
	target = "CursorColor",
}

-- Keys: CMD on Mac, CTRL on Windows (same shortcuts, different modifier)
local mod_key = is_mac and "CMD" or "CTRL"

config.keys = {
	-- Tabs
	{ key = "t", mods = mod_key, action = wezterm.action.SpawnTab("CurrentPaneDomain") },
	{ key = "w", mods = mod_key, action = wezterm.action.CloseCurrentTab({ confirm = true }) },

	-- Rename tab (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
	-- Leave name blank to keep current name and just change color
	{
		key = "r",
		mods = mod_key .. "|SHIFT",
		action = wezterm.action.PromptInputLine({
			description = "Enter tab name (leave blank to keep current) → then pick a color  [ESC to cancel]",
			action = wezterm.action_callback(function(window, pane, input)
				-- User pressed ESC
				if input == nil then
					return
				end

				-- Get current title (without color suffix) if input is blank
				local name = input
				if #name == 0 then
					local current = window:active_tab():get_title()
					-- Strip existing color suffix if present
					name = current:match("^(.+):%w+$") or current
					-- If still empty, use pane title
					if #name == 0 then
						name = pane:get_title():gsub("%.exe$", ""):gsub(".*[/\\]", "")
					end
				end

				-- Show color picker
				window:perform_action(
					wezterm.action.InputSelector({
						title = "Pick a tab color  [ESC to cancel]",
						choices = {
							{ label = "⬜  Default (no color)" },
							{ label = "🔴  Red", id = "red" },
							{ label = "🟢  Green", id = "green" },
							{ label = "🔵  Blue", id = "blue" },
							{ label = "🟡  Yellow", id = "yellow" },
							{ label = "🟣  Purple", id = "purple" },
							{ label = "🪷  Pink", id = "pink" },
							{ label = "🟠  Orange", id = "orange" },
							{ label = "🪵  Teal", id = "teal" },
						},
						action = wezterm.action_callback(function(window, pane, id)
							if id then
								window:active_tab():set_title(name .. ":" .. id)
							else
								window:active_tab():set_title(name)
							end
						end),
					}),
					pane
				)
			end),
		}),
	},

	-- Splits
	{ key = "d", mods = mod_key, action = wezterm.action.SplitHorizontal({ domain = "CurrentPaneDomain" }) },
	{ key = "d", mods = mod_key .. "|SHIFT", action = wezterm.action.SplitVertical({ domain = "CurrentPaneDomain" }) },

	-- Clear scrollback
	{ key = "k", mods = mod_key, action = wezterm.action.ClearScrollback("ScrollbackAndViewport") },
	{ key = "k", mods = "CTRL|SHIFT", action = wezterm.action.ClearScrollback("ScrollbackAndViewport") },

	-- WSL/Ubuntu (Windows only, Alt+Shift+U - Ctrl+Shift+U is reserved for emoji picker)
	{ key = "u", mods = "ALT|SHIFT", action = wezterm.action.SpawnCommandInNewTab({ args = { "wsl" } }) },
}

-- Platform-specific adjustments
if is_windows then
	-- Windows: default to WSL Ubuntu
	config.default_domain = "WSL:Ubuntu"
	config.wsl_domains = wezterm.default_wsl_domains()
	for _, domain in ipairs(config.wsl_domains) do
		if domain.name:find("Ubuntu") then
			domain.default_prog = { "bash", "-c", "cd ~ && exec bash -l" }
		end
	end
elseif is_mac then
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
