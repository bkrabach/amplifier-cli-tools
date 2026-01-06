# Remote & Mobile Development with amplifier-dev

Work on Amplifier projects from anywhere - your laptop, tablet, or phone - without losing session context when you switch devices or get disconnected.

## The Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                      Always-On Dev Box                          │
│  (WSL/macOS/Ubuntu with tmux sessions that persist 24/7)        │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  tmux session: my-feature                               │   │
│   │  ├── amplifier (AI agent running)                       │   │
│   │  ├── shell (two panes)                                  │   │
│   │  ├── git (lazygit)                                      │   │
│   │  └── files (mc)                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         ▲           ▲           ▲           ▲
         │           │           │           │
    ┌────┴───┐  ┌────┴───┐  ┌────┴───┐  ┌────┴───┐
    │ Laptop │  │ Tablet │  │ Phone  │  │Desktop │
    │ (home) │  │ (cafe) │  │ (bus)  │  │ (work) │
    └────────┘  └────────┘  └────────┘  └────────┘
         │           │           │           │
         └───────────┴─────┬─────┴───────────┘
                           │
              Tailscale VPN + Mosh/SSH + tmux
```

**Key insight**: Your tmux session runs on the always-on box. You just attach to it from whatever device you have. Disconnect? No problem - the session keeps running. Pick up exactly where you left off from any device.

## The Stack

Three layers of resilience work together:

| Layer | Tool | What It Handles |
|-------|------|-----------------|
| **Network** | Tailscale | VPN connectivity, NAT traversal, device discovery |
| **Transport** | Mosh | Connection resilience, roaming, local echo |
| **Session** | tmux | Terminal persistence, scrollback, window management |

Each layer handles failures the others can't:
- Tailscale reconnects when you switch networks
- Mosh survives brief disconnects and IP changes without dropping
- tmux keeps your session alive even if mosh dies

## Prerequisites

### 1. Always-On Development Box

A machine that stays running and accessible:

| Option | Notes |
|--------|-------|
| **WSL on Windows desktop** | Great if you have a Windows PC that stays on |
| **Mac mini / Mac Studio** | Solid choice, low power |
| **Linux server** | Home server, NUC, or cloud VPS |
| **Old laptop** | Repurpose that dusty ThinkPad |

**Requirements:**
- SSH server running
- Git, tmux, mosh installed
- Amplifier and amplifier-cli-tools installed

### 2. Tailscale (VPN Layer)

[Tailscale](https://tailscale.com/) creates a private network across all your devices:

```bash
# Install on your always-on box
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh

# Now your box is accessible at: your-hostname.tailnet-name.ts.net
```

**Why Tailscale?**
- Works through NAT/firewalls (no port forwarding needed)
- Built-in SSH server (no config required)
- Free for personal use (100 devices)
- Works from anywhere with internet

Install Tailscale on all your client devices too (laptop, phone, tablet).

### 3. Mosh (Transport Layer)

[Mosh](https://mosh.org/) (mobile shell) provides connection resilience that SSH can't:

**Install on your dev box:**
```bash
# Ubuntu/Debian/WSL
sudo apt update && sudo apt install mosh

# macOS
brew install mosh

# Verify
mosh --version
```

**Ensure UTF-8 locale** (required by mosh):
```bash
# Check current locale
locale

# If not UTF-8, generate and set it
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8

# Log out and back in, then verify
locale  # Should show en_US.UTF-8
```

**Why Mosh?**

| Scenario | SSH | Mosh |
|----------|-----|------|
| Laptop sleeps for 5 min | Connection dead | Resumes instantly |
| Switch WiFi → cellular | Connection dead | Seamless transition |
| High latency (200ms+) | Sluggish typing | Instant local echo |
| Brief packet loss | Freezes, may disconnect | Graceful degradation |

Mosh uses UDP and maintains terminal state on both ends, so it can recover from network issues that would kill an SSH connection.

### 4. Termius (Client Layer)

[Termius](https://termius.com/) provides a consistent SSH/Mosh experience everywhere:

| Platform | Install |
|----------|---------|
| Windows | Microsoft Store or termius.com |
| macOS | App Store or termius.com |
| Linux | Snap, Flatpak, or .deb/.rpm |
| iOS | App Store |
| Android | Play Store |

**Why Termius?**
- Same experience on all platforms (including mobile)
- **Built-in mosh support** (critical for mobile)
- Syncs hosts/keys across devices
- Good terminal emulator with touch support
- Free tier works well

**Recommended Setup: Two Profiles**

Create two host profiles in Termius for your dev box - one for local/desktop use (SSH) and one for mobile/remote use (Mosh):

| Profile | Protocol | When to Use |
|---------|----------|-------------|
| `devbox` | SSH | Local network, stable connection, need mouse scrolling |
| `devbox-mobile` | Mosh | Mobile, flaky WiFi, cellular, roaming |

**Why two profiles?**

Mosh provides excellent connection resilience but has a limitation: **mouse scrolling doesn't work in tmux** when connected via Mosh + Termius. This is a known issue with how Termius handles mouse events over Mosh connections.

- **SSH profile**: Full mouse support (scrolling works in tmux)
- **Mosh profile**: Connection resilience (survives disconnects, IP changes)

**Creating the profiles:**

1. Install Termius on all your devices
2. Create an account to sync across devices
3. Add your dev box twice:

   **Profile 1: `devbox` (SSH)**
   - Host: `your-hostname.tailnet-name.ts.net`
   - Mosh: **Disabled**
   - Use for: Desktop/laptop on stable connections

   **Profile 2: `devbox-mobile` (Mosh)**
   - Host: `your-hostname.tailnet-name.ts.net`
   - Mosh: **Enabled**
   - Use for: Mobile devices, unreliable networks

Both connect to the same tmux session - just choose the right profile for your situation.

### Alternative Clients

If you prefer other clients, ensure they support mosh:

| Client | Mosh Support | Platforms |
|--------|--------------|-----------|
| **Termius** | Built-in | All (recommended) |
| **Blink Shell** | Built-in | iOS only (excellent) |
| **JuiceSSH** | Via plugin | Android |
| **Terminal** | `mosh` command | macOS/Linux |

For clients without built-in mosh, install the mosh client and connect via command line:
```bash
mosh your-hostname.tailnet-name.ts.net
```

## Workflow

### Starting a Work Session

Connect via mosh and create a workspace:

```bash
# Connect with mosh (from any device)
mosh your-devbox
# Or if using Termius, just tap your saved host (mosh enabled)

