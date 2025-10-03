#!/usr/bin/env python3
"""
Menu Bar Workspace Manager using rumps
Wraps the working command-line script with a clean menu bar interface
"""

import rumps
import subprocess
import threading
import json
from pathlib import Path

class WorkspaceMenuBarApp(rumps.App):
    def __init__(self):
        super(WorkspaceMenuBarApp, self).__init__(
            "Workspaces",
            title=None,
            icon="./rectangle.grid.2x2.png",
            quit_button=None,
            template=True  # Hide from dock
        )
        
        # Path to the working command-line script
        self.script_path = Path(__file__).parent / "workspace_manager_app.py"
        
        # Create initial menu
        self.menu = [
            "Save Current Workspace",
            None,  # Separator
            "Delete Workspace",
            None,  # Separator
            "List Workspaces",
            None,  # Separator
            rumps.MenuItem("Quit", callback=rumps.quit_application)
        ]
        
        # Update with existing workspaces
        self.update_workspace_menu()
    
    def run_command(self, command_args):
        """Run the command-line script with given arguments"""
        try:
            cmd = ["python3", str(self.script_path)] + command_args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def get_workspace_list(self):
        """Get list of saved workspaces"""
        success, stdout, stderr = self.run_command(["list"])
        if not success:
            return []
        
        workspaces = []
        for line in stdout.split('\n'):
            if line.startswith('• '):
                # Extract workspace name from "• Name - X apps: ..."
                name = line[2:].split(' - ')[0].strip()
                if name:
                    workspaces.append(name)
        
        return workspaces
    
    def update_workspace_menu(self):
        """Update the Load Workspace menu with current workspaces"""
        # Remove old Load Workspace menu if it exists
        if "Load Workspace" in self.menu:
            del self.menu["Load Workspace"]
        
        workspaces = self.get_workspace_list()
        
        if workspaces:
            # Create Load Workspace submenu
            load_menu = rumps.MenuItem("Load Workspace")
            for workspace in workspaces:
                def make_callback(ws_name):
                    return lambda _: self.load_workspace_background(ws_name)
                
                item = rumps.MenuItem(workspace, callback=make_callback(workspace))
                load_menu.add(item)
            
            # Insert after Save Current Workspace
            self.menu.insert_after("Save Current Workspace", load_menu)
        else:
            # Add disabled item
            disabled_item = rumps.MenuItem("Load Workspace (No workspaces saved)")
            disabled_item.set_callback(None)
            self.menu.insert_after("Save Current Workspace", disabled_item)
    
    def load_workspace_background(self, name):
        """Load workspace in background thread"""
        def load_worker():
            rumps.notification(
                title="Workspaces",
                subtitle="Loading workspace...",
                message=f"Loading '{name}'"
            )
            
            success, stdout, stderr = self.run_command(["load", name])
            
            if success:
                rumps.notification(
                    title="Workspaces",
                    subtitle="Workspace loaded",
                    message=f"'{name}' restored successfully"
                )
            else:
                rumps.notification(
                    title="Workspaces",
                    subtitle="Load failed",
                    message=f"Error loading '{name}': {stderr}"
                )
        
        # Run in background thread so UI doesn't freeze
        threading.Thread(target=load_worker, daemon=True).start()
    
    @rumps.clicked("Save Current Workspace")
    def save_workspace(self, _):
        """Save current workspace"""
        # Get workspace name from user
        response = rumps.Window(
            message='Enter workspace name:',
            title='Save Workspace',
            default_text='My Workspace',
            ok='Save',
            cancel='Cancel',
            dimensions=(300, 20)
        ).run()
        
        if response.clicked and response.text.strip():
            workspace_name = response.text.strip()
            
            def save_worker():
                rumps.notification(
                    title="Workspaces",
                    subtitle="Saving workspace...",
                    message=f"Capturing '{workspace_name}'"
                )
                
                success, stdout, stderr = self.run_command(["save", workspace_name])
                
                if success:
                    # Update menu with new workspace
                    self.update_workspace_menu()
                    
                    rumps.notification(
                        title="Workspaces",
                        subtitle="Workspace saved",
                        message=f"'{workspace_name}' saved successfully"
                    )
                else:
                    rumps.notification(
                        title="Workspaces",
                        subtitle="Save failed",
                        message=f"Error saving '{workspace_name}': {stderr}"
                    )
            
            # Run in background thread
            threading.Thread(target=save_worker, daemon=True).start()
    
    @rumps.clicked("Delete Workspace")
    def delete_workspace(self, _):
        """Delete a workspace"""
        workspaces = self.get_workspace_list()
        
        if not workspaces:
            rumps.alert("No workspaces found!")
            return
        
        # Get workspace name to delete
        response = rumps.Window(
            message='Enter workspace name to delete:',
            title='Delete Workspace',
            default_text='',
            ok='Delete',
            cancel='Cancel',
            dimensions=(300, 20)
        ).run()
        
        if response.clicked and response.text.strip():
            workspace_name = response.text.strip()
            
            if workspace_name in workspaces:
                # Confirm deletion
                confirm = rumps.alert(
                    title="Confirm Deletion",
                    message=f"Are you sure you want to delete workspace '{workspace_name}'?",
                    ok="Delete",
                    cancel="Cancel"
                )
                
                if confirm == 1:  # OK button
                    success, stdout, stderr = self.run_command(["delete", workspace_name])
                    
                    if success:
                        # Update menu
                        self.update_workspace_menu()
                        
                        rumps.notification(
                            title="Workspaces",
                            subtitle="Workspace deleted",
                            message=f"'{workspace_name}' deleted"
                        )
                    else:
                        rumps.alert(f"Error deleting workspace: {stderr}")
            else:
                rumps.alert(f"Workspace '{workspace_name}' not found!")
    
    @rumps.clicked("List Workspaces")
    def list_workspaces(self, _):
        """Show list of all workspaces"""
        success, stdout, stderr = self.run_command(["list"])
        
        if success:
            if "No saved workspaces found!" in stdout:
                rumps.alert("No saved workspaces found!")
            else:
                # Clean up the output for display
                lines = stdout.strip().split('\n')
                clean_lines = []
                for line in lines:
                    if line.startswith('Saved workspaces:'):
                        continue
                    if line.strip():
                        clean_lines.append(line)
                
                if clean_lines:
                    message = "Saved Workspaces:\n\n" + "\n".join(clean_lines)
                    rumps.alert(title="Workspace List", message=message)
                else:
                    rumps.alert("No saved workspaces found!")
        else:
            rumps.alert(f"Error listing workspaces: {stderr}")

def main():
    # Check if the command-line script exists
    script_path = Path(__file__).parent / "workspace_manager_app.py"
    if not script_path.exists():
        rumps.alert(
            title="Error",
            message=f"Command-line script not found: {script_path}\n\nPlace workspace_manager_app.py in the same directory."
        )
        return
    
    # Test if the script works
    try:
        result = subprocess.run(
            ["python3", str(script_path), "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            rumps.alert(
                title="Error",
                message=f"Command-line script test failed:\n{result.stderr}"
            )
            return
    except Exception as e:
        rumps.alert(
            title="Error", 
            message=f"Cannot run command-line script:\n{e}"
        )
        return
    
    # Start the menu bar app
    import AppKit
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    # Start the menu bar app
    workspace_app = WorkspaceMenuBarApp()
    workspace_app.run()

if __name__ == "__main__":
    main()