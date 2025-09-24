#!/usr/bin/env python3
"""
Complete Workspace Manager for macOS
Saves and restores complete workspace setups including app positions, Safari tabs, documents, etc.
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

class WorkspaceManager:
    def __init__(self):
        self.workspace_dir = Path.cwd() / "saved_workspaces"
        self.workspace_dir.mkdir(exist_ok=True)
        
    def run_applescript(self, script: str) -> str:
        """Execute AppleScript and return result"""
        try:
            result = subprocess.run(
                ['osascript', '-e', script], 
                capture_output=True, 
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"AppleScript error: {result.stderr}")
                return ""
        except subprocess.TimeoutExpired:
            print("AppleScript timed out")
            return ""
        except Exception as e:
            print(f"Error running AppleScript: {e}")
            return ""
    
    def get_running_apps(self) -> List[str]:
        """Get list of visible running applications"""
        script = '''
        tell application "System Events"
            set appList to name of every application process whose visible is true
        end tell
        return appList
        '''
        result = self.run_applescript(script)
        if result:
            # Parse AppleScript list format
            apps = result.replace('{', '').replace('}', '').split(', ')
            return [app.strip('"') for app in apps if app.strip()]
        return []
    
    def capture_safari_data(self) -> Dict[str, Any]:
        """Capture Safari tabs and window positions"""
        script = '''
        set safariData to {}
        tell application "Safari"
            if it is running then
                repeat with w from 1 to count of windows
                    set windowTabs to {}
                    repeat with t from 1 to count of tabs in window w
                        set end of windowTabs to URL of tab t in window w
                    end repeat
                    set end of safariData to windowTabs
                end repeat
            end if
        end tell
        
        # Convert to string format safely
        set AppleScript's text item delimiters to "|||"
        set windowResults to {}
        repeat with windowTabs in safariData
            set AppleScript's text item delimiters to ":::"
            set windowString to windowTabs as string
            set end of windowResults to windowString
            set AppleScript's text item delimiters to "|||"
        end repeat
        set finalResult to windowResults as string
        set AppleScript's text item delimiters to ""
        return finalResult

        '''

        result = self.run_applescript(script)
        if result:
            windows = []
            for window_data in result.split('|||'):
                if window_data.strip():
                    tabs = [url.strip() for url in window_data.split(':::') if url.strip()]
                    if tabs:
                        windows.append(tabs)
            
            return {
                "app": "Safari",
                "type": "browser",
                "windows": windows,
                "window_positions": self.get_window_positions("Safari")
            }
        return {}
    
    def capture_word_data(self) -> Dict[str, Any]:
        """Capture Word documents"""
        script = '''
        tell application "Microsoft Word"
            if it is running then
                set docList to {}
                set docCount to count of documents
                if docCount = 0 then return ""
        
                repeat with i from 1 to docCount
                    set doc to document i
                    if saved of doc is true then
                        if full name of doc is not "" then
                            try
                                set end of docList to (name of doc) & ":::" & (full name of doc)
                            on error
                                set end of docList to (name of doc) & ":::"
                            end try
                        end if
                    end if
                end repeat                
                set AppleScript's text item delimiters to "|||"
                set docResult to docList as string
                set AppleScript's text item delimiters to ""
                return docResult
            end if
        end tell
        '''

        result = self.run_applescript(script)
        if result:
            documents = []
            for doc_data in result.split('|||'):
                if doc_data.strip():
                    parts = doc_data.split(':::')
                    doc_name = parts[0] if parts else ""
                    doc_path = parts[1] if len(parts) > 1 else ""
                    if doc_name:
                        documents.append({"name": doc_name, "path": doc_path})
            
            return {
                "app": "Microsoft Word",
                "type": "document_editor",
                "documents": documents,
                "window_positions": self.get_window_positions("Microsoft Word")
            }
        return {}
    
    def capture_logos_data(self) -> Dict[str, Any]:
        """Capture Logos Bible Software state"""
        # Check if Logos is running
        script = '''
        tell application "System Events"
            if exists process "Logos" then
                return "running"
            else
                return "not running"
            end if
        end tell
        '''
        
        result = self.run_applescript(script)
        if result == "running":
            # Try to get current layout (this may need adjustment based on Logos version)
            layout_script = '''
            tell application "System Events"
                tell process "Logos"
                    try
                        set currentLayout to name of menu item 1 of menu "Layouts" of menu bar 1
                        return currentLayout
                    on error
                        return ""
                    end try
                end tell
            end tell
            '''
            
            current_layout = self.run_applescript(layout_script)
            
            return {
                "app": "Logos",
                "type": "bible_software",
                "current_layout": current_layout,
                "window_positions": self.get_window_positions("Logos")
            }
        return {}
    
    def capture_zotero_data(self) -> Dict[str, Any]:
        """Capture Zotero state"""
        script = '''
        tell application "System Events"
            if exists process "Zotero" then
                return "running"
            else
                return "not running"
            end if
        end tell
        '''
        
        result = self.run_applescript(script)
        if result == "running":
            return {
                "app": "Zotero",
                "type": "reference_manager",
                "window_positions": self.get_window_positions("Zotero")
            }
        return {}
    
    def get_window_positions(self, app_name: str) -> List[Dict[str, int]]:
        """Get window positions and sizes for an app"""
        print(f"  Getting window positions for {app_name}...")
        
        # Try a more direct approach - get each window individually
        positions = []
        
        # First, get the number of windows
        count_script = f'''
        tell application "System Events"
            tell process "{app_name}"
                try
                    return count of windows
                on error
                    return 0
                end try
            end tell
        end tell
        '''
        
        window_count_result = self.run_applescript(count_script)
        print(f"  Window count result: '{window_count_result}'")
        
        try:
            window_count = int(window_count_result) if window_count_result else 0
        except ValueError:
            print(f"    Could not parse window count: {window_count_result}")
            return positions
        
        print(f"  Found {window_count} windows for {app_name}")
        
        # Get position for each window individually
        for i in range(1, window_count + 1):
            window_script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    try
                        set pos to position of window {i}
                        set siz to size of window {i}
                        return (item 1 of pos) & "," & (item 2 of pos) & "," & (item 1 of siz) & "," & (item 2 of siz)
                    on error errMsg
                        return "ERROR: " & errMsg
                    end try
                end tell
            end tell
            '''
            
            result = self.run_applescript(window_script)
            print(f"    Window {i} result: '{result}'")
            
            if result and not result.startswith("ERROR:"):
                # Clean up the result - remove extra spaces and commas
                clean_result = result.strip().replace(" ,, ", ",").replace(",,", ",")
                coords = clean_result.split(',')
                
                # Filter out empty strings
                coords = [c.strip() for c in coords if c.strip()]
                
                print(f"    Cleaned coords: {coords}")
                
                if len(coords) == 4:
                    try:
                        position_data = {
                            "x": int(float(coords[0])),
                            "y": int(float(coords[1])),
                            "width": int(float(coords[2])),
                            "height": int(float(coords[3]))
                        }
                        positions.append(position_data)
                        print(f"    ✓ Parsed window {i}: {position_data}")
                    except (ValueError, IndexError) as e:
                        print(f"    ✗ Could not parse window {i} data '{clean_result}': {e}")
                else:
                    print(f"    ✗ Wrong number of coordinates ({len(coords)}): {coords}")
            else:
                print(f"    ✗ Failed to get window {i} position: {result}")
        
        print(f"    Final result: {len(positions)} windows captured")
        return positions
    
    def capture_workspace(self, name: str) -> None:
        """Capture current workspace state"""
        print(f"Capturing workspace: {name}")
        
        workspace_data = {
            "name": name,
            "created": datetime.now().isoformat(),
            "apps": []
        }
        
        # Capture specific apps
        app_capturers = {
            "Safari": self.capture_safari_data,
            "Microsoft Word": self.capture_word_data,
            "Logos": self.capture_logos_data,
            "Zotero": self.capture_zotero_data
        }
        
        running_apps = self.get_running_apps()
        print(f"Found running apps: {running_apps}")
        
        for app_name, capturer in app_capturers.items():
            if app_name in running_apps:
                print(f"Capturing {app_name}...")
                app_data = capturer()
                if app_data:
                    workspace_data["apps"].append(app_data)
        
        # Capture other running apps (basic)
        for app_name in running_apps:
            if app_name not in app_capturers and app_name not in ["Finder", "System Events"]:
                print(f"Capturing {app_name} (basic)...")
                window_positions = self.get_window_positions(app_name)
                basic_data = {
                    "app": app_name,
                    "type": "generic",
                    "window_positions": window_positions
                }
                if window_positions:  # Only add if we got positions
                    workspace_data["apps"].append(basic_data)
        
        # Save workspace
        workspace_file = self.workspace_dir / f"{name}.json"
        with open(workspace_file, 'w') as f:
            json.dump(workspace_data, f, indent=2)
        
        print(f"Workspace saved to: {workspace_file}")

    def restore_safari(self, app_data: Dict[str, Any]) -> None:
        """Restore Safari with tabs"""
        print("Restoring Safari...")

        windows = app_data.get("windows", [])
        if not windows:
            return

        # Close existing Safari windows first
        close_script = '''
        tell application "Safari"
            try
                close every window
            end try
        end tell
        '''
        self.run_applescript(close_script)
        time.sleep(1)

        # Open Safari and create windows with tabs
        for i, window_tabs in enumerate(windows):
            if not window_tabs:
                continue

            if i == 0:
                # First window
                script = f'''
                tell application "Safari"
                    activate
                    make new document with properties {{URL:"{window_tabs[0]}"}}
                    set currentWindow to front window
                '''

                # Add additional tabs
                for tab_url in window_tabs[1:]:
                    script += f'''
                    make new tab at end of tabs of currentWindow with properties {{URL:"{tab_url}"}}
                    '''

                script += '''
                end tell
                '''
            else:
                # Additional windows
                script = f'''
                tell application "Safari"
                    make new document with properties {{URL:"{window_tabs[0]}"}}
                    set currentWindow to front window
                '''

                for tab_url in window_tabs[1:]:
                    script += f'''
                    make new tab at end of tabs of currentWindow with properties {{URL:"{tab_url}"}}
                    '''

                script += '''
                end tell
                '''

            self.run_applescript(script)
            time.sleep(2)  # Give time for pages to load

    def convert_to_posix(self, path):
        applescript = f'''
        set posixPath to POSIX path of "{path}"
        return posixPath
        '''
        result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
        return result.stdout.strip()

    def is_document_open(self, doc_path):
        applescript = f'''
        tell application "Microsoft Word"
            set docNames to name of every document
        end tell
        '''
        try:
            result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, check=True)
            open_docs = result.stdout.split(", ")
            return any(doc_path.endswith(doc.strip()) for doc in open_docs)
        except subprocess.CalledProcessError as e:
            print(f"Error checking if document is open: {e}")
            return False

    def open_document(self, doc_path):
        if not os.path.exists(doc_path):
            print(f"The file does not exist: {doc_path}")
            return

        if self.is_document_open(doc_path):
            print(f"Document is already open: {doc_path}")
            return

        print(f"Opening document: {doc_path}")
        applescript = f'''
            try
                tell application "Microsoft Word"
                    activate
                    open POSIX file "{doc_path}"
                end tell
            on error errMsg
                log "Error opening document: " & errMsg
            end try
            '''
        try:
            subprocess.run(['osascript', '-e', applescript], check=True)
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print(f"Error opening document: {e}")

    def restore_word(self, app_data: Dict[str, Any]) -> None:
        """Restore Word documents"""
        print("Restoring Microsoft Word...")

        self.run_applescript('''
        tell application "System Events"
            if not (exists process "Microsoft Word") then
                tell application "Microsoft Word" to launch
            end if
        end tell
        ''')
        time.sleep(2)
        self.run_applescript('tell application "Microsoft Word" to activate')
        time.sleep(5)

        documents = app_data.get("documents", [])
        if not documents:
            return
        
        for doc in documents:
            applescript_path = doc.get("path")
            posix_path = self.convert_to_posix(applescript_path)

            if posix_path:
                self.open_document(posix_path)

    def restore_logos(self, app_data: Dict[str, Any]) -> None:
        """Restore Logos Bible Software"""
        print("Restoring Logos...")
        
        # Open Logos
        self.run_applescript('tell application "Logos" to activate')
        time.sleep(3)  # Logos takes time to load
        
        # Try to set layout if specified
        layout = app_data.get("current_layout", "")
        if layout:
            script = f'''
            tell application "System Events"
                tell process "Logos"
                    try
                        click menu item "{layout}" of menu "Layouts" of menu bar 1
                    end try
                end tell
            end tell
            '''
            self.run_applescript(script)
    
    def restore_window_positions(self, app_name: str, positions: List[Dict[str, int]]) -> None:
        """Restore window positions for an app"""
        if not positions:
            return
        
        print(f"Restoring window positions for {app_name}...")
        time.sleep(2)  # Give app more time to fully open and create windows
        
        # First, check how many windows the app actually has
        check_script = f'''
        tell application "System Events"
            tell process "{app_name}"
                try
                    return count of windows
                on error
                    return 0
                end try
            end tell
        end tell
        '''
        
        window_count_str = self.run_applescript(check_script)
        try:
            actual_window_count = int(window_count_str) if window_count_str else 0
        except ValueError:
            actual_window_count = 0
        
        print(f"  {app_name} has {actual_window_count} windows, restoring {len(positions)} positions")
        
        # Restore positions for each window
        for i, pos in enumerate(positions):
            if i >= actual_window_count:
                break  # Don't try to position windows that don't exist
                
            script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    try
                        -- Window numbering in AppleScript starts at 1
                        set targetWindow to window {i+1}
                        
                        -- Set position first
                        set position of targetWindow to {{{pos["x"]}, {pos["y"]}}}
                        
                        -- Small delay to let position change take effect
                        delay 0.1
                        
                        -- Then set size
                        set size of targetWindow to {{{pos["width"]}, {pos["height"]}}}
                        
                        return "Window {i+1} positioned at ({pos["x"]}, {pos["y"]}) with size ({pos["width"]}, {pos["height"]})"
                    on error errMsg
                        return "Error positioning window {i+1}: " & errMsg
                    end try
                end tell
            end tell
            '''
            
            result = self.run_applescript(script)
            if result:
                print(f"    {result}")
            
            time.sleep(0.3)  # Small delay between window adjustments
    
    def restore_workspace(self, name: str) -> None:
        """Restore a saved workspace"""
        workspace_file = self.workspace_dir / f"{name}.json"
        
        if not workspace_file.exists():
            print(f"Workspace '{name}' not found!")
            return
        
        with open(workspace_file, 'r') as f:
            workspace_data = json.load(f)
        
        print(f"Restoring workspace: {workspace_data['name']}")
        print("Note: This will open apps without closing existing ones.")
        print("You may want to close existing apps first.")
        print()
        
        # First pass: Open all applications
        for app_data in workspace_data.get("apps", []):
            app_name = app_data.get("app", "")
            app_type = app_data.get("type", "generic")
            
            print(f"Opening {app_name}...")
            
            if app_name == "Safari":
                self.restore_safari(app_data)
            elif app_name == "Microsoft Word":
                self.restore_word(app_data)
            elif app_name == "Logos":
                self.restore_logos(app_data)
            elif app_name == "Zotero":
                self.run_applescript('tell application "Zotero" to activate')
                time.sleep(2)
            else:
                # Generic app - just open it
                try:
                    self.run_applescript(f'tell application "{app_name}" to activate')
                    time.sleep(1)
                except:
                    print(f"Could not open {app_name}")
        
        # Give all apps time to fully load
        print("\nWaiting for apps to fully load before positioning windows...")
        time.sleep(3)
        
        # Second pass: Restore window positions for all apps
        print("Restoring window positions...")
        for app_data in workspace_data.get("apps", []):
            app_name = app_data.get("app", "")
            positions = app_data.get("window_positions", [])
            
            if positions:
                self.restore_window_positions(app_name, positions)
        
        print(f"\nWorkspace '{name}' restored!")
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all saved workspaces"""
        workspaces = []
        
        for file_path in self.workspace_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    workspaces.append({
                        "name": data.get("name", file_path.stem),
                        "created": data.get("created", "Unknown"),
                        "app_count": len(data.get("apps", [])),
                        "apps": [app.get("app", "Unknown") for app in data.get("apps", [])]
                    })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping invalid workspace file {file_path}: {e}")
                continue
        
        return sorted(workspaces, key=lambda x: x["created"], reverse=True)
    
    def delete_workspace(self, name: str) -> None:
        """Delete a workspace"""
        workspace_file = self.workspace_dir / f"{name}.json"
        
        if not workspace_file.exists():
            print(f"Workspace '{name}' not found!")
            return
        
        workspace_file.unlink()
        print(f"Workspace '{name}' deleted.")