# Create a new workspace for your task
amplifier-dev ~/work/add-caching-layer

# You're now in a tmux session with:
# - amplifier running in the main window
# - shell, git, files windows ready
```

### Working Across Devices

**Disconnect gracefully (optional):**
```
Ctrl+b d    # Detach from tmux (session keeps running)
```

**Or just close the terminal / switch apps** - mosh handles brief disconnects, and tmux preserves everything even if mosh dies.

**Reconnect from any device:**
```bash
mosh your-devbox
amplifier-dev ~/work/add-caching-layer   # Reattaches to existing session
```

### The Resilience in Action

| What Happens | What You Experience |
|--------------|---------------------|
| Close laptop lid for 5 min | Open lid → still connected, continue typing |
| Walk out of WiFi range | Brief "mosh: waiting" → reconnects on cellular |
| Phone call interrupts on mobile | Return to Termius → session intact |
| Mosh connection actually dies | `mosh devbox` → tmux session still there |
| Dev box reboots | Mosh dies, tmux dies, but workspace dir remains. Re-run `amplifier-dev` |

### Switching Between Tasks

Run multiple workspaces simultaneously:

```bash
# Different tmux sessions for different tasks
amplifier-dev ~/work/add-caching-layer
amplifier-dev ~/work/fix-auth-bug
amplifier-dev ~/work/refactor-api
```

List all sessions:
```bash
tmux list-sessions
```

Attach to a specific session:
```bash
tmux attach -t add-caching-layer
```

### Finishing a Task

When you're done with a task and have pushed all changes:

```bash
amplifier-dev --destroy ~/work/add-caching-layer
```

This kills the tmux session and removes the workspace directory.

## Mobile-Specific Tips

### Touch-Friendly tmux Navigation

**Switch windows** (most common action):
- `Ctrl+b` then window number (`0`, `1`, `2`, etc.)
- Or `Ctrl+b n` (next) / `Ctrl+b p` (previous)

**Scroll in tmux** (to see history):
- `Ctrl+b [` enters copy mode
- Use arrow keys or Page Up/Down to navigate
- `q` to exit copy mode

> **Note**: Mouse scrolling does NOT work in tmux when connected via Mosh. This is a known limitation. Use keyboard navigation in copy mode, or connect via SSH when you need mouse scrolling.

### Termius Mobile Tips

1. **Use the `devbox-mobile` (Mosh) profile** for connection resilience
2. **Use the extended keyboard bar** - Termius shows Ctrl, Alt, Esc, arrow keys
3. **Pinch to zoom** - Adjust text size on the fly
4. **Landscape mode** - More columns for code viewing
5. **Quick commands** - Save common commands as snippets

### Optimizing for Small Screens

When on mobile, focus on the amplifier window:
```
Ctrl+b 0    # Jump to main amplifier window
```

Use Amplifier's chat interface - it's more mobile-friendly than editing code directly.

**Mobile-friendly tasks:**
- Code review and discussion
- Architecture planning
- Debugging via conversation
- Reading/researching in the codebase
- Committing and pushing completed work

**Save for larger screens:**
- Heavy code editing
- Complex multi-file refactoring
- Side-by-side diffs

## Configuration

### Recommended tmux Configuration

The `amplifier-setup` command creates a mobile-friendly `~/.tmux.conf`:

```bash
amplifier-setup   # Run once on your dev box
```

Key features it enables:
- Mouse support (scrolling, clicking, resizing)
- Sane scroll history (10,000 lines)
- Intuitive pane splitting (`Ctrl+b |` and `Ctrl+b -`)
- Status bar with session info

### Optimizing for High Latency

If you're frequently on slow connections, add to `~/.tmux.conf`:

```bash
# Reduce status bar update frequency
set -g status-interval 5

# Larger scrollback for long sessions
set -g history-limit 50000
```

## Troubleshooting

### Mosh: "locale not found" or UTF-8 errors

Mosh requires UTF-8 locale on the server:

```bash
# On the dev box
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
# Log out and back in
```

### Mosh: "connection refused" or timeout

1. **Check mosh-server is installed**: `which mosh-server`
2. **UDP ports may be blocked**: Mosh uses UDP 60000-61000. If on a restrictive network, fall back to SSH:
   ```bash
   ssh your-devbox  # Plain SSH as fallback
   ```
3. **Tailscale handles ports**: Within your tailnet, UDP should work. If not, check `tailscale status`.

### Mouse scrolling doesn't work in tmux (Mosh)

**This is a known limitation**, not a misconfiguration. When connected via Mosh, mouse scroll events don't properly reach tmux. This affects Termius and most other terminal emulators.

**Workarounds:**

1. **Use SSH when you need mouse scrolling** - Connect with your SSH profile instead of Mosh
2. **Keyboard navigation in copy mode**:
   ```
   Ctrl+b [        # Enter copy mode
   Arrow keys      # Navigate line by line
   Page Up/Down    # Navigate by page
   Ctrl+u/Ctrl+d   # Half-page up/down
   g / G           # Jump to top/bottom
   q               # Exit copy mode
   ```
3. **Termius Gesture Mode** (mobile): Tap the finger icon on the keyboard toolbar, then swipe for arrow key emulation

**Recommendation**: Use the dual-profile approach - SSH profile for desktop/mouse work, Mosh profile for mobile/unreliable networks.

### SSH vs Mosh: When to use which

| Situation | Use | Why |
|-----------|-----|-----|
| Desktop, stable network | SSH | Full mouse support |
| Mobile device | Mosh | Survives disconnects |
| Flaky WiFi / cellular | Mosh | Connection resilience |
| Heavy scrolling/mouse work | SSH | Mouse events work |
| Laptop that sleeps frequently | Mosh | Resumes after wake |

Both protocols connect to the same tmux session - you can switch between them freely.

### "Connection refused" when connecting

1. Check Tailscale is running on both devices: `tailscale status`
2. Verify the hostname: `tailscale status | grep your-hostname`
3. Ensure SSH is enabled: `sudo tailscale up --ssh`

### Session not found when reattaching

The session name comes from the directory name:

```bash
# These create/attach to session named "my-feature"
amplifier-dev ~/work/my-feature
amplifier-dev /home/user/work/my-feature   # Same session

# This is a DIFFERENT session (different directory name)
amplifier-dev ~/projects/my-feature
```

### tmux shows old session state

If Amplifier or other processes died, you might see a stale window. Just restart:

```bash
# In the tmux session
Ctrl+b :    # tmux command prompt
respawn-pane -k   # Kill and restart current pane
```

Or destroy and recreate the workspace:

```bash
amplifier-dev --destroy ~/work/my-task
amplifier-dev ~/work/my-task
```

## Example: A Day of Mobile Development

**Morning (laptop at home):**
```bash
# Use SSH profile - stable connection, mouse scrolling works
ssh devbox
amplifier-dev ~/work/new-feature -p "Let's implement the caching layer"
# Work for a couple hours, scroll through code, make progress
Ctrl+b d    # Detach, head out
```

**Commute (phone on cellular):**
```bash
# Tap devbox-mobile in Termius (Mosh profile)
amplifier-dev ~/work/new-feature
# Check Amplifier's progress, review suggestions
# Approve a commit, push to branch
# Just switch apps - mosh handles disconnect
```

**Afternoon (tablet at cafe, flaky WiFi):**
```bash
# Use Mosh profile - connection survives WiFi drops
amplifier-dev ~/work/new-feature
# Continue the conversation, refine implementation
# Create PR when ready
```

**Evening (desktop at home):**
```bash
# Back to SSH profile for mouse scrolling comfort
ssh devbox
amplifier-dev ~/work/new-feature
# Final review, address PR feedback, scroll through diffs
amplifier-dev --destroy ~/work/new-feature   # Task complete!
```

One continuous session, four devices, zero context loss. Use SSH when you can, Mosh when you need resilience.

## Summary: The Full Stack

```
┌─────────────────────────────────────────────────┐
│                  Your Device                    │
│  (Termius with mosh support)                    │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              Tailscale VPN                      │
│  (Handles: NAT traversal, device discovery,    │
│   network switching, encryption)               │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                   Mosh                          │
│  (Handles: Brief disconnects, IP roaming,      │
│   local echo, packet loss)                     │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                   tmux                          │
│  (Handles: Session persistence, scrollback,    │
│   window management, survives mosh death)      │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              amplifier-dev                      │
│  (Handles: Workspace setup, multi-repo,        │
│   consistent dev environment)                  │
└─────────────────────────────────────────────────┘
```

Each layer adds resilience. Together, they make remote development feel local.
