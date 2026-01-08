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

-- Tab colors (Catppuccin Mocha palette) for colored tab names
local tab_colors = {
	red = { bg = "#f38ba8", fg = "#1e1e2e" },
	green = { bg = "#a6e3a1", fg = "#1e1e2e" },
	blue = { bg = "#89b4fa", fg = "#1e1e2e" },
	yellow = { bg = "#f9e2af", fg = "#1e1e2e" },
	purple = { bg = "#cba6f7", fg = "#1e1e2e" },
	pink = { bg = "#f5c2e7", fg = "#1e1e2e" },
	orange = { bg = "#fab387", fg = "#1e1e2e" },
	teal = { bg = "#94e2d5", fg = "#1e1e2e" },
}

-- Format tab titles with optional colors
-- Supports "name:color" format (e.g., "Server:blue", "Dev:red")
wezterm.on("format-tab-title", function(tab)
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
		title = title:gsub("%.exe$", ""):gsub(".*[/\\]", "")
		-- Capitalize first letter
		if #title > 0 then
			title = title:sub(1, 1):upper() .. title:sub(2)
		end
	end

	-- Add padding
	title = "  " .. title .. "  "

	-- Return with color if specified
	if color then
		return {
			{ Background = { Color = color.bg } },
			{ Foreground = { Color = color.fg } },
			{ Text = title },
		}
	end

	return title
end)

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

	-- Rename tab with color picker (Cmd+Shift+R on Mac, Ctrl+Shift+R elsewhere)
	-- Leave name blank to keep current name and just change color
	{
		key = "r",
		mods = "CMD|SHIFT",
		action = wezterm.action.PromptInputLine({
			description = "Enter tab name (blank = keep current) → then pick color  [ESC to cancel]",
			action = wezterm.action_callback(function(window, pane, input)
				if input == nil then
					return
				end
				local name = input
				if #name == 0 then
					local current = window:active_tab():get_title()
					name = current:match("^(.+):%w+$") or current
					if #name == 0 then
						name = pane:get_title():gsub("%.exe$", ""):gsub(".*[/\\]", "")
					end
				end
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
							{ label = "🩷  Pink", id = "pink" },
							{ label = "🟠  Orange", id = "orange" },
							{ label = "🩵  Teal", id = "teal" },
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
	{
		key = "r",
		mods = "CTRL|SHIFT",
		action = wezterm.action.PromptInputLine({
			description = "Enter tab name (blank = keep current) → then pick color  [ESC to cancel]",
			action = wezterm.action_callback(function(window, pane, input)
				if input == nil then
					return
				end
				local name = input
				if #name == 0 then
					local current = window:active_tab():get_title()
					name = current:match("^(.+):%w+$") or current
					if #name == 0 then
						name = pane:get_title():gsub("%.exe$", ""):gsub(".*[/\\]", "")
					end
				end
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
							{ label = "🩷  Pink", id = "pink" },
							{ label = "🟠  Orange", id = "orange" },
							{ label = "🩵  Teal", id = "teal" },
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