def main():
    parser = argparse.ArgumentParser(description='Workspace Manager for macOS')
    parser.add_argument('command', choices=['save', 'load', 'list', 'delete'])
    parser.add_argument('name', nargs='?', help='Workspace name')
    
    args = parser.parse_args()
    
    manager = WorkspaceManager()
    
    try:
        if args.command == 'save':
            if not args.name:
                name = input("Enter workspace name: ").strip()
            else:
                name = args.name
            
            if not name:
                print("Workspace name is required!")
                sys.exit(1)
            
            manager.capture_workspace(name)
        
        elif args.command == 'load':
            if not args.name:
                # Show available workspaces
                workspaces = manager.list_workspaces()
                if not workspaces:
                    print("No saved workspaces found!")
                    sys.exit(1)
                
                print("Available workspaces:")
                for i, ws in enumerate(workspaces, 1):
                    print(f"{i}. {ws['name']} ({ws['app_count']} apps)")
                
                try:
                    choice = int(input("Select workspace number: ")) - 1
                    if 0 <= choice < len(workspaces):
                        name = workspaces[choice]['name']
                    else:
                        print("Invalid selection!")
                        sys.exit(1)
                except ValueError:
                    print("Invalid input!")
                    sys.exit(1)
            else:
                name = args.name
            
            manager.restore_workspace(name)
        
        elif args.command == 'list':
            workspaces = manager.list_workspaces()
            if not workspaces:
                print("No saved workspaces found!")
            else:
                print("Saved workspaces:")
                for ws in workspaces:
                    print(f"• {ws['name']} - {ws['app_count']} apps: {', '.join(ws['apps'])}")
                    print(f"  Created: {ws['created'][:19]}")  # Show date without microseconds
                    print()
        
        elif args.command == 'delete':
            if not args.name:
                workspaces = manager.list_workspaces()
                if not workspaces:
                    print("No saved workspaces found!")
                    sys.exit(1)
                
                print("Available workspaces:")
                for i, ws in enumerate(workspaces, 1):
                    print(f"{i}. {ws['name']}")
                
                try:
                    choice = int(input("Select workspace number to delete: ")) - 1
                    if 0 <= choice < len(workspaces):
                        name = workspaces[choice]['name']
                    else:
                        print("Invalid selection!")
                        sys.exit(1)
                except ValueError:
                    print("Invalid input!")
                    sys.exit(1)
            else:
                name = args.name
            
            confirm = input(f"Are you sure you want to delete '{name}'? (y/N): ")
            if confirm.lower() == 'y':
                manager.delete_workspace(name)
            else:
                print("Cancelled.")
    
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()