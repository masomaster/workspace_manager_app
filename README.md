# Workspace Manager App

A macOS workspace management tool that saves and restores complete workspace setups including app positions, Safari tabs, Word documents, and more.

## Features

- Save current workspace state (running apps, window positions, Safari tabs, Word documents)
- Restore saved workspaces
- Command-line interface for direct usage
- Menu bar app for convenient access
- Support for Safari, Microsoft Word, Logos Bible Software, Zotero, and other apps

## Installation

### Requirements

Install the required Python package for the menu bar app:

```bash
pip3 install rumps
```

### System Permissions

Terminal (on macOS) requires the following permissions:

1. **Files & Folders access** to the parent directory (e.g., Desktop)
2. **Accessibility privileges**

To grant these permissions:
1. Go to System Preferences → Security & Privacy → Privacy
2. Add Terminal to "Files and Folders" and grant access to Desktop (or parent directory)
3. Add Terminal to "Accessibility" and enable it

## Usage

### Command Line Interface

You can use the app directly from the command line (from workspace_manager_app/src/):

```bash
# Save current workspace
python3 workspace_manager_app.py save "My Workspace"

# Load a workspace
python3 workspace_manager_app.py load "My Workspace"

# List all saved workspaces
python3 workspace_manager_app.py list

# Delete a workspace
python3 workspace_manager_app.py delete "My Workspace"
```

### Menu Bar App

Start the menu bar application:

```bash
python3 workspace_menubar_wrapper.py
```

The menu bar app provides:
- Save Current Workspace
- Load Workspace (submenu with saved workspaces)
- Delete Workspace
- List Workspaces

### Auto-Launch Setup

To automatically launch the menu bar app at login:

1. Make the launch script executable:
   ```bash
   chmod +x launch_workspaces_menubar_app.sh
   ```

2. Add `launch_workspaces_menubar_app.sh` as a login item:
   - Go to System Preferences → Users & Groups → Login Items
   - Click the "+" button and select the script

## File Structure

```
workspace_manager_app/
├── src/
│   ├── workspace_manager_app.py      # Main command-line application
│   ├── workspace_menubar_wrapper.py  # Menu bar wrapper using rumps
│   ├── launch_workspaces_menubar_app.sh  # Launch script
│   └── saved_workspaces/             # Directory for saved workspace files
└── README.md
```

## Supported Applications

- **Safari**: Saves and restores tabs and window positions
- **Microsoft Word**: Saves and restores open documents
- **Logos Bible Software**: Saves and restores layouts and window positions
- **Zotero**: Saves and restores window positions
- **Generic Apps**: Saves and restores window positions for any running application

## Notes

- Workspaces are saved as JSON files in the `saved_workspaces` directory
- The app uses AppleScript to interact with macOS applications
- Window positioning may vary slightly depending on system settings and display configuration
- Some applications may require additional time to fully load before window positioning takes effect